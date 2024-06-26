# map/routes.py
import osmnx as ox
import matplotlib.pyplot as plt
import contextily as ctx
import geopandas as gpd
from shapely.geometry import box
import numpy as np
import random
from flask import request, Response, Blueprint, jsonify
import io
from models import db, Cell
import requests



map_bp = Blueprint('map', __name__, url_prefix='/map')



################################################################
########################### SPLIT MAP ##########################
################################################################


# Impostazioni di OSMnx
ox.settings.log_console = True
ox.settings.use_cache = True

# Funzione per calcolare la lunghezza di un grado di longitudine alla latitudine specifica
def meters_to_degrees(meters, lat):
    return meters / (111320 * np.cos(np.radians(lat)))

# Funzione per creare una griglia di rettangoli
def create_grid(residential_bounds, cell_size_degrees, crs):
    minx, miny, maxx, maxy = residential_bounds
    x_coords = np.arange(minx, maxx, cell_size_degrees)
    y_coords = np.arange(miny, maxy, cell_size_degrees)
    grid = []
    for x in x_coords:
        for y in y_coords:
            grid.append(box(x, y, x + cell_size_degrees, y + cell_size_degrees))
    return gpd.GeoDataFrame({'geometry': grid}, crs=crs)

# Funzione per calcolare l'area di intersezione
def area_of_intersection(rectangle, residential_union):
    intersection = rectangle.intersection(residential_union)
    return intersection.area / rectangle.area

@map_bp.route('/dividiMappa', methods=['GET'])
def dividi_mappa():
    city = request.args.get('city', 'Cagliari, Italy')
    cell_size_meters = int(request.args.get('cell', 400))
    save_variable = bool(request.args.get('save', 0))

    # Scarica le geometrie delle aree residenziali
    tags = {'landuse': 'residential'}
    residential_areas = ox.geometries_from_place(city, tags)

    # Filtra solo i poligoni (le aree residenziali)
    residential_areas = residential_areas[residential_areas.geometry.geom_type == 'Polygon']

    # Converti in un sistema di coordinate proiettate (ad esempio, UTM zone 32N)
    residential_areas_projected = residential_areas.to_crs(epsg=32632)

    # Calcola la media della latitudine delle aree residenziali per una conversione più precisa
    avg_lat = residential_areas_projected.geometry.centroid.to_crs(epsg=4326).y.mean()

    # Calcola la dimensione della cella in gradi
    cell_size_degrees = meters_to_degrees(cell_size_meters, avg_lat)

    # Crea la griglia di rettangoli
    grid = create_grid(residential_areas.total_bounds, cell_size_degrees, residential_areas.crs)

    # Filtra i rettangoli che hanno almeno il 20% dell'area in zone residenziali
    residential_union = residential_areas.unary_union
    grid['intersection_area_ratio'] = grid.geometry.apply(lambda x: area_of_intersection(x, residential_union))
    grid = grid[grid['intersection_area_ratio'] >= 0.2]

    fig, ax = plt.subplots(figsize=(10, 10))


    # Save valid rectangles to the database
    if save_variable:
        for _, row in grid.iterrows():
            rectangle = row.geometry
            minx, miny, maxx, maxy = rectangle.bounds
            new_rectangle = Cell(
                top_left_lon=minx,
                top_left_lat=maxy,
                bottom_right_lon=maxx,
                bottom_right_lat=miny,
                valore=0
            )
            db.session.add(new_rectangle)
        db.session.commit()


    # Traccia le aree residenziali
    residential_areas.boundary.plot(ax=ax, color="blue")

    # Colori casuali con trasparenza
    #colors = ['green', 'red', 'yellow']
    #for geom in grid.geometry:
    #    color = random.choice(colors)
    #    x, y = geom.exterior.xy
    #    ax.fill(x, y, color=color, alpha=0.5)  # alpha per la trasparenza

    # Traccia i bordi dei rettangoli della griglia
    grid.boundary.plot(ax=ax, edgecolor='red')

    # Aggiungi l'immagine satellitare di sfondo
    ctx.add_basemap(ax, crs=residential_areas.crs.to_string(), source=ctx.providers.Esri.WorldImagery)

    # Imposta i limiti del grafico con un margine del 5%
    minx, miny, maxx, maxy = residential_areas.total_bounds
    x_margin = (maxx - minx) * 0.05
    y_margin = (maxy - miny) * 0.05
    ax.set_xlim(minx - x_margin, maxx + x_margin)
    ax.set_ylim(miny - y_margin, maxy + y_margin)

    ax.set_xlabel('Longitudine')
    ax.set_ylabel('Latitudine')
    #ax.set_title(f'Divisione centro abitato di {city} con griglia')

    # Salva la figura in un buffer
    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    plt.close(fig)

    return Response(buf.getvalue(), mimetype='image/png')



################################################################
############################ GET CELL ##########################
################################################################

@map_bp.route('/getAllCells', methods=['GET'])
def get_all_cells():
    try:
        # Query the database for all Rectangle entries
        rectangles = Cell.query.all()
        
        # Serialize the data
        cells_data = []
        for rect in rectangles:
            cells_data.append({
                'id': rect.id,
                'top_left_lon': rect.top_left_lon,
                'top_left_lat': rect.top_left_lat,
                'bottom_right_lon': rect.bottom_right_lon,
                'bottom_right_lat': rect.bottom_right_lat,
                'valore': rect.valore
            })
        
        return jsonify(cells_data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    


################################################################
########################## GET CHALLENGE #######################
################################################################

# Function to get the address from coordinates
def get_address_from_coordinates(lat, lon):
    url = f"https://nominatim.openstreetmap.org/reverse?format=json&lat={lat}&lon={lon}&addressdetails=1"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        address = data.get('address', {})
        road = address.get('road', 'Unknown road')
        house_number = address.get('house_number', 'No number')
        return f"{road}, {house_number}"
    else:
        return "Address not found"


@map_bp.route('/getChallenges', methods=['GET'])
def get_challenges():
    try:
        # Query the database for all Rectangle entries
        rectangles = Cell.query.all()
        
        # Select 4 random rectangles
        if len(rectangles) < 4:
            return jsonify({"error": "Not enough rectangles in the database"}), 500
        
        selected_rectangles = random.sample(rectangles, 4)
        
        challenges_data = []
        for rect in selected_rectangles:
            center_lat = (rect.top_left_lat + rect.bottom_right_lat) / 2
            center_lon = (rect.top_left_lon + rect.bottom_right_lon) / 2
            address = get_address_from_coordinates(center_lat, center_lon)
            challenges_data.append({
                'id': rect.id,
                'top_left_lon': rect.top_left_lon,
                'top_left_lat': rect.top_left_lat,
                'bottom_right_lon': rect.bottom_right_lon,
                'bottom_right_lat': rect.bottom_right_lat,
                'valore': rect.valore,
                'address': address
            })
        
        return jsonify(challenges_data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
