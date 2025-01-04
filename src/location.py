from geopy.geocoders import Nominatim
import requests
from db import gateway_database

def rev_geocode(lat, long, gateway_id):
        # Initialize geolocator
        geolocator = Nominatim(user_agent="geoapi")

        # Reverse geocoding
        try:
            location = geolocator.reverse((lat, long))
            address = location.raw.get('address', {})
            road = address.get('road', '')
            place = address.get('suburb', '') or address.get('town', '') or address.get('village', '') or address.get('county', '')
            with gateway_database() as db:
                db.save_to_db("Unknown", gateway_id, f"{road}, {place}", "Unknown")  if place and road else "Location information not available"
            return f"{road}, {place}" if place and road else "Location information not available"
        except:
            # Define the API endpoint and parameters
            url = "https://nominatim.openstreetmap.org/reverse"
            params = {
                "lat": lat,
                "lon": long,
                "format": "json"
            }
            
            # Make the GET request
            response = requests.get(url, params=params, headers={"User-Agent": "MyApp"})
            response.raise_for_status()  # Raise an exception for HTTP errors
            
            # Parse the JSON response
            location_data = response.json()
            
            # Extract place name and postal code
            place_name = location_data.get("address", {}).get("village") or \
                        location_data.get("address", {}).get("town") or \
                        location_data.get("address", {}).get("city")
            db.save_to_db(lat, long, f"{place_name}")  if place_name else "Location information not available"
            return f"{place_name}" if place_name else "Location information not available"


    
