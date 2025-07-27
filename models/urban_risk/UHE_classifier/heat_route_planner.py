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

# Initialize colorama for colored output
init()

# API Keys (replace with your own)
OPENWEATHERMAP_API_KEY = "e9996824ed740719c3aa65edf575bd83"
GOOGLE_MAPS_API_KEY = "AIzaSyAlXyyMyJ2JdHCGslCw_1dFxIzDw5KaIIQ"

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
    """Adjust walking speed based on heat scenario."""
    """安置 “km/h to m/s."""
    speeds = {'Low': 5.0, 'Moderate': 4.0, 'High': 3.0}
    return speeds[scenario] / 3.6

def estimate_resources(scenario, distance):
    """Estimate water needed based on scenario and distance."""
    water_per_km = {'Low': 0.2, 'Moderate': 0.4, 'High': 0.6}
    return water_per_km[scenario] * (distance / 1000)

# Load Nihonbashi boundary
nihonbashi_boundary = gpd.read_file("UHE_classifier/Nihonbashi_Line.shp")
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
evac_data = pd.read_csv("UHE_classifier/evac_shelters.csv")

# Load and preprocess data
data = load_and_preprocess_data("UHE_classifier/weather_df_summer_2015_2024.csv")
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

# Fetch weather data and predict scenario
weather_data = fetch_weather_data(start_lat, start_lon, OPENWEATHERMAP_API_KEY)
if not weather_data:
    exit()
scenario = predict_scenario(weather_data, scaler, rf_classifier, features)

# Calculate heat metrics
hazard, exposure, vulnerability = calculate_heat_metrics(scenario)

# Display evacuation shelters
print(f"\n{Fore.GREEN}Available Evacuation Shelters:{Style.RESET_ALL}")
for i, row in evac_data.iterrows():
    print(f"{i+1}. {row['Name']} (Capacity: {row['Capacity']})")
choice = int(input(f"{Fore.YELLOW}Enter the number of your chosen shelter: {Style.RESET_ALL}")) - 1
if choice < 0 or choice >= len(evac_data):
    print(f"{Fore.RED}Invalid choice.{Style.RESET_ALL}")
    exit()

end_name = evac_data.iloc[choice]['Name']
end_lat = evac_data.iloc[choice]['latitude']
end_lon = evac_data.iloc[choice]['longitude']

# Get street network and park polygons
G = ox.graph_from_polygon(polygon, network_type='walk')
parks = ox.features.features_from_polygon(polygon, tags={'leisure': 'park'})
parks = parks[parks.geometry.type.isin(['Polygon', 'MultiPolygon'])]

# Get edge geometries
edges = ox.graph_to_gdfs(G, nodes=False)

# Find edges intersecting parks
edges_in_parks = gpd.sjoin(edges, parks, how='inner', predicate='intersects')

# Assign hazard to edges
edges['H_edge'] = hazard
edges.loc[edges.index.isin(edges_in_parks.index), 'H_edge'] = hazard * 0.5

# Assign costs to graph edges
for u, v, key, data in G.edges(keys=True, data=True):
    edge_index = (u, v, key)
    data['cost'] = edges.loc[edge_index, 'H_edge'] * edges.get(edge_index, {'length': data['length']})['length']

# Find nearest nodes
start_node = ox.distance.nearest_nodes(G, start_lon, start_lat)
end_node = ox.distance.nearest_nodes(G, end_lon, end_lat)

# Find shortest path
try:
    path = nx.shortest_path(G, start_node, end_node, weight='cost')
except nx.NetworkXNoPath:
    print(f"{Fore.RED}No path found to the selected shelter.{Style.RESET_ALL}")
    exit()

# Calculate route statistics
path_edges = list(zip(path[:-1], path[1:]))
total_distance = sum(G[u][v][0].get('length', 0) for u, v in path_edges)
walking_speed = adjust_walking_speed(scenario)
total_time = total_distance / walking_speed / 60  # minutes
total_risk = sum(edges.loc[(u, v, 0), 'H_edge'] * G[u][v][0].get('length', 0) 
                 for u, v in path_edges if (u, v, 0) in edges.index)
water_needed = estimate_resources(scenario, total_distance)

# Display results
print(f"\n{Fore.GREEN}=== Route to {end_name} ==={Style.RESET_ALL}")
print(f"🔥 Heat Scenario: {Fore.RED}{scenario}{Style.RESET_ALL}")
print(f"🔥 Heat Hazard: {Fore.RED}{hazard:.2f}{Style.RESET_ALL}")
print(f"🔥 Heat Exposure: {Fore.YELLOW}{exposure:.2f} (simplified){Style.RESET_ALL}")
print(f"🔥 Heat Vulnerability: {Fore.YELLOW}{vulnerability:.2f} (simplified){Style.RESET_ALL}")
print(f"🔥 Total Distance: {total_distance:.2f} meters")
print(f"🔥 Estimated Time: {total_time:.2f} minutes")
print(f"🔥 Total Heat Risk: {total_risk:.2f}")
print(f"🔥 Water Needed: {water_needed:.2f} liters")
print(f"{Fore.GREEN}Route includes green areas to reduce heat exposure.{Style.RESET_ALL}")

# Plot route
fig, ax = ox.plot_graph_route(G, path, route_color='green', route_linewidth=6, node_size=0)
plt.show()