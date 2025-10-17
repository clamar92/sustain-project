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
from geopy.geocoders import OpenCage
from models import EnvironmentalData


map_bp = Blueprint('map', __name__, url_prefix='/map')


################################################################
########################### SPLIT MAP ##########################
################################################################

# Impostazioni di OSMnx
ox.settings.log_console = True
ox.settings.use_cache = True

# Inizializza il geocoder OpenCage
geolocator = OpenCage(api_key='542212d332054c58b252c81c50a6c2d1')  # Sostituisci con la tua chiave API OpenCage

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

def format_address(location):
    components = location.raw.get('components', {})
    house_number = components.get('house_number', '')
    road = components.get('road', '')
    #city = components.get('city', '')
    #state = components.get('state', '')
    #country = components.get('country', '')
    #return f"{house_number} {road}, {city}, {state}, {country}".strip(', ')
    return f"{house_number} {road}, Cagliari, Italy".strip(', ')


@map_bp.route('/dividiMappa', methods=['GET'])
def dividi_mappa():
    city = request.args.get('city', 'Cagliari, Italy')
    cell_size_meters = int(request.args.get('cell', 300))
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
    grid = grid[grid['intersection_area_ratio'] >= 0.7]

    fig, ax = plt.subplots(figsize=(10, 10))

    # Save valid rectangles to the database
    if save_variable:
        # Cancella tutti i campi della tabella Cell
        db.session.query(Cell).delete()
        db.session.commit()

        for _, row in grid.iterrows():
            rectangle = row.geometry
            minx, miny, maxx, maxy = rectangle.bounds
            center = rectangle.centroid

            try:
                location = geolocator.reverse((center.y, center.x), language='en')
                address = format_address(location) if location and location.address else 'Unknown'
            except Exception as e:
                address = 'Unknown'
                print(f"Geocoding error: {e}")


            if address != 'Unknown':
                new_rectangle = Cell(
                    top_left_lon=minx,
                    top_left_lat=maxy,
                    bottom_right_lon=maxx,
                    bottom_right_lat=miny,
                    air_quality=0,
                    address=address
                )
                db.session.add(new_rectangle)
        db.session.commit()

    # Traccia le aree residenziali
    residential_areas.boundary.plot(ax=ax, color="blue")

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
            #air_quality_status = 'LOW' if rect.air_quality == 0 else 'MEDIUM' if rect.air_quality == 1 else 'HIGH'
            # simulazione valore air quality
            airquality = random.randint(0, 2)
            air_quality_status = 'LOW' if airquality == 0 else 'MEDIUM' if airquality == 1 else 'HIGH'
            
            cells_data.append({
                'topLeft': {
                    'latitude': rect.top_left_lat,
                    'longitude': rect.top_left_lon
                },
                'bottomRight': {
                    'latitude': rect.bottom_right_lat,
                    'longitude': rect.bottom_right_lon
                },
                'air_quality': air_quality_status
            })
        
        return jsonify(cells_data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    


################################################################
########################## GET CHALLENGE #######################
################################################################
@map_bp.route('/getChallenges', methods=['GET'])
def get_challenges():
    try:
        # Query the database for all Cell entries
        #rectangles = Cell.query.all()
        
        # Controlla se ci sono almeno 4 rettangoli nel database
        #if len(rectangles) < 4:
        #    return jsonify({"error": "Not enough rectangles in the database"}), 500
        
        # Seleziona 4 rettangoli casuali
        #selected_rectangles = random.sample(rectangles, 4)

        # Query the database for the specific Cell entries
        rectangles = Cell.query.filter(Cell.id.in_([884, 893, 899, 906])).all()

        # Controlla se ci sono esattamente 4 rettangoli nel database
        if len(rectangles) != 4:
            return jsonify({"error": "The required rectangles are not available in the database"}), 500

        # Seleziona i rettangoli specificati
        selected_rectangles = rectangles

        
        challenges_data = []
        for rect in selected_rectangles:

            # simulazione valore air quality
            airquality = random.randint(0, 2)
            air_quality_status = 'LOW' if airquality == 0 else 'MEDIUM' if airquality == 1 else 'HIGH'

            #air_quality_status = 'LOW' if rect.air_quality == 0 else 'MEDIUM' if rect.air_quality == 1 else 'HIGH'

            # Genera un numero casuale di punti da 100 a 500
            points = random.randint(50, 100)

            # Utilizza le coordinate del centro del rettangolo come "waypoint"
            waypoint_latitude = (rect.top_left_lat + rect.bottom_right_lat) / 2
            waypoint_longitude = (rect.top_left_lon + rect.bottom_right_lon) / 2

            challenges_data.append({
                'cell': {
                    'topLeft': {
                        'latitude': rect.top_left_lat,
                        'longitude': rect.top_left_lon
                    },
                    'bottomRight': {
                        'latitude': rect.bottom_right_lat,
                        'longitude': rect.bottom_right_lon
                    },
                    'air_quality': air_quality_status
                },
                'points': points,
                'waypoint': {
                    'latitude': waypoint_latitude,
                    'longitude': waypoint_longitude
                },
                'address': rect.address
            })
        
        return jsonify(challenges_data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500





################################################################
############################# GET DATA #########################
################################################################

@map_bp.route('/getEnvironmentalData', methods=['GET'])
def get_environmental_data():
    try:
        # Recupera i parametri della richiesta
        start_time = request.args.get('from')
        end_time = request.args.get('to')

        if not start_time or not end_time:
            return jsonify({"error": "Missing 'from' or 'to' parameter"}), 400

        # Converte le stringhe in oggetti datetime
        from datetime import datetime
        try:
            start_dt = datetime.fromisoformat(start_time)
            end_dt = datetime.fromisoformat(end_time)
        except ValueError:
            return jsonify({"error": "Invalid datetime format. Use ISO 8601 (e.g. 2025-10-10T12:00:00)"}), 400

        # Query del database per intervallo di tempo
        results = (EnvironmentalData.query
                   .filter(EnvironmentalData.timestamp >= start_dt)
                   .filter(EnvironmentalData.timestamp <= end_dt)
                   .all())

        # Serializza i risultati
        data_list = []
        for record in results:
            data_list.append({
                'id': record.id,
                'user_id': record.user_id,
                'battery_capacity': record.battery_capacity,
                'battery_lifetime': record.battery_lifetime,
                'temperature': record.temperature,
                'humidity': record.humidity,
                'co2_scd41': record.co2_scd41,
                'co2_stc31c': record.co2_stc31c,
                'voc': record.voc,
                'pm1_0': record.pm1_0,
                'pm2_5': record.pm2_5,
                'pm4_0': record.pm4_0,
                'pm10': record.pm10,
                'timestamp': record.timestamp.isoformat()
            })

        return jsonify(data_list)

    except Exception as e:
        return jsonify({"error": str(e)}), 500
