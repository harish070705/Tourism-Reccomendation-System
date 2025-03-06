import requests
import json
import pandas as pd
import numpy as np
import sys

# LocationIQ API key
api_key = 'pk.3afcc65437a2bab5b6dd4ff20959918e'

# The place to search
place = sys.argv[1]  # Get the search query from command line

# Construct the URL for LocationIQ API
url = f"https://us1.locationiq.com/v1/search.php?key={api_key}&q={place}&format=json"

# Make the API request to get the coordinates for the place
response = requests.get(url)

# Check if the request was successful
if response.status_code == 200:
    # Parse the JSON response
    data = response.json()
    
    # Use the most relevant result (e.g., the first result)
    lat = float(data[0]['lat'])
    lon = float(data[0]['lon'])
else:
    print(f"Error: Unable to fetch data (Status code: {response.status_code})")
    exit()

# Load hotel data
hotel_data_path = r"data\cleaned_hotel_info.csv"
hotels = pd.read_csv(hotel_data_path)

# Step 1: Remove rows with 'nil' or missing latitude or longitude
hotels = hotels.dropna(subset=['latitude', 'longitude'])

# Step 2: Ensure the latitude and longitude columns are floats
hotels['latitude'] = pd.to_numeric(hotels['latitude'], errors='coerce')
hotels['longitude'] = pd.to_numeric(hotels['longitude'], errors='coerce')

# Step 3: Remove rows that have invalid (NaN) values after conversion
hotels = hotels.dropna(subset=['latitude', 'longitude'])

# Step 4: Function to calculate Pythagorean distance
def calculate_distance(lat1, lon1, lat2, lon2):
    return np.sqrt((lat1 - lat2)**2 + (lon1 - lon2)**2)

# Step 5: Calculate the distance between the given coordinates and each hotel
hotels['distance'] = hotels.apply(lambda row: calculate_distance(lat, lon, row['latitude'], row['longitude']), axis=1)

# Step 6: Sort the DataFrame by the 'distance' column
hotels_sorted = hotels.sort_values(by='distance')

# Step 7: Return the top 3 nearest hotels as a JSON response
top_3_hotels = hotels_sorted[['hotel_name', 'latitude', 'longitude', 'distance', 'hotel_rating', 'price']].head(3)
top_3_hotels_json = top_3_hotels.to_dict(orient='records')

# Returning the JSON response
print(json.dumps(top_3_hotels_json))
