# 2025-Summer-Tokyo-Studio

## Nihonbashi Digital Twin for Urban Risk and Regeneration

This repository supports a digital twin system for **Nihonbashi, Tokyo**, as a strategic planning platform for urban revitalization and carbon neutrality.

It connects high-frequency urban risk and low-frequency urban regeneration through simulation, analytics, and visual interfaces.

Urban digital twins are used here as an **interactive GIS-based platform** to simulate and support decisions in complex, multi-stakeholder urban systems.


### 1. Urban Risk
- Focus: High-frequency urban problems such as flooding, heat wave or earthquake events for evacuations
- Method: Agent-based evacuation models, real-time sensing

### 2. Urban Regeneration
- Focus: Low-frequency urban problems such as urban design and redevelopment
- Method: 3D models, energy modeling, scenario planning

### 3. GIS-based interactive platform
- Output data is published to an **ArcGIS Online group**. [link](https://arcg.is/0zSCb9)
- Data is visualized through:
  - **Web Maps**
  - **Dashboards** 
  - **Experience Builder** [link](https://experience.arcgis.com/experience/3cd168b03d3a4c72b63bf71d72212cba)
  - **Interactive Heat-Responsive Shelter Routing Tool for Nihonbashi** [link](https://gt-2025-summer-tokyo-studio.github.io/heatwave_route/)




## Contributor Instructions: 

### 1. Access the ArcGIS Online Platform

- Go to:  [link](https://gtmaps.maps.arcgis.com/), sign in with **Georgia Tech SSO Login**
- Join the ArcGIS Online Group [link](https://arcg.is/0zSCb9)
---

### 2. Uploading Data Layers

Before uploading, ensure (if necessary):
- All spatial data are uniformly projected using WGS 84 or Japan National Coordinate System (JGD). (WGS84, JGD2000)
- Time fields are uniformly formatted to support event-driven and time-series analysis. (YYYY-MM-DDTHH:mm:ss.sssZ)
- Each layer is accompanied by a README-style metadata document, which specifies field definitions, data sources, collection time and unit specifications.
· Unified spatial ID fields (e.g. parcel number, building ID, etc.) are used for each layer to facilitate spatial connection and attribute merging. (Based on the existing building layer ID and used for joining related data.)

Items supported in ArcGIS Online: [link](https://doc.arcgis.com/en/arcgis-online/reference/supported-items.htm)
- Shapefiles (.shp)
- Raster Datasets (.tif, .img, etc.)
- GeoJSON
- CSV
- ...

Steps:
1. Go to ArcGIS Online → **Content > Add Item > From your computer or web**
2. Use clear file naming
3. Add description
4. Add tags:   
   - topic (`risk`, `regen`, `mobility`)
5. Go to the Group Content section, then click **Add items to group** to add existing layers with the group.
---

### 3. Uploading Simulation Models

Package files as a ZIP:
- `model.py`, `readme.txt`, `inputs/`, `outputs/`

Upload options:
- **GitHub**: Place the model in `/models/urban_risk/` or `/models/regeneration/` 
- Or, upload the ZIP to **Data 2025** in Teams and share the access link in if your file or folder is too large for GitHub

---

### 4. Visualization Integration

Add data/model output into the dashboard using the following methods
- 3D model to ArcGIS Urban (DAE, FBX, DWG, OBJ...) [link](https://doc.arcgis.com/en/urban/latest/help/help-external-layers.htm)
- Images, diagrams, or GIFs to be embedded in dashboard.
- Shapefile, Scene Layer, Geojson, CSV (with coordinates) to ArcGIS Online Web Map
- Map animation or large point/cloud data, use Kepler.gl

---

### 5. Metadata & Documentation

- Each upload should be listed in `data/metadata/` with:
  - Title, description, source, coordinate system, last updated
- Simulation models should include a `README.md` with:
  - Purpose, inputs and outputs, applicable scenarios, required tools, and how to run



## Tools and Technologies
- GIS: ArcGIS Pro, ArcGIS Online, Experience Builder
- Simulation: Rhino/Grasshopper, AnyLogic, Python (ABM, NetworkX)
- Data: 3D CityGML from PLATEAU, Street Networks from OSM, GPS Human Flows, Socioeconomic Data


## Repository Structure

```bash
2025-Summer-Tokyo-Studio/
├── data/                        # External data links + metadata
│   ├── metadata/                # Data schema, layer IDs, CRS, update logs
│   └── files/                   # Small files
│   └── README.md                # Data descriptions + download links: URLs to datasets (CityGML, OSM, e-Stat, etc.)
│
├── scripts/                     # Data analysis + visualization
│   ├── preprocess/              # Clean, merge, convert data
│   ├── analytics/               # KPI, scenario analysis
│   └── visualization/           # Charts, map layers, heatmaps
│
├── models/                      # Simulation models
│   ├── urban_risk/              # ABM for evacuation
│   ├── urban_regeneration/            # Urban form, carbon modeling, energy simulation
│   └── README.md                # Model objectives, inputs/outputs, run instructions
│
├── dashboards/                  # Interactive platform 
│   ├── README.md              # ArcGIS Dashboard + Experience Builder URLs
│
├── docs/                        # Project documentation
│   ├── use_cases.md             # Urban risk & regeneration scenarios
│   ├── architecture.md          # Digital twin system design overview
│   └── methodology.md           # Models, data integration, design logic
│
└── README.md
