import pandas as pd
import numpy as np
import osmnx as ox
import networkx as nx
import geopandas as gpd
import requests
from shapely.geometry import Point, LineString, Polygon
from colorama import init, Fore, Style
from tqdm import tqdm
import time
from heat_scenario_classifier import load_and_preprocess_data, train_classifier, predict_scenario
import matplotlib.pyplot as plt
from collections import defaultdict

# Initialize colorama for colored output
init()

# API Keys (replace with your own)
OPENWEATHERMAP_API_KEY = "e9996824ed740719c3aa65edf575bd83"
GOOGLE_MAPS_API_KEY = "AIzaSyAlXyyMyJ2JdHCGslCw_1dFxIzDw5KaIIQ"

# Constants
DRIVING_SPEED_KMH = 30  # Driving speed in km/h

# Vulnerability levels and factors
def get_vulnerability_level(pop):
    if pop <= 5:
        return 'Low'
    elif pop <= 15:
        return 'Medium'
    else:
        return 'High'

vulnerability_factors = {'Low': 1.0, 'Medium': 1.5, 'High': 2.0}
level_order = {'Low': 1, 'Medium': 2, 'High': 3}

def geocode_address(address, api_key):
    """Geocode an address to get latitude and longitude using Google Maps API."""
    url = f"https://maps.googleapis.com/maps/api/geocode/json?address={address}&region=jp&key={api_key}"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        if data['status'] == 'OK':
            location = data['results'][0]['geometry']['location']
            return location['lat'], location['lng']
        else:
            print(f"{Fore.RED}Geocoding failed: {data['status']}{Style.RESET_ALL}")
            return None
    else:
        print(f"{Fore.RED}Geocoding API request failed: {response.status_code}{Style.RESET_ALL}")
        return None

def fetch_weather_data(lat, lon, api_key):
    """Fetch current weather data from OpenWeatherMap API."""
    url = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={api_key}&units=metric"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        return {
            'total_precip': 0.0,
            'avg_temp': data['main']['temp'],
            'max_temp': data['main']['temp_max'],
            'min_temp': data['main']['temp_min'],
            'avg_humidity': data['main']['humidity'],
            'avg_wind_speed': data['wind']['speed'],
            'sunshine': 0.0,
            'solar_rad': 0.0,
            'avg_cloud': data['clouds']['all'] / 10.0
        }
    else:
        print(f"{Fore.RED}Weather API request failed: {response.status_code}{Style.RESET_ALL}")
        return None

def calculate_heat_metrics(scenario):
    """Calculate Heat Hazard, Exposure, and Vulnerability based on scenario."""
    hazard = {'Low': 20, 'Moderate': 50, 'High': 80}[scenario]
    exposure = 1.0  # Simplified for individual route planning
    vulnerability = 1.0  # Simplified for general users
    return hazard, exposure, vulnerability

def adjust_walking_speed(scenario):
    """Adjust walking speed based on heat scenario (km/h to m/s)."""
    speeds = {'Low': 5.0, 'Moderate': 4.0, 'High': 3.0}
    return speeds[scenario] / 3.6

def estimate_resources(scenario, distance):
    """Estimate water needed based on scenario and distance."""
    water_per_km = {'Low': 0.2, 'Moderate': 0.4, 'High': 0.6}
    return water_per_km[scenario] * (distance / 1000)

# Load Nihonbashi boundary
nihonbashi_boundary = gpd.read_file("data/Nihonbashi_Line.shp")
nihonbashi_boundary.set_crs(epsg=2451, inplace=True)
nihonbashi_boundary = nihonbashi_boundary.to_crs(epsg=4326)

# Convert line to polygon if necessary
line = nihonbashi_boundary.geometry.iloc[0]
if not line.is_ring:
    line_coords = list(line.coords)
    if line_coords[0] != line_coords[-1]:
        line_coords.append(line_coords[0])
    line = LineString(line_coords)
try:
    polygon = Polygon(line)
    nihonbashi_boundary.at[nihonbashi_boundary.index[0], 'geometry'] = polygon
except Exception as e:
    print(f"{Fore.RED}Failed to convert line to polygon: {e}{Style.RESET_ALL}")
    exit()
