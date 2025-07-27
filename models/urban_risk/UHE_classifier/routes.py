import osmnx as ox
import networkx as nx
import geopandas as gpd
from heat_route_planner_v2 import (
    geocode_address, polygon, GOOGLE_MAPS_API_KEY, OPENWEATHERMAP_API_KEY,
    evac_data, predict_scenario, fetch_weather_data, features,
    scaler, rf_classifier, 
    calculate_heat_metrics, adjust_walking_speed, estimate_resources,
    G_walk, G_drive, pop_data,
    DRIVING_SPEED_KMH, level_order
)
from collections import defaultdict
from shapely.geometry import Point, LineString, mapping



def getRoute(address, shelter_id):
    coords = geocode_address(address, GOOGLE_MAPS_API_KEY)
    # coords = [35.6863395, 139.7823384]
    if not coords:
        # raise ValueError("Geocoding failed")
        return "Geocoding failed"
    start_lat, start_lon = coords
    point = Point(start_lon, start_lat)
    if not polygon.contains(point):
        # raise ValueError("Address is outside Nihonbashi")
        return "Address is outside Nihonbashi"
    # 获取用户选择的避难所 Selected shelter id
    if int(shelter_id) < 0 or int(shelter_id) >= len(evac_data):
        # raise ValueError("Invalid shelter ID")
        return "Invalid shelter ID"

    # 计算距离 Calculate distances
    evac_data['distance'] = ox.distance.great_circle(start_lat, start_lon, evac_data['latitude'], evac_data['longitude'])

    # 最近的5个避难所 Get top 5 nearest shelters
    top5 = evac_data.sort_values('distance').head(5).reset_index(drop=True)

    shelter = top5.iloc[shelter_id-1]
    end_lat = shelter['latitude']
    end_lon = shelter['longitude']

    # 天气 & 热风险 Weather & Hazard
    # # weather_data = fetch_weather_data(start_lat, start_lon, OPENWEATHERMAP_API_KEY)
    # weather_data = {'total_precip': 0.0,
    #         'avg_temp': 25.0,
    #         'max_temp': 30.0,
    #         'min_temp': 18.0,
    #         'avg_humidity': 0.54,
    #         'avg_wind_speed': 2.0,
    #         'sunshine': 0.0,
    #         'solar_rad': 0.0,
    #         'avg_cloud': 1 / 10.0}
    # if not weather_data:
    #     # raise ValueError("Weather API error")
    #     return "Weather API error"
    
    # features = ['total_precip', 'avg_temp', 'max_temp', 'min_temp',
    #             'avg_humidity', 'avg_wind_speed', 'sunshine', 'solar_rad', 'avg_cloud']
    # scenario = predict_scenario(weather_data, scaler, rf_classifier, features)
    weather_data = fetch_weather_data(start_lat, start_lon, OPENWEATHERMAP_API_KEY)
    if not weather_data:
        exit()
    scenario = predict_scenario(weather_data, scaler, rf_classifier, features)
    
    hazard, exposure, vulnerability = calculate_heat_metrics(scenario)

    parks = ox.features.features_from_polygon(polygon, tags={'leisure': 'park'})
    parks = parks[parks.geometry.type.isin(['Polygon', 'MultiPolygon'])]

    edges_walk = ox.graph_to_gdfs(G_walk, nodes=False)
    edges_in_parks = gpd.sjoin(edges_walk, parks, how='inner', predicate='intersects')

    edges_walk['H_edge'] = hazard
    edges_walk.loc[edges_walk.index.isin(edges_in_parks.index), 'H_edge'] = hazard * 0.5
    edges_with_vuln = gpd.sjoin(edges_walk, pop_data[['geometry', 'vulnerability_level', 'vulnerability_factor']],
                                how='left', predicate='intersects')
    edges_with_vuln['vulnerability_level'] = edges_with_vuln['vulnerability_level'].fillna('Low')
    edges_with_vuln_grouped = edges_with_vuln.groupby(edges_with_vuln.index).agg({
        'vulnerability_factor': 'max',
        'vulnerability_level': lambda x: max(x, key=lambda k: level_order[k])
    })
    edges_walk['vulnerability_factor'] = edges_with_vuln_grouped['vulnerability_factor'].fillna(1.0)
    edges_walk['vulnerability_level'] = edges_with_vuln_grouped['vulnerability_level'].fillna('Low')

    # 节点匹配 Nodes Match
    start_node_walk = ox.distance.nearest_nodes(G_walk, start_lon, start_lat)
    end_node_walk = ox.distance.nearest_nodes(G_walk, end_lon, end_lat)
    start_node_drive = ox.distance.nearest_nodes(G_drive, start_lon, start_lat)
    end_node_drive = ox.distance.nearest_nodes(G_drive, end_lon, end_lat)
    
    # 查找路线 Find paths
    try:
        path_walk_heat = nx.shortest_path(G_walk, start_node_walk, end_node_walk, weight='cost')
        path_walk_distance = nx.shortest_path(G_walk, start_node_walk, end_node_walk, weight='length')
        path_drive = nx.shortest_path(G_drive, start_node_drive, end_node_drive, weight='length')
    except nx.NetworkXNoPath:
        # raise ValueError("No path found")
        return "No path found"

    # Calculate walking heat-optimized path stats #最优热度：步行距离，速度，时间，总热风险，水需求
    distance_walk_heat = sum(G_walk[u][v][0]['length'] for u, v in zip(path_walk_heat[:-1], path_walk_heat[1:]))
    walking_speed = adjust_walking_speed(scenario)
    time_walk_heat = distance_walk_heat / walking_speed / 60  # minutes
    total_risk_walk_heat = sum(edges_walk.loc[(u, v, 0), 'H_edge'] * G_walk[u][v][0]['length'] 
                           for u, v in zip(path_walk_heat[:-1], path_walk_heat[1:]) 
                           if (u, v, 0) in edges_walk.index)
    water_needed = estimate_resources(scenario, distance_walk_heat) 

    # Calculate walking shortest path heat risk for reference 步行最短总距离
    total_risk_walk_distance = sum(edges_walk.loc[(u, v, 0), 'H_edge'] * G_walk[u][v][0]['length'] 
                               for u, v in zip(path_walk_distance[:-1], path_walk_distance[1:]) 
                               if (u, v, 0) in edges_walk.index)

    # Calculate driving path stats 开车距离，速度，时间
    distance_drive = sum(G_drive[u][v][0]['length'] for u, v in zip(path_drive[:-1], path_drive[1:]))
    driving_speed_ms = DRIVING_SPEED_KMH / 3.6  # Convert km/h to m/s
    time_drive = distance_drive / driving_speed_ms / 60  # minutes

    # 步行脆弱等级
    vuln_summary = defaultdict(lambda: {'length': 0, 'count': 0})
    path_vuln_levels = []
    for u, v in zip(path_walk_heat[:-1], path_walk_heat[1:]):
        if (u, v, 0) in edges_walk.index:
            length = G_walk[u][v][0]['length']
            vuln_level = edges_walk.loc[(u, v, 0), 'vulnerability_level']
            path_vuln_levels.append(vuln_level)
            vuln_summary[vuln_level]['length'] += length
            vuln_summary[vuln_level]['count'] += 1

    # Determine maximum vulnerability level
    max_vuln_level = max(path_vuln_levels, key=lambda x: level_order[x]) if path_vuln_levels else 'Low'

    #步行路线
    walk_path_segments = []

    for u, v in zip(path_walk_heat[:-1], path_walk_heat[1:]):
        if (u, v, 0) in edges_walk.index:
            vuln_level = edges_walk.loc[(u, v, 0), 'vulnerability_level']
            geom = edges_walk.loc[(u, v, 0), 'geometry']
            
            if geom.geom_type == 'LineString':
                walk_path_segments.append({
                    "type": "LineString",
                    "geometry": mapping(geom),
                    "vulnerability_level": vuln_level
                })
            elif geom.geom_type == 'MultiLineString':
                for g in geom.geoms:
                    walk_path_segments.append({
                        "type": "LineString",
                        "geometry": mapping(g),
                        "vulnerability_level": vuln_level
                    })

    #开车路线
    drive_coords = [(G_drive.nodes[node]['x'], G_drive.nodes[node]['y']) for node in path_drive]

    drive_path_segments = []

    drive_path_segment = {
        "type": "LineString",
        "geometry": mapping(LineString(drive_coords)),
        "mode": "drive"
    }
    drive_path_segments.append(drive_path_segment)




    # 返回参数，路线
    return {
        "shelter_id": int(shelter_id),
        "shelter_name": shelter['Name'],
        "heat_scenario": scenario,
        "heat_hazard": round(hazard, 2),
        "heat_exposure": round(exposure, 2),
        "heat_vulnerability": round(vulnerability, 2),
        "walk_distance": round(distance_walk_heat, 2),
        "estimated_time_min": round(time_walk_heat, 2),
        "total_heat_risk": round(total_risk_walk_heat, 2),
        "heat_risk_reference": (
            round(
                ((total_risk_walk_distance - total_risk_walk_heat) / total_risk_walk_distance) * 100, 
                2
            ) if total_risk_walk_distance > 0 else None
        ),
        "water_needed_liters": round(water_needed, 2),
        "max_vulnerability_level": max_vuln_level,
        "vulnerability_summary": {
            level: {
                "total_length_m": round(vuln_summary[level]["length"], 2),
                "edge_count": vuln_summary[level]["count"]
            }
            for level in ["Low", "Medium", "High"] if level in vuln_summary
        },
        "walk_path_segments": walk_path_segments,
        "start_point": mapping(Point(start_lon, start_lat)),
        "end_point": mapping(Point(end_lon, end_lat)),
        "drive_path_segments": drive_path_segments,
        "drive_distance":round(distance_drive, 2),
        "drive_time":round(time_drive, 2)

    }