import json
import os
from dotenv import load_dotenv
import pymongo
from bson.objectid import ObjectId
import requests
import openai
import pandas as pd
from posterDetailFunction import get_movie_poster_details

load_dotenv() 
mongodb_uri = os.getenv('Mongo_URI') #retrieve mongodb uri from .env file

# FastAPI server URL (modify if server is hosted elsewhere)
FASTAPI_URL = "http://127.0.0.1:8000"

try:
    client = pymongo.MongoClient(mongodb_uri) # this creates a client that can connect to our DB
    db = client.get_database("movies") # this gets the database named 'Movies'
    movieDetails = db.get_collection("movieDetails")

    client.server_info() # forces client to connect to server
    print("Connected successfully to the 'Movies' database!")

except pymongo.errors.ConnectionFailure as e:
    print(f"Could not connect to MongoDB: {e}")
    exit(1)

def update_movie_poster_characteristics(imdbID: str):
    patch_url = f"{FASTAPI_URL}/movies/{imdbID}/posterCharacteristics"
    
    # Query MongoDB for the movie by imdbID
    movie = movieDetails.find_one({"imdbID": imdbID})
    
    # Check if movie exists
    if not movie:
        print(f"Movie with IMDb ID {imdbID} not found in the database.")
        return
    
    # Extract posterLink from the movie document
    poster_link = movie.get('posterLink', None)

    if not poster_link:
        print(f"Poster link not found for movie with IMDb ID {imdbID}.")
        return

    # Get poster detail using the imported custom function
    poster_characteristics = get_movie_poster_details(poster_link)

    # Make the PATCH request to the FastAPI server
    response = requests.patch(patch_url, json=poster_characteristics)

    # Check the response and handle success/failure
    if response.status_code == 200:
        print(f"Successfully updated movie {imdbID} poster characteristics.")
        print(response.json())  # Print the updated movie details
    else:
        print(f"Failed to update movie {imdbID}. Status Code: {response.status_code}")
        print(response.text)  # Print the error message from the response