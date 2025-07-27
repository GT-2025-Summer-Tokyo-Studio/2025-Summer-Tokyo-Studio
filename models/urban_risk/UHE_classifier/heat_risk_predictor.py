# Heat Risk Predictor (heat_risk_predictor.py):
# Imports the classification module to predict the UHE scenario.
# The heat risk is now directly tied to the classification result: 80 for 'High', 50 for 'Moderate', and 20 for 'Low'.
# Human comfort is calculated based on this heat risk, adjusted by wind speed and illumination.
# Enhanced user interaction with colored prompts and a progress bar remains intact.

from colorama import init, Fore, Style
from tqdm import tqdm
import time
from heat_scenario_classifier import load_and_preprocess_data, train_classifier, predict_scenario

# Initialize colorama for colored output
init()

def calculate_heat_risk(scenario):
    # Heat risk directly based on classified scenario
    if scenario == 'High':
        return 80.0  # High risk
    elif scenario == 'Moderate':
        return 50.0  # Moderate risk
    else:  # Low
        return 20.0  # Low risk

def calculate_human_comfort(heat_risk, wind_speed, illumination):
    # Human comfort adjusted based on heat risk and environmental factors
    comfort = 100 - (heat_risk * 1.5) + (wind_speed * 0.5) - (illumination * 0.2)
    return max(0, min(100, comfort))

# Load data and train classifier
data = load_and_preprocess_data("data/weather_df_summer_2015_2024.csv")
features = ['total_precip', 'avg_temp', 'max_temp', 'min_temp', 'avg_humidity', 
            'avg_wind_speed', 'sunshine', 'solar_rad', 'avg_cloud']
scaler, rf_classifier = train_classifier(data, features)

# Fancy welcome message
print(f"{Fore.CYAN}🌡️ Welcome to the Heat Risk & Comfort Predictor! 🌞{Style.RESET_ALL}")
print("Please provide the following weather parameters:\n")

# User inputs with colored prompts
total_precip = float(input(f"{Fore.YELLOW}Total Precipitation (mm): {Style.RESET_ALL}"))
avg_temp = float(input(f"{Fore.YELLOW}Average Temperature (°C): {Style.RESET_ALL}"))
max_temp = float(input(f"{Fore.YELLOW}Maximum Temperature (°C): {Style.RESET_ALL}"))
min_temp = float(input(f"{Fore.YELLOW}Minimum Temperature (°C): {Style.RESET_ALL}"))
avg_humidity = float(input(f"{Fore.YELLOW}Average Humidity (%): {Style.RESET_ALL}"))
avg_wind_speed = float(input(f"{Fore.YELLOW}Average Wind Speed (m/s): {Style.RESET_ALL}"))
sunshine = float(input(f"{Fore.YELLOW}Sunshine Duration (hours): {Style.RESET_ALL}"))
solar_rad = float(input(f"{Fore.YELLOW}Solar Radiation (MJ/m²): {Style.RESET_ALL}"))
avg_cloud = float(input(f"{Fore.YELLOW}Average Cloud Cover (oktas): {Style.RESET_ALL}"))

# Additional inputs for comfort calculation
wind_speed = float(input(f"{Fore.YELLOW}Wind Speed (m/s): {Style.RESET_ALL}"))
illumination = float(input(f"{Fore.YELLOW}Illumination Intensity (lux): {Style.RESET_ALL}"))

# Predict scenario (UHE assessment)
input_data = {
    'total_precip': total_precip, 'avg_temp': avg_temp, 'max_temp': max_temp,
    'min_temp': min_temp, 'avg_humidity': avg_humidity, 'avg_wind_speed': avg_wind_speed,
    'sunshine': sunshine, 'solar_rad': solar_rad, 'avg_cloud': avg_cloud
}
scenario = predict_scenario(input_data, scaler, rf_classifier, features)

# Simulate calculation with a progress bar
print(f"\n{Fore.MAGENTA}Calculating results...{Style.RESET_ALL}")
for _ in tqdm(range(100), desc="Processing", bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt}"):
    time.sleep(0.02)

# Calculate results
heat_risk = calculate_heat_risk(scenario)
human_comfort = calculate_human_comfort(heat_risk, wind_speed, illumination)

# Fancy output
print(f"\n{Fore.GREEN}=== Heat Risk & Human Comfort Prediction ==={Style.RESET_ALL}")
print(f"🔥 Predicted UHE Scenario: {Fore.RED}{scenario}{Style.RESET_ALL}")
print(f"🔥 Heat Risk Level: {Fore.RED}{heat_risk:.2f}{Style.RESET_ALL} (on a scale of 0-100)")
print(f"😊 Human Comfort Level: {Fore.BLUE}{human_comfort:.2f}%{Style.RESET_ALL}")

# Conditional feedback
if human_comfort < 40:
    print(f"{Fore.RED}⚠️ Warning: Low comfort level! Consider mitigation strategies.{Style.RESET_ALL}")
elif human_comfort < 70:
    print(f"{Fore.YELLOW}⚠️ Moderate comfort: Could be improved with better ventilation or shade.{Style.RESET_ALL}")
else:
    print(f"{Fore.GREEN}✅ Excellent comfort level! Conditions are optimal.{Style.RESET_ALL}")