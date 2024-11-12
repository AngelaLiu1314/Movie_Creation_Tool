import json
import os
import traceback
from dotenv import load_dotenv
import pymongo
from bson.objectid import ObjectId
import requests
import openai
import pandas as pd
import certifi
from PIL import Image
from io import BytesIO

load_dotenv() 
mongodb_uri = os.getenv('Mongo_URI') #retrieve mongodb uri from .env file

try:
    db_client = pymongo.MongoClient(mongodb_uri, tlsCAFile=certifi.where()) # this creates a client that can connect to our DB
    db = db_client.get_database("movies") # this gets the database named 'Movies'
    movieDetails = db.get_collection("movieDetails")

    db_client.server_info() # forces client to connect to server
    print("Connected successfully to the 'Movies' database!")
    
    posterDetails = db.get_collection("posterDetails")
    print("Connected successfully to the 'Posters' database!")

except pymongo.errors.ConnectionFailure as e:
    print(f"Could not connect to MongoDB: {e}")
    exit(1)

# Read in the main dataframe from which we'll get the IMDB IDs
mainDF = pd.read_csv(os.getenv("IMDB_PROCESSED_DF_PATH"), low_memory= False) # Please store your respective csv file path in your .env file

start_after_id = ObjectId("670c676c660f80b2ceeec2a4")

def update_documents_posterImage(movie):
    poster_link = movie.get("posterLink")

    if poster_link and poster_link != "N/A":
        response = requests.get(poster_link)
        try:
            image = Image.open(BytesIO(response.content))
            # Converting to bytes
            img_byte_array = BytesIO()
            image.save(img_byte_array, format="JPEG")
            img_data = img_byte_array.getvalue()

            # Updating document
            movieDetails.update_one(
                {"_id": movie["_id"]},
                {"$set": {"posterImage": img_data}}
            )
            
            print(f"Processed document ID: {movie["_id"]}")
            
        except:
            movieDetails.update_one(
                {"_id": movie["_id"]},
                {"$set": {"posterImage": "N/A"}}
            )
            print("Couldn't get the image. Storing as N/A")

def update_documents_trainingPrompt(movie):
    try:
        imdbID = movie["imdbID"]
        genres = movie["genre"]
        directors = movie["director"]
        plot = movie["plot"]
        
        if len(genres) > 1:
            genre_str = ", ".join(genres)
        else:
            genre_str = str(genres[0])
    
        if isinstance(directors, list):
            if len(directors) == 1:
                director_str = directors[0]
            elif len(directors) == 2:
                director_str = f"{directors[0]} and {directors[1]}"
            else:
                director_str = ", ".join(directors[:-1]) + f", and {directors[-1]}"
        else:
            director_str = directors

        # Generate the training prompt
        training_prompt = f"{genre_str} movie directed by {director_str}. Plot: {plot}"

        try:
            movieDetails.update_one(
                {"_id": movie["_id"]},
                {"$set": {"trainingPrompt": training_prompt}}
            )
        except Exception as e:
            print(f"Error updating document {movie['_id']} in MongoDB: {e}")
            traceback.print_exc()
        
        print(f"Updated document {movie['_id']} with training prompt.")
    except Exception as e:
        print(f"Error processing document {movie.get('_id')}: {e}")
        traceback.print_exc()
        
    print("Batch processing complete.")

# Uncomment the update function you want to run

start_after_id = "670fd09e2ecae278089a940a"

query_filter = {"_id": {"$gte": ObjectId(start_after_id)}}
batch_size = 500
cursor = movieDetails.find(query_filter).sort("_id", 1).limit(batch_size)

while True:
    batch = list(cursor)
    if not batch:
        break
    for movie in batch:
        try:
            # update_documents_posterImage()
            update_documents_trainingPrompt(movie)
        except Exception as e:
            print("Error in processing the movie")
            continue
    

# Close connection once finished
db_client.close()
print("MongoDB connection closed.")
