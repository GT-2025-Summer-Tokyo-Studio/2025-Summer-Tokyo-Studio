# Kinetic Floor Energy Calculator

An ArcGIS Python Toolbox for calculating potential energy generation from kinetic floor systems based on building foot traffic patterns.

## Overview

This tool analyzes GPS visit data to estimate the energy generation potential of piezoelectric floor tiles in buildings. It calculates daily and yearly energy output based on visitor patterns and configurable coverage areas.

## Features

- **Spatial Analysis**: Joins GPS visit data with building footprints
- **Multi-Coverage Analysis**: Calculates energy potential at 10%, 25%, 50%, 75%, and 90% floor coverage
- **Comprehensive Metrics**: Provides visitor counts, footstep estimates, and energy calculations
- **Summary Statistics**: Generates district-wide energy generation totals

## Derived Datasets

### Nihonbashi_GT_TokyoStudio_2023.gdb

The layers used:
- Buildings_District2
- GPS_Weekday

## Software Requirements

- ArcGIS Pro or ArcMap with Spatial Analyst extension
- Python 3.x with the following packages:
  - arcpy (included with ArcGIS Pro)
  - pandas
  - datetime
