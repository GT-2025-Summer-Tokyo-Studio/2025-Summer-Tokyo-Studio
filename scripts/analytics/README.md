# Yearly kWh Generated Per Building Use Category
## Prerequisites
To run the `kwhByBuildingUseCategory.py` script, you will need to load the output dataset from the ArcPy kinetic floor energy calculator tool (it should have the spatially joined variables).

# Kinetic Floor Payback Analysis
A Python tool for analyzing the financial viability and payback period of kinetic floor tile installations based on building foot traffic patterns and energy generation potential. `kineticFloorPaybackPeriod.py`

## Purpose

This tool calculates the economic feasibility of installing piezoelectric floor tiles in buildings by analyzing installation costs, energy generation potential, maintenance expenses, and revenue from electricity savings to determine payback periods.

## Prerequisites

### Software Requirements
- Python 3.x
- Required packages:
  - pandas
  - numpy

### Input Data Requirements
- CSV file containing kinetic energy analysis data with the following columns:
  - `KFArea`: Kinetic floor area (m²)
  - `footsteps`: Daily footstep count per building
  - `MainUse`: Building type/usage classification

## Key Constants and Assumptions

### Cost Parameters
- **Tile Cost**: ¥56,700 per tile (based on Pavegen 2024 pricing)
- **Installation Cost**: ¥30,000 per m²
- **Tile Coverage**: 0.25 m² per tile
- **Annual Maintenance**: 2% of total installation cost

### Energy Parameters
- **Energy per Footstep**: 5 Joules (realistic conversion rate)
- **Analysis Period**: 20-year system lifespan
- **Operating Days**: 365 days per year

### Electricity Rates (Tokyo)
- **Commercial Buildings**: ¥30.18 per kWh (offices, hospitals, commercial spaces)
- **Residential Buildings**: ¥36.70 per kWh
- **Default Rate**: Commercial rate for unclassified buildings

## Features

### Cost Analysis
- Calculates total number of tiles required
- Computes installation and equipment costs
- Estimates annual maintenance expenses

### Revenue Calculations
- Determines energy generation based on realistic footstep-to-electricity conversion
- Maps building types to appropriate electricity rates
- Calculates annual revenue from energy savings

### Payback Analysis
- Computes net annual benefits (revenue minus maintenance)
- Determines payback period in years
- Categorizes buildings by payback performance:
  - Excellent: < 10 years
  - Good: 10-15 years  
  - Fair: 15-25 years
  - Poor: > 25 years
  - Never: Negative or zero net benefit

### Performance Metrics
- Cost per kWh generated over system lifetime
- Energy generation per square meter
- Revenue potential per square meter

## Usage

```python
import pandas as pd
from payback_analysis import add_payback_analysis, generate_summary_stats

# Load your kinetic energy dataset
df = pd.read_csv('kinetic_06292025.csv')

# Add payback analysis columns
df_with_payback = add_payback_analysis(df)

# Generate summary statistics
generate_summary_stats(df_with_payback)

# Save results
df_with_payback.to_csv('kinetic_with_payback_analysis.csv', index=False)
```

## Output Columns Added

The analysis adds the following columns to your dataset:

**Cost Columns:**
- `num_tiles`: Number of tiles required
- `tile_cost_yen`: Equipment cost in yen
- `installation_cost_yen`: Installation cost in yen
- `total_installation_cost_yen`: Total upfront investment

**Energy & Revenue Columns:**
- `corrected_daily_energy_kwh`: Realistic daily energy generation
- `corrected_yearly_energy_kwh`: Annual energy generation
- `annual_revenue_yen`: Annual electricity savings
- `annual_maintenance_cost_yen`: Annual maintenance costs

**Analysis Columns:**
- `payback_years`: Time to recover investment
- `payback_category`: Performance classification
- `net_annual_benefit_yen`: Annual profit/loss
- `cost_per_kwh_yen`: Cost efficiency metric
- `energy_per_sqm_kwh_year`: Energy density
- `revenue_per_sqm_yen_year`: Revenue density

## Summary Output

The tool generates comprehensive terminal output including:
- Total buildings analyzed and installation costs
- District-wide energy generation potential  
- Payback period distribution across buildings
- Best performing buildings identification
- Optimization insights and recommendations
