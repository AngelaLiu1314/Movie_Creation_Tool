import os
from dotenv import load_dotenv
import openai
import json
from google.cloud import vision
import pymongo
import certifi
from datetime import datetime

load_dotenv() 
mongodb_uri = os.getenv('Mongo_URI') #retrieve mongodb uri from .env file

try:
    client = pymongo.MongoClient(mongodb_uri, tlsCAFile=certifi.where()) # this creates a client that can connect to our DB
    db = client.get_database("movies") # this gets the database named 'Movies'
    movieDetails = db.get_collection("movieDetails")
    posterDetails = db.get_collection("posterDetails")

    client.server_info() # forces client to connect to server
    print("Connected successfully to the 'Movies' database!")

except pymongo.errors.ConnectionFailure as e:
    print(f"Could not connect to MongoDB: {e}")
    exit(1)

print("GOOGLE_APPLICATION_CREDENTIALS:", os.getenv("GOOGLE_APPLICATION_CREDENTIALS"))

try:
    client = vision.ImageAnnotatorClient()
    print("Client initialized successfully.")
except Exception as e:
    print(f"Failed to initialize client: {e}")

def analyze_poster_image(poster_link):
    """
    Analyzes a poster image using Google Vision API and returns characteristics.
    """
    print("Starting analyze_poster_image function...")
    
    vision_client = vision.ImageAnnotatorClient()
    image = vision.Image()
    image.source.image_uri = poster_link
    
    # Initialize dictionary to hold extracted poster characteristics
    poster_characteristics = {}
    
    # Identifying color scheme using color response
    try:
        color_response = vision_client.image_properties(image=image)
        print("Color response received:", color_response)
        color_scheme = []
        for color_info in color_response.image_properties_annotation.dominant_colors.colors:
            rgb = color_info.color
            hex_code = '#{:02x}{:02x}{:02x}'.format(int(rgb.red), int(rgb.green), int(rgb.blue))
            color_scheme.append(hex_code)
        poster_characteristics["colorScheme"] = color_scheme
    except Exception as e:
        print("Error in color analysis:", e)

    # Identifying image elements using object response
    # try:
    #     object_response = vision_client.object_localization(image=image)
    #     main_elements = [obj.name for obj in object_response.localized_object_annotations]
    #     poster_characteristics["mainElements"] = main_elements
    # except Exception as e:
    #     print("Error in label detection:", e)
    
    # Run label detection
    try:
        label_response = vision_client.label_detection(image=image)
        labels = [label.description for label in label_response.label_annotations]
        poster_characteristics["Labels"] = labels
    except Exception as e:
        print("Error in web labeling")
    
    # Identifying taglines using text_response    
    try:
        text_response = vision_client.text_detection(image=image)
        print("Text response received:", text_response)
        texts = [text.description for text in text_response.text_annotations]
        poster_characteristics["tagline"] = texts[0] if texts else None
    except Exception as e:
        print("Error in text detection:", e)

    # Getting the decade of the movie
    try:
        movie = movieDetails.find_one({"posterLink": poster_link})
        if movie:
            release_date = movie["releaseDate"]
            date_obj = datetime.strptime(release_date, "%Y-%m-%d")
            release_year = str(date_obj.year)
            release_decade = release_year[0:3] + "0"
            poster_characteristics["decade"] = release_decade
    except Exception as e:
        print("Error in getting the movie:", e)
        
    return poster_characteristics

test_link = "https://m.media-amazon.com/images/M/MV5BNzY0ZTlhYzgtOTgzZC00ZTg2LTk4NTEtZDllM2E2NGE5Njg2XkEyXkFqcGc@._V1_SX300.jpg"
poster_characteristics = analyze_poster_image(test_link)
print(poster_characteristics)