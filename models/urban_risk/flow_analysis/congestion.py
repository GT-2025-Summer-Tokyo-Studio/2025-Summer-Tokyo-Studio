import pandas as pd
import geopandas as gpd
from shapely import wkt
from shapely.geometry import LineString
import folium


df = pd.read_csv("congestion.csv")
evac_data = pd.read_csv("evac_shelters.csv")

def parse_linestring_z(wkt_str):
    return LineString([(x, y) for x, y, *_ in wkt.loads(wkt_str.replace(" Z", "")).coords])

df["geometry"] = df["geometry"].apply(parse_linestring_z)

gdf = gpd.GeoDataFrame(df, geometry="geometry", crs="EPSG:4326")

center = gdf.union_all().centroid
congested = folium.Map(location=[center.y, center.x], zoom_start=15, tiles="CartoDBPositron")

for _, row in gdf.iterrows():
    coords = [(pt[1], pt[0]) for pt in row.geometry.coords]
    folium.PolyLine(
        coords,
        color='red',
        weight=7,
        opacity=0.8,
        tooltip=row.get("Name", "Line")
    ).add_to(congested)

evac_layer = folium.FeatureGroup(name="Evacuation Centers")
min_cap = evac_data['Capacity'].min()
max_cap = evac_data['Capacity'].max()
def scale_radius(capacity, min_cap, max_cap, min_radius=12, max_radius=24):
    if max_cap == min_cap:
        return min_radius
    return min_radius + (capacity - min_cap) / (max_cap - min_cap) * (max_radius - min_radius)
for _, row in evac_data.iterrows():
    radius = scale_radius(row['Capacity'], min_cap, max_cap)
    fill_color = 'black' if row['Type'] == 'OG' else 'limegreen'
    popup_content = f"""
    <b>{row['Name']}</b><br>
    Capacity: {row['Capacity']:,}"""
    folium.CircleMarker(
        location=(row['latitude'], row['longitude']),
        radius=radius,
        color='black',
        fill=True,
        fill_color=fill_color,
        weight=2,
        fill_opacity=0.8,
        tooltip=f"{row['Name']} (Capacity: {row['Capacity']})",
        popup=folium.Popup(popup_content, max_width=300)
    ).add_to(evac_layer)
evac_layer.add_to(congested)

congested.save("congestion_map.html")



