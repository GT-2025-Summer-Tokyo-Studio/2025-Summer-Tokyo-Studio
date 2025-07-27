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
OPENWEATHERMAP_API_KEY = "11f55ace1d57529699ae6c93e63efc21"
GOOGLE_MAPS_API_KEY = "AIzaSyACNNLSreKshTtf2o8SruS1oE0rybjOt7Q"

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

# # Get walking and driving graphs
G_walk = ox.graph_from_polygon(polygon, network_type='walk')
G_drive = ox.graph_from_polygon(polygon, network_type='drive')
#