polygon = nihonbashi_boundary.geometry.iloc[0]

# Load evacuation shelters
evac_data = pd.read_csv("data/evac_shelters.csv")

# Load vulnerability data
pop_data = gpd.read_file("data/elder_pop_parcel_2020_2050.shp")
pop_data = pop_data.to_crs(epsg=4326)
pop_data['Pop20_75'] = pd.to_numeric(pop_data['Pop20_75'], errors='coerce')
pop_data['vulnerability_level'] = pop_data['Pop20_75'].apply(get_vulnerability_level)
pop_data['vulnerability_factor'] = pop_data['vulnerability_level'].map(vulnerability_factors)

# Load and preprocess data
data = load_and_preprocess_data("data/weather_df_summer_2015_2024.csv")
features = ['total_precip', 'avg_temp', 'max_temp', 'min_temp', 'avg_humidity', 
            'avg_wind_speed', 'sunshine', 'solar_rad', 'avg_cloud']
scaler, rf_classifier = train_classifier(data, features)

# Welcome message
print(f"{Fore.CYAN}🌡️ Heat Risk Route Planner to Evacuation Shelters in Nihonbashi 🌞{Style.RESET_ALL}")
print("Enter your starting address within Nihonbashi, Tokyo.\n")

# Get starting address
while True:
    start_address = input(f"{Fore.YELLOW}Enter starting address: {Style.RESET_ALL}")
    start_coords = geocode_address(start_address, GOOGLE_MAPS_API_KEY)
    if start_coords:
        start_lat, start_lon = start_coords
        start_point = Point(start_lon, start_lat)
        if polygon.contains(start_point):
            break
        else:
            print(f"{Fore.RED}Address is outside Nihonbashi area. Please try again.{Style.RESET_ALL}")
    else:
        print(f"{Fore.RED}Failed to geocode address. Please try again.{Style.RESET_ALL}")

# Calculate distances to shelters and select top 5 closest
distances = ox.distance.great_circle(start_lat, start_lon, evac_data['latitude'], evac_data['longitude'])
evac_data['distance'] = distances
top5_shelters = evac_data.sort_values('distance').head(5).reset_index(drop=True)

# Display top 5 closest shelters
print(f"\n{Fore.GREEN}Top 5 Closest Evacuation Shelters:{Style.RESET_ALL}")
for i, row in top5_shelters.iterrows():
    print(f"{i+1}. {row['Name']} (Capacity: {row['Capacity']}, Distance: {row['distance']:.2f} meters)")

# User selects a shelter
choice = int(input(f"{Fore.YELLOW}Enter the number of your chosen shelter (1-5): {Style.RESET_ALL}")) - 1
if choice < 0 or choice >= 5:
    print(f"{Fore.RED}Invalid choice.{Style.RESET_ALL}")
    exit()

selected_shelter = top5_shelters.iloc[choice]
end_name = selected_shelter['Name']
end_lat = selected_shelter['latitude']
end_lon = selected_shelter['longitude']

# Fetch weather data and predict scenario
weather_data = fetch_weather_data(start_lat, start_lon, OPENWEATHERMAP_API_KEY)
if not weather_data:
    exit()
scenario = predict_scenario(weather_data, scaler, rf_classifier, features)

# Calculate heat metrics
hazard, exposure, vulnerability = calculate_heat_metrics(scenario)

# Get walking and driving graphs
G_walk = ox.graph_from_polygon(polygon, network_type='walk')
G_drive = ox.graph_from_polygon(polygon, network_type='drive')

# Get park polygons for walking route
parks = ox.features.features_from_polygon(polygon, tags={'leisure': 'park'})
parks = parks[parks.geometry.type.isin(['Polygon', 'MultiPolygon'])]

# Get edge geometries for walking graph
edges_walk = ox.graph_to_gdfs(G_walk, nodes=False)

# Find edges intersecting parks
edges_in_parks = gpd.sjoin(edges_walk, parks, how='inner', predicate='intersects')

# Assign hazard to walking edges
edges_walk['H_edge'] = hazard
edges_walk.loc[edges_walk.index.isin(edges_in_parks.index), 'H_edge'] = hazard * 0.5

