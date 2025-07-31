import pandas as pd
import numpy as np

def add_payback_analysis(df):
    """
    Add payback analysis columns to existing kinetic energy dataset
    
    Parameters:
    df: DataFrame with existing columns (KFArea, footsteps, MainUse, etc.)
    
    Returns:
    DataFrame with additional payback analysis columns
    """
    
    # Constants based on market research
    COST_PER_TILE_YEN = 56700  # ¥56,700 per tile (Pavegen 2024 pricing)
    INSTALLATION_COST_PER_SQM_YEN = 30000  # ¥30,000 per m² installation
    TILE_AREA_SQM = 0.25  # Each tile is 0.25 m²
    MAINTENANCE_RATE = 0.02  # 2% annual maintenance
    
    # Tokyo electricity rates (¥/kWh)
    COMMERCIAL_RATE = 30.18  # Office, hospital, commercial
    RESIDENTIAL_RATE = 36.70  # Residential buildings
    
    # Energy conversion (realistic calculation)
    ENERGY_PER_STEP_JOULES = 5  # Joules per footstep, original run was 3 per
    JOULES_TO_KWH = 1 / 3600000  # Convert joules to kWh
    ENERGY_PER_STEP_KWH = ENERGY_PER_STEP_JOULES * JOULES_TO_KWH
    
    # Create a copy to avoid modifying original
    df_analysis = df.copy()
    
    # 1. Calculate number of tiles needed
    df_analysis['num_tiles'] = np.ceil(df_analysis['KFArea'] / TILE_AREA_SQM)
    
    # 2. Calculate costs
    df_analysis['tile_cost_yen'] = df_analysis['num_tiles'] * COST_PER_TILE_YEN
    df_analysis['installation_cost_yen'] = df_analysis['KFArea'] * INSTALLATION_COST_PER_SQM_YEN
    df_analysis['total_installation_cost_yen'] = (
        df_analysis['tile_cost_yen'] + df_analysis['installation_cost_yen']
    )
    
    # 3. Map building types to electricity rates
    # You'll need to adjust this mapping based on your MainUse values
    def get_electricity_rate(main_use):
        """Map building use to appropriate electricity rate"""
        main_use_lower = str(main_use).lower()
        if any(term in main_use_lower for term in ['office', 'commercial', 'hospital']):
            return COMMERCIAL_RATE
        elif any(term in main_use_lower for term in ['residential', 'resid', 'house']):
            return RESIDENTIAL_RATE
        else:
            return COMMERCIAL_RATE  # Default to commercial rate
    
    df_analysis['electricity_rate_yen_kwh'] = df_analysis['MainUse'].apply(get_electricity_rate)
    
    # 4. Calculate corrected energy generation (using footsteps instead of your EnergyYearly_kWh)
    df_analysis['corrected_daily_energy_kwh'] = (
        df_analysis['footsteps'] * ENERGY_PER_STEP_KWH # the real
        #(df_analysis['footsteps'] * 250) * ENERGY_PER_STEP_KWH # * 250 say there's 50 more people per building/day
        #(df_analysis['footsteps'] * 900) * ENERGY_PER_STEP_KWH # * 900 say there's 50 more people per building/day
        #(df_analysis['footsteps'] * 1400) * ENERGY_PER_STEP_KWH # * 1400 say there's 50 more people per building/day
    )
    df_analysis['corrected_yearly_energy_kwh'] = (
        df_analysis['corrected_daily_energy_kwh'] * 365
    )
    
    # 5. Calculate annual costs and revenues
    df_analysis['annual_maintenance_cost_yen'] = (
        df_analysis['total_installation_cost_yen'] * MAINTENANCE_RATE
    )
    df_analysis['annual_revenue_yen'] = (
        df_analysis['corrected_yearly_energy_kwh'] * df_analysis['electricity_rate_yen_kwh']
    )
    
    # 6. Calculate net benefit and payback
    df_analysis['net_annual_benefit_yen'] = (
        df_analysis['annual_revenue_yen'] - df_analysis['annual_maintenance_cost_yen']
    )
    
    # Payback calculation (handle division by zero)
    df_analysis['payback_years'] = np.where(
        df_analysis['net_annual_benefit_yen'] > 0,
        df_analysis['total_installation_cost_yen'] / df_analysis['net_annual_benefit_yen'],
        np.inf  # Never pays back if net benefit is negative/zero
    )
    
    # 7. Calculate cost per kWh generated (useful for optimization)
    df_analysis['cost_per_kwh_yen'] = np.where(
        df_analysis['corrected_yearly_energy_kwh'] > 0,
        df_analysis['total_installation_cost_yen'] / (df_analysis['corrected_yearly_energy_kwh'] * 20),  # 20-year lifespan
        np.inf
    )
    
    # 8. Add efficiency metrics for optimization
    df_analysis['energy_per_sqm_kwh_year'] = (
        df_analysis['corrected_yearly_energy_kwh'] / df_analysis['KFArea']
    )
    df_analysis['revenue_per_sqm_yen_year'] = (
        df_analysis['annual_revenue_yen'] / df_analysis['KFArea']
    )
    
    # 9. Create payback categories for analysis
    def categorize_payback(years):
        if years == np.inf:
            return 'Never'
        elif years <= 10:
            return 'Excellent (<10 years)'
        elif years <= 15:
            return 'Good (10-15 years)'
        elif years <= 25:
            return 'Fair (15-25 years)'
        else:
            return 'Poor (>25 years)'
    
    df_analysis['payback_category'] = df_analysis['payback_years'].apply(categorize_payback)
    
    return df_analysis

