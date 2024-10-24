# DO NOT RUN UNTIL OPENAI API PROVIDED

import json
import os
from dotenv import load_dotenv
import pymongo
from bson.objectid import ObjectId
import requests
import openai
import pandas as pd
from posterDetailsGPT import get_movie_poster_details
import certifi

load_dotenv() 
mongodb_uri = os.getenv('Mongo_URI') #retrieve mongodb uri from .env file

# FastAPI server URL (modify if server is hosted elsewhere)
FASTAPI_URL = "http://127.0.0.1:8000"

try:
    client = pymongo.MongoClient(mongodb_uri,tlsCAFile=certifi.where()) # this creates a client that can connect to our DB
    db = client.get_database("movies") # this gets the database named 'movies'
    movieDetails = db.get_collection("movieDetails")
    posterDetails = db.get_collection("posterDetails")

    client.server_info() # forces client to connect to server
    print("Connected successfully to the 'Movies' database!")

except pymongo.errors.ConnectionFailure as e:
    print(f"Could not connect to MongoDB: {e}")
    exit(1)

def add_movie_poster_characteristics(imdbID: str):
    poster_url = f"{FASTAPI_URL}/posters/{imdbID}"

    # imdb id check to avoid redundant database storing
    existingPoster = posterDetails.find_one({"imdbID": imdbID})
    
    if existingPoster:
        print(f"Poster with imdbID {imdbID} already exists. Skipping insertion.")
        return
    else:
        # Query MongoDB for the movie by imdbID
        movie = movieDetails.find_one({"imdbID": imdbID})
        
        # Check if movie exists
        if not movie:
            print(f"Movie with IMDb ID {imdbID} not found in the database.")
            return
        
        # Extract posterLink and plot from the movie document
        plot = movie.get('plot', None)
        poster_link = movie.get('posterLink', None)

        if not poster_link or poster_link == "N/A" or not plot or plot == 'N/A':
            print(f"Poster link or plot not found for movie with IMDb ID {imdbID}.")
            return
        
        ''' just used for testing
        poster_characteristics = {
            "title": "sample movie 1",
            "tagline": "this is a sample poster",
            "colorScheme": [
                "AA0011",
                "BB1122",
                "CC2233"
            ],
            "font": [
                "Futura Bold",
                "Roboto Thin",
                "Papyrus"
            ],
            "atmosphere": "futuristic",
            "imageElement": {
                "main": "Man in a spacesuit",
                "background": "Mars-like planet"
            },
            "artStyle": "Realistic phtography",
            "periodStyle": "Modern"
        } 
        '''

        # Get poster detail using the imported custom function
        poster_characteristics = get_movie_poster_details(poster_link)

        # Add the IMDb ID, posterLink, and plot to the poster characteristics to match pydantic
        poster_characteristics["imdbID"] = imdbID
        poster_characteristics["posterLink"] = poster_link
        poster_characteristics["plot"] = plot

        # Make the POST request to create a record to the FastAPI server
        response = requests.post(poster_url, json=poster_characteristics)

        # Check the response and handle success/failure
        if response.status_code == 200:
            print(f"Successfully updated movie {imdbID} poster characteristics.")
            print(response.json())  # Print the updated movie details
        else:
            print(f"Failed to update movie {imdbID}. Status Code: {response.status_code}")
            print(response.text)  # Print the error message from the response

# Read in the main dataframe from which we'll get the IMDB IDs
mainDF = pd.read_csv(os.getenv("IMDB_PROCESSED_DF_PATH"), low_memory= False) # Please store your respective csv file path in your .env file


lastIndex = 0 # Please try to update it based on the printed lastIndex before closing out
dailyBatchSize = 1000

for imdbID in mainDF.imdb_id[lastIndex:lastIndex + dailyBatchSize]:
    try:
        add_movie_poster_characteristics(imdbID)
    except pymongo.errors.PyMongoError as e:
        print(f"An error occurred while adding the poster detail: {e}")
    

lastIndex += dailyBatchSize
print(lastIndex)


# add_movie_poster_characteristics("tt01") used for testing

client.close()
print("MongoDB connection closed.")