# Assign vulnerability to walking edges
edges_with_vuln = gpd.sjoin(edges_walk, pop_data[['geometry', 'vulnerability_level', 'vulnerability_factor']], how='left', predicate='intersects')
edges_with_vuln['vulnerability_level'] = edges_with_vuln['vulnerability_level'].fillna('Low')
edges_with_vuln_grouped = edges_with_vuln.groupby(edges_with_vuln.index).agg({
    'vulnerability_factor': 'max',
    'vulnerability_level': lambda x: max(x, key=lambda k: level_order[k])
})
edges_walk['vulnerability_factor'] = edges_with_vuln_grouped['vulnerability_factor'].fillna(1.0)
edges_walk['vulnerability_level'] = edges_with_vuln_grouped['vulnerability_level'].fillna('Low')

# Assign costs to walking graph edges
for u, v, key, data in G_walk.edges(keys=True, data=True):
    edge_index = (u, v, key)
    data['cost'] = edges_walk.loc[edge_index, 'H_edge'] * data['length'] * edges_walk.loc[edge_index, 'vulnerability_factor']

# Find nearest nodes for walking and driving
start_node_walk = ox.distance.nearest_nodes(G_walk, start_lon, start_lat)
end_node_walk = ox.distance.nearest_nodes(G_walk, end_lon, end_lat)
start_node_drive = ox.distance.nearest_nodes(G_drive, start_lon, start_lat)
end_node_drive = ox.distance.nearest_nodes(G_drive, end_lon, end_lat)

# Find paths
try:
    path_walk_heat = nx.shortest_path(G_walk, start_node_walk, end_node_walk, weight='cost')
    path_walk_distance = nx.shortest_path(G_walk, start_node_walk, end_node_walk, weight='length')
    path_drive = nx.shortest_path(G_drive, start_node_drive, end_node_drive, weight='length')
except nx.NetworkXNoPath:
    print(f"{Fore.RED}No path found to the selected shelter.{Style.RESET_ALL}")
    exit()

# Calculate walking heat-optimized path stats
distance_walk_heat = sum(G_walk[u][v][0]['length'] for u, v in zip(path_walk_heat[:-1], path_walk_heat[1:]))
walking_speed = adjust_walking_speed(scenario)
time_walk_heat = distance_walk_heat / walking_speed / 60  # minutes
total_risk_walk_heat = sum(edges_walk.loc[(u, v, 0), 'H_edge'] * G_walk[u][v][0]['length'] 
                           for u, v in zip(path_walk_heat[:-1], path_walk_heat[1:]) 
                           if (u, v, 0) in edges_walk.index)
water_needed = estimate_resources(scenario, distance_walk_heat)

# Calculate walking shortest path heat risk for reference
total_risk_walk_distance = sum(edges_walk.loc[(u, v, 0), 'H_edge'] * G_walk[u][v][0]['length'] 
                               for u, v in zip(path_walk_distance[:-1], path_walk_distance[1:]) 
                               if (u, v, 0) in edges_walk.index)

# Calculate driving path stats
distance_drive = sum(G_drive[u][v][0]['length'] for u, v in zip(path_drive[:-1], path_drive[1:]))
driving_speed_ms = DRIVING_SPEED_KMH / 3.6  # Convert km/h to m/s
time_drive = distance_drive / driving_speed_ms / 60  # minutes

# Vulnerability summary for walking path
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

# Display results in terminal
print(f"\n{Fore.GREEN}=== Walking Route to {end_name} ==={Style.RESET_ALL}")
print(f"🔥 Heat Scenario: {Fore.RED}{scenario}{Style.RESET_ALL}")
print(f"🔥 Heat Hazard: {Fore.RED}{hazard:.2f}{Style.RESET_ALL}")
print(f"🔥 Heat Exposure: {Fore.YELLOW}{exposure:.2f} (simplified){Style.RESET_ALL}")
print(f"🔥 Heat Vulnerability: {Fore.YELLOW}{vulnerability:.2f} (simplified){Style.RESET_ALL}")
print(f"🔥 Total Distance: {distance_walk_heat:.2f} meters")
print(f"🔥 Estimated Time: {time_walk_heat:.2f} minutes")
print(f"🔥 Total Heat Risk: {total_risk_walk_heat:.2f}")
if total_risk_walk_distance > 0:
    risk_reduction = ((total_risk_walk_distance - total_risk_walk_heat) / total_risk_walk_distance) * 100
    print(f"🔥 Heat Risk Reference: This path reduces heat risk by {risk_reduction:.2f}% compared to the shortest path ({total_risk_walk_distance:.2f}).")
