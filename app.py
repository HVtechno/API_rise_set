from flask import Flask, request, jsonify
import requests
from urllib.parse import quote
import pytz
from datetime import datetime, timedelta
from opencage.geocoder import OpenCageGeocode
import os
from dotenv import load_dotenv
import json

load_dotenv()

app = Flask(__name__)

#call environment variables
OPENCAGE_API_KEY = os.getenv('OPENCAGE_API_KEY')
Google_api_key = os.getenv('Google_api_key')
OPEN_WEATHER_KEY = os.getenv('OPEN_WEATHER_KEY')

# Initialize the geocoder
geocoder = OpenCageGeocode(OPENCAGE_API_KEY)

def convert_to_local_time(utc_time, country):
    geocoding_url = f'https://api.opencagedata.com/geocode/v1/json?q={quote(country)}&key={OPENCAGE_API_KEY}'
    geocoding_response = requests.get(geocoding_url)
    geocoding_data = geocoding_response.json()
    
    if 'results' in geocoding_data and len(geocoding_data['results']) > 0:
        country_timezone = geocoding_data['results'][0]['annotations']['timezone']['name']
        local_timezone = pytz.timezone(country_timezone)
        utc_time = datetime.strptime(utc_time, '%I:%M:%S %p')
        local_time = utc_time.replace(tzinfo=pytz.utc).astimezone(local_timezone)
        return local_time.strftime('%I:%M %p')
    else:
        return "Timezone information not available for the selected country"
    

def get_latitude_longitude(country):
    geocoding_url = f'https://api.opencagedata.com/geocode/v1/json?q={quote(country)}&key={OPENCAGE_API_KEY}'
    geocoding_response = requests.get(geocoding_url)
    geocoding_data = geocoding_response.json()

    if 'results' in geocoding_data and len(geocoding_data['results']) > 0:
        latitude = geocoding_data['results'][0]['geometry']['lat']
        longitude = geocoding_data['results'][0]['geometry']['lng']
        return latitude, longitude
    else:
        return None, None

def get_city_state_from_lat_lng(lat, lng, Google_api_key):
    base_url = "https://maps.googleapis.com/maps/api/geocode/json"
    params = {
        "latlng": f"{lat},{lng}",
        "key": Google_api_key,
    }

    city = ""
    state = ""

    try:
        response = requests.get(base_url, params=params)
        data = response.json()

        if data["status"] == "OK":
            for result in data["results"]:
                for component in result["address_components"]:
                    if "locality" in component["types"]:
                        city = component["long_name"]
                    if "administrative_area_level_1" in component["types"]:
                        state = component["short_name"]
                return city, state
        else:
            print("Geocoding request failed with status:", data["status"])
            return None, None

    except requests.exceptions.RequestException as e:
        print("Request error:", e)
        return None, None
    
@app.route('/get_sunrise_sunset')
def get_sunrise_sunset():
    date = request.args.get('date')
    country = request.args.get('country')

    if not date or not country:
        return jsonify({'error': 'Date and country are required parameters.'}), 400

    latitude, longitude = get_latitude_longitude(country)

    if latitude is None or longitude is None:
        return jsonify({'error': 'Unable to geocode the selected country'})

    url = f'https://api.sunrise-sunset.org/json?lat={latitude}&lng={longitude}&date={date}'
    response = requests.get(url)

    data = response.json()
    sunrise = data['results']['sunrise']
    sunset = data['results']['sunset']

    country_city, country_state = get_city_state_from_lat_lng(latitude, longitude, Google_api_key)
    sunrise_local = convert_to_local_time(sunrise, country)
    sunset_local = convert_to_local_time(sunset, country)

    response_json = {
        'sunrise': sunrise_local,
        'sunset': sunset_local
    }

    if country_city:
        response_json['city'] = country_city

    if country_state:
        response_json['state'] = country_state

    return jsonify(response_json)
    
if __name__ == '__main__':
    app.run(debug=True)