def generate_summary_stats(df_analysis):
    """Generate summary statistics for terminal output"""
    print("=== KINETIC TILE PAYBACK ANALYSIS SUMMARY ===\n")
    
    # Basic stats
    print(f"Total buildings analyzed: {len(df_analysis)}")
    print(f"Total kinetic floor area: {df_analysis['KFArea'].sum():,.0f} m²")
    print(f"Total tiles needed: {df_analysis['num_tiles'].sum():,.0f}")
    print(f"Total installation cost: ¥{df_analysis['total_installation_cost_yen'].sum():,.0f}")
    
    # Energy generation
    print(f"\nTotal annual energy generation: {df_analysis['corrected_yearly_energy_kwh'].sum():,.1f} kWh")
    print(f"Total annual revenue potential: ¥{df_analysis['annual_revenue_yen'].sum():,.0f}")
    
    # Payback distribution
    print(f"\nPayback period distribution:")
    payback_dist = df_analysis['payback_category'].value_counts()
    for category, count in payback_dist.items():
        percentage = (count / len(df_analysis)) * 100
        print(f"  {category}: {count} buildings ({percentage:.1f}%)")
    
    # Best performing buildings
    finite_payback = df_analysis[df_analysis['payback_years'] != np.inf]
    if len(finite_payback) > 0:
        print(f"\nBest payback periods:")
        best_buildings = finite_payback.nsmallest(5, 'payback_years')
        for idx, row in best_buildings.iterrows():
            print(f"  Building {idx}: {row['payback_years']:.1f} years, {row['footsteps']:,} steps/day")
    
    # Optimization insights
    print(f"\nInsights:")
    print(f"  Average payback (finite): {finite_payback['payback_years'].mean():.1f} years")
    print(f"  Median cost per kWh: ¥{df_analysis['cost_per_kwh_yen'].replace([np.inf], np.nan).median():.0f}")
    print(f"  Most efficient building: {df_analysis['energy_per_sqm_kwh_year'].max():.3f} kWh/m²/year")

# Example usage:
if __name__ == "__main__":
    # Load
    df = pd.read_csv('kinetic_06292025.csv')
   
    # Add payback analysis
    df_with_payback = add_payback_analysis(df)
    
    # Display key columns
    key_columns = [
        'KFArea', 'footsteps', 'MainUse', 'total_installation_cost_yen',
        'corrected_yearly_energy_kwh', 'annual_revenue_yen', 'payback_years', 'payback_category'
    ]
    
    print("Sample results with payback analysis:")
    print(df_with_payback[key_columns].round(2))
    
    # Generate summary
    generate_summary_stats(df_with_payback)
    
    print(f"\n=== NEW COLUMNS ADDED ===")
    new_columns = [
        'num_tiles', 'tile_cost_yen', 'installation_cost_yen', 'total_installation_cost_yen',
        'electricity_rate_yen_kwh', 'corrected_daily_energy_kwh', 'corrected_yearly_energy_kwh',
        'annual_maintenance_cost_yen', 'annual_revenue_yen', 'net_annual_benefit_yen',
        'payback_years', 'cost_per_kwh_yen', 'energy_per_sqm_kwh_year', 
        'revenue_per_sqm_yen_year', 'payback_category'
    ]
    
    for col in new_columns:
        print(f"  - {col}")
    
    # Save results
    # kinetic_with_payback_analysis.csv is the real
    # kinetic_with_payback_analysis_multiplied250.csv is the multiplied
    # kinetic_with_payback_analysis_multiplied900.csv is the multiplied
    # kinetic_with_payback_analysis_multiplied1400.csv is the multiplied
    df_with_payback.to_csv('kinetic_with_payback_analysis.csv', index=False)
    print(f"\nResults saved to 'kinetic_with_payback_analysis.csv'")
