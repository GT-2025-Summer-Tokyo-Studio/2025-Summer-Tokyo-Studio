import pandas as pd

# Load the output dataset from the ArcPy kinetic energy calculator tool (should have the spatially joined variables)
df = pd.read_csv('kinetic_06182025.csv')

# Define energy variables
energy_vars = ['Energy_10p_kWh', 'Energy_25p_kWh', 'Energy_50p_kWh', 'Energy_75p_kWh', 'Energy_90p_kWh']

# Sum each variable by category (daily values)
result_daily = df.groupby('MainUse')[energy_vars].sum()

print("Daily Energy Consumption by Category:")
print(result_daily)

# Convert to yearly (multiply by 365)
result_yearly = result_daily * 365

print("\nYearly Energy Consumption by Category:")
print(result_yearly)
