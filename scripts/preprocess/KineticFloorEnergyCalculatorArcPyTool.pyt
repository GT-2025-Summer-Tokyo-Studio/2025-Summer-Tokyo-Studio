# -*- coding: utf-8 -*-
# ArcPy tool. Import into the ArcGIS Pro toolbox to run.
import arcpy


class Toolbox:
    def __init__(self):
        """Define the toolbox (the name of the toolbox is the name of the
        .pyt file)."""
        self.label = "Toolbox"
        self.alias = "toolbox"

        # List of tool classes associated with this toolbox
        self.tools = [KineticFloorEnergyCalculator2]


class KineticFloorEnergyCalculator2:
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Step 1_Building Kinetic Energy Generator"
        self.description = "Calculates the potential energy generation from kinetic floors based on building visits"
        self.canRunInBackground = False # Blocks the UI while running

    def getParameterInfo(self):
        """Define the tool parameters."""
        param0 = arcpy.Parameter(
            displayName="Buildings Layer",
            name="buildings_layer",
            datatype="GPFeatureLayer",
            parameterType="Required",
            direction="Input"
        )

        param1 = arcpy.Parameter(
            displayName="GPS Visits Layer",
            name="gps_visits_layer",
            datatype="GPFeatureLayer",
            parameterType="Required",
            direction="Input"
        )

        param2 = arcpy.Parameter(
            displayName="D2 Boundary Layer",
            name="district2_boundary",
            datatype="GPFeatureLayer",
            parameterType="Required",
            direction="Input"
        )

        param3 = arcpy.Parameter(
            displayName="Focus Kinetic Floor Coverage (%)",
            name="coverage_pct",
            datatype="GPDouble",
            parameterType="Optional",  # will compute multiple levels regardless of the user input
            direction="Input"
        )
        param3.value = 50  # Default coverage area to calculate
        param3.filter.type = "Range"
        param3.filter.list = [10, 100]
     
        param4 = arcpy.Parameter(
            displayName="Energy per Step (Joules)",
            name="energy_per_step",
            datatype="GPDouble",
            parameterType="Required",
            direction="Input")
        param4.value = 5

        param5 = arcpy.Parameter(
            displayName="Average Stride Length (meters)",
            name="stride_avg", # Average length of a person's stride (a forward step).
            datatype="GPDouble",
            parameterType="Derived",
            direction="Output")
        param5.value = 1.2

        param6 = arcpy.Parameter(
            displayName="One piezoelectric tile (sq meters)",
            name="tile_sqm", # Size of a single pizoelectric tile. Combine to determine kinetic floor area.
            datatype="GPDouble",
            parameterType="Derived",
            direction="Output")
        param6.value = 0.25
        
        param7 = arcpy.Parameter(
            displayName="Output Feature Class",
            name="output_fc",
            datatype="DEFeatureClass",
            parameterType="Required",
            direction="Output")

        return [param0, param1, param2, param3, param4, param5, param6, param7]

    def isLicensed(self):
        """Set whether the tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""
        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter. This method is called after internal validation."""
        return

    def execute(self, parameters, messages):
        """The source code of the tool."""

        import arcpy
        import pandas as pd
        import datetime
        from datetime import datetime as dt

        arcpy.env.overwriteOutput = True

        # Get parameters
        buildings_layer = parameters[0].valueAsText
        gps_visits_layer = parameters[1].valueAsText
        district2_boundary = parameters[2].valueAsText
        coverage_pct = float(parameters[3].value)
        energy_per_step = float(parameters[4].value)
        outputbuildings_fc = parameters[7].valueAsText

        arcpy.env.workspace = arcpy.env.scratchGDB # temp storage, solves an overwrite conflict

        arcpy.AddMessage("Starting the kinetic floor energy analysis...")
        
        ####-----SPATIAL JOIN-----
        arcpy.AddMessage("Creating an output feature class...")
        if arcpy.Exists(outputbuildings_fc):
            arcpy.management.Delete(outputbuildings_fc)
        arcpy.management.CopyFeatures(buildings_layer, outputbuildings_fc)

        # Check geometry types and spatial references
        buildings_desc = arcpy.Describe(outputbuildings_fc)
        visits_desc = arcpy.Describe(gps_visits_layer)

        arcpy.AddMessage(f"Buildings geometry type: {buildings_desc.shapeType}")
        arcpy.AddMessage(f"GPS visits geometry type: {visits_desc.shapeType}")
        arcpy.AddMessage(f"Buildings spatial reference: {buildings_desc.spatialReference.name}")
        arcpy.AddMessage(f"GPS visits spatial reference: {visits_desc.spatialReference.name}")

        # Spatial join the GPS visits to buildings
        arcpy.AddMessage("Joining GPS visits to buildings...")
        visits_join = "Visits_Building_Join"
        arcpy.analysis.SpatialJoin(
            target_features=outputbuildings_fc,
            join_features=gps_visits_layer,
            out_feature_class=visits_join,
            join_operation="JOIN_ONE_TO_MANY",
            match_option="INTERSECT"
        )

        ####-----AGGREGATE THE VISITS-----
        arcpy.AddMessage("Processing GPS visit data...")
        # Updated field names for new data structure
        visit_fields = ["TARGET_FID", "tripid", "recordedat", "lat", "lon"]
        visit_data = []

        with arcpy.da.SearchCursor(visits_join, visit_fields) as cursor:
            for row in cursor:
                visit_data.append({
                    "OBJECTID": row[0],
                    "tripid": row[1], 
                    "recordedat": row[2], 
                    "latitude": row[3], 
                    "longitude": row[4]
                })

        df_visits = pd.DataFrame(visit_data)

        # Parse the ISO datetime format and extract hour
        if 'recordedat' in df_visits.columns:
            mask = df_visits['recordedat'].notna()
            if mask.any():
                # Parse ISO format datetime string (2023-05-21T10:33:59.592Z)
                try:
                    df_visits.loc[mask, 'datetime'] = pd.to_datetime(df_visits.loc[mask, 'recordedat'], 
                                                                   format='%Y-%m-%dT%H:%M:%S.%fZ', 
                                                                   errors='coerce')
                    # Alternative parsing if first format fails
                    still_null = df_visits['datetime'].isna() & mask
                    if still_null.any():
                        df_visits.loc[still_null, 'datetime'] = pd.to_datetime(df_visits.loc[still_null, 'recordedat'], 
                                                                             errors='coerce')
                    
                    # Extract hour from parsed datetime
                    df_visits.loc[mask, 'hour'] = df_visits.loc[mask, 'datetime'].dt.hour
                    df_visits['hour'] = df_visits['hour'].fillna(-1).astype(int)
                    
                    arcpy.AddMessage(f"Successfully parsed {mask.sum()} datetime records")
                except Exception as e:
                    arcpy.AddMessage(f"Warning: Could not parse datetime format: {str(e)}")
                    df_visits['hour'] = -1
            else:
                df_visits['hour'] = -1
        else:
            df_visits['hour'] = -1

        df_visits['visit'] = 1

        # Aggregate visits by building using tripid instead of uuid
        arcpy.AddMessage("Aggregating visits by building...")
        building_visits = df_visits.groupby('OBJECTID').agg(
            visits=('visit', 'sum'),
            uq_visitors=('tripid', 'nunique')  # Changed from uuid to tripid
        ).reset_index()

        ###-----ADD ALL FIELDS FIRST (BEFORE ANY CURSORS)-----
        arcpy.AddMessage("Adding analysis fields to the output...")
        
        # Define coverage levels
        coverage_levels = [10, 25, 50, 75, 90]
        
        # Add base fields first
        required_fields = [
            ["uq_visitors", "LONG"],
            ["t_visits", "LONG"],
            ["stride_avg", "DOUBLE"],
            ["tile_sqm", "DOUBLE"],
            ["GFArea", "DOUBLE"],
            ["KFArea", "DOUBLE"],
            ["footsteps", "LONG"],
            ["EnergyDaily_J", "DOUBLE"],
            ["EnergyDaily_kWh", "DOUBLE"],
            ["EnergyYearly_kWh", "DOUBLE"],
            ["Coverage_pct", "SHORT"],
        ]

        for field_name, field_type in required_fields:
            if field_name not in [f.name for f in arcpy.ListFields(outputbuildings_fc)]:
                arcpy.management.AddField(outputbuildings_fc, field_name, field_type)

        # Add coverage level fields
        arcpy.AddMessage("Adding multiple coverage level fields...")
        for pct in coverage_levels:
            field_name = f"KFloor_{pct}p"
            if field_name not in [f.name for f in arcpy.ListFields(outputbuildings_fc)]:
                arcpy.management.AddField(outputbuildings_fc, field_name, "DOUBLE")

        # Add energy fields for each coverage level
        for pct in coverage_levels:
            energy_field = f"Energy_{pct}p_kWh"
            if energy_field not in [f.name for f in arcpy.ListFields(outputbuildings_fc)]:
                arcpy.management.AddField(outputbuildings_fc, energy_field, "DOUBLE")

        # Create lookup dictionary
        dict_building_visit = dict(zip(building_visits['OBJECTID'],
                                    zip(building_visits['uq_visitors'],
                                        building_visits['visits'])))

        ###-----CALCULATE VALUES WITH SINGLE CURSOR-----
        arcpy.AddMessage("Calculating kinetic floor energy generation...")
        
        # Create the complete field list for the cursor
        coverage_fields = [f"KFloor_{pct}p" for pct in coverage_levels]
        energy_fields = [f"Energy_{pct}p_kWh" for pct in coverage_levels]
        
        cursor_fields = [
            "OBJECTID",        # 0
            "TFA",             # 1
            "NFloor",          # 2
            "stride_avg",      # 3
            "tile_sqm",        # 4
            "GFArea",          # 5
            "KFArea",          # 6
            "uq_visitors",     # 7
            "t_visits",        # 8
            "footsteps",       # 9
            "EnergyDaily_J",   # 10
            "EnergyDaily_kWh", # 11
            "EnergyYearly_kWh", # 12
            "Coverage_pct"     # 13
        ] + coverage_fields + energy_fields

        # Single cursor to update all values
        with arcpy.da.UpdateCursor(outputbuildings_fc, cursor_fields) as cursor:
            for row in cursor:
                objectid = row[0]

                # Set constants
                stride_avg = 1.2  # meters
                tile_sqm = 0.25   # sq meters
                row[3] = stride_avg
                row[4] = tile_sqm

                # calculate ground floor area
                if row[1] is not None and row[2] is not None and row[2] > 0:
                    GFArea = row[1] / row[2]  # TFA / NFloor
                else:
                    GFArea = 0
                row[5] = GFArea

                # calculate kinetic floor area for focus percentage
                KFArea = GFArea * (coverage_pct / 100)
                row[6] = KFArea

                # get visit data
                if objectid in dict_building_visit:
                    uq_visitors, t_visits = dict_building_visit[objectid]
                    row[7] = uq_visitors
                    row[8] = t_visits

                    # Calculate footsteps
                    footsteps = (KFArea / stride_avg) * t_visits
                    row[9] = footsteps
                else:
                    row[7] = 0
                    row[8] = 0
                    row[9] = 0
                    footsteps = 0

                # Calculate energy for focus percentage
                energy_joules = footsteps * energy_per_step
                row[10] = energy_joules

                energykwh = energy_joules / 3600000
                row[11] = energykwh

                energy_yearly_kwh = energykwh * 365
                row[12] = energy_yearly_kwh

                row[13] = coverage_pct

                # Calculate values for all coverage levels
                base_index = 14  # Where coverage fields start
                
                for i, pct in enumerate(coverage_levels):
                    # Calculate kinetic floor area for this coverage level
                    coverage_KFArea = GFArea * (pct / 100)
                    row[base_index + i] = coverage_KFArea
                    
                    # Calculate energy for this coverage level
                    if row[8] > 0:  # if there are visits
                        coverage_footsteps = (coverage_KFArea / stride_avg) * row[8]
                        coverage_energy_j = coverage_footsteps * energy_per_step
                        coverage_energy_kwh = coverage_energy_j / 3600000
                    else:
                        coverage_energy_kwh = 0
                    
                    # Set energy field (start after coverage fields)
                    row[base_index + len(coverage_levels) + i] = coverage_energy_kwh

                cursor.updateRow(row)

        ###-----SUMMARY STATISTICS-----
        arcpy.AddMessage("Calculating summary statistics...")
        stats_table = "KineticFloor_Summary"
        if arcpy.Exists(stats_table):
            arcpy.management.Delete(stats_table)

        arcpy.analysis.Statistics(
            outputbuildings_fc,
            stats_table,
            [["EnergyDaily_kWh", "SUM"], 
            ["EnergyYearly_kWh", "SUM"]]
        )
        
        # Read and display results
        with arcpy.da.SearchCursor(stats_table, ["SUM_EnergyDaily_kWh", "SUM_EnergyYearly_kWh"]) as cursor:
            for row in cursor:
                # Based on the coverage_pct input
                arcpy.AddMessage(f"Total Daily Energy Generation: {row[0]:.2f} kWh")
                arcpy.AddMessage(f"Total Yearly Energy Generation: {row[1]:.2f} kWh")
                break
        
        arcpy.AddMessage("Multiple coverage level analysis complete!")
        arcpy.AddMessage("Ready to create the dashboard!")
        return

    def postExecute(self, parameters):
        """This method takes place after outputs are processed and
        added to the display."""
        return
