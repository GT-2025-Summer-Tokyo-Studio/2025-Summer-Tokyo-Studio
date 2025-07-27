import pandas as pd
import osmnx as ox
from shapely.geometry import Point
from heat_route_planner_v2 import geocode_address, GOOGLE_MAPS_API_KEY, evac_data, polygon
import geopandas as gpd

# evac_data = pd.read_csv("evac_shelters.csv")

# nihonbashi_boundary = gpd.read_file("Nihonbashi_Line.shp")
# nihonbashi_boundary.set_crs(epsg=2451, inplace=True)
# nihonbashi_boundary = nihonbashi_boundary.to_crs(epsg=4326)
# polygon = nihonbashi_boundary.geometry.iloc[0]

def queryShelters(address):
    coords = geocode_address(address, GOOGLE_MAPS_API_KEY)
    # coords = [35.6863395, 139.7823384]
    if not coords:
        # raise ValueError("Geocoding failed")
        return "Geocoding failed"
    lat, lon = coords
    point = Point(lon, lat)
    if not polygon.contains(point):
        # raise ValueError("Address is outside Nihonbashi") # 在边界内 Inside the boundary
        return "Address is outside Nihonbashi"

    # 计算距离 Calculate distances
    evac_data['distance'] = ox.distance.great_circle(lat, lon, evac_data['latitude'], evac_data['longitude'])

    # 最近的5个避难所 Get top 5 nearest shelters
    top5 = evac_data.sort_values('distance').head(5).reset_index(drop=True)

    # 列表 List of shelters
    shelter_list = []
    for i, row in top5.iterrows():
        shelter_list.append({
            "id": int(i+1),
            "name": row['Name'],
            "capacity": int(row['Capacity']),
            "distance": float(row['distance']),
            "latitude": float(row['latitude']),
            "longitude": float(row['longitude'])
        })

    return shelter_list