else:
    print(f"🔥 Heat Risk Reference: Shortest path heat risk is {total_risk_walk_distance:.2f}.")
print(f"🔥 Water Needed: {water_needed:.2f} liters")
print(f"🔥 Maximum Vulnerability Level: {max_vuln_level}")
print(f"{Fore.GREEN}Route includes green areas and considers vulnerable populations.{Style.RESET_ALL}")

print("\nVulnerability Summary along the Path:")
print(f"{'Level':<10} {'Total Length (m)':<20} {'Number of Edges':<20}")
for level in ['Low', 'Medium', 'High']:
    if level in vuln_summary:
        total_length = vuln_summary[level]['length']
        count = vuln_summary[level]['count']
        print(f"{level:<10} {total_length:<20.2f} {count:<20}")

print(f"\n{Fore.GREEN}=== Driving Route to {end_name} ==={Style.RESET_ALL}")
print(f"🚗 Total Distance: {distance_drive:.2f} meters")
print(f"🚗 Estimated Time: {time_drive:.2f} minutes")

# Plot routes with table
fig = plt.figure(figsize=(12, 6))
ax1 = fig.add_subplot(121)
ox.plot_graph(G_walk, ax=ax1, show=False, close=False, node_size=0)

# Walking path with vulnerability colors
level_colors = {'Low': 'green', 'Medium': 'yellow', 'High': 'red'}
for u, v in zip(path_walk_heat[:-1], path_walk_heat[1:]):
    if (u, v, 0) in edges_walk.index:
        vuln_level = edges_walk.loc[(u, v, 0), 'vulnerability_level']
        color = level_colors.get(vuln_level, 'gray')
        edge_geom = edges_walk.loc[(u, v, 0), 'geometry']
        if edge_geom.type == 'LineString':
            xs, ys = edge_geom.xy
            ax1.plot(xs, ys, color=color, linewidth=3)
        else:
            for geom in edge_geom.geoms:
                xs, ys = geom.xy
                ax1.plot(xs, ys, color=color, linewidth=3)

# Driving path
drive_coords = [(G_drive.nodes[node]['y'], G_drive.nodes[node]['x']) for node in path_drive]
ax1.plot([coord[1] for coord in drive_coords], [coord[0] for coord in drive_coords], 
         color='blue', linewidth=3, label='Driving Path')

# Start and end markers
ax1.plot(start_lon, start_lat, 'ro', markersize=10, label='Start')
ax1.plot(end_lon, end_lat, 'bo', markersize=10, label='End')

# Legend
from matplotlib.lines import Line2D
legend_elements = [Line2D([0], [0], color='green', lw=3, label='Walking Path: Low Vulnerability'),
                   Line2D([0], [0], color='yellow', lw=3, label='Walking Path: Medium Vulnerability'),
                   Line2D([0], [0], color='red', lw=3, label='Walking Path: High Vulnerability'),
                   Line2D([0], [0], color='blue', lw=3, label='Driving Path')]
ax1.legend(handles=legend_elements)
ax1.set_title("Route Map")

# Add table
ax2 = fig.add_subplot(122)
ax2.axis('off')
table_data = [
    ["Heat Scenario", scenario],
    ["Heat Hazard", f"{hazard:.2f}"],
    ["Total Distance (m)", f"{distance_walk_heat:.2f}"],
    ["Estimated Time (min)", f"{time_walk_heat:.2f}"],
    ["Total Heat Risk", f"{total_risk_walk_heat:.2f}"],
    ["Water Needed (L)", f"{water_needed:.2f}"],
    ["Max Vulnerability", max_vuln_level]
]
table = ax2.table(cellText=table_data, colLabels=["Metric", "Value"], loc='center', cellLoc='center')
table.auto_set_font_size(False)
table.set_fontsize(10)
table.scale(1, 1.5)
ax2.set_title("Walking Route Statistics")

plt.tight_layout()
plt.show()