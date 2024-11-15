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
import torch
from torchvision import transforms, models
from torchvision.models import ResNet18_Weights
from transformers import BlipProcessor, BlipForConditionalGeneration
import datetime

load_dotenv() 
mongodb_uri = os.getenv('Mongo_URI') #retrieve mongodb uri from .env file

try:
    db_client = pymongo.MongoClient(mongodb_uri, tlsCAFile=certifi.where()) # this creates a client that can connect to our DB
    db = db_client.get_database("movies") # this gets the database named 'Movies'
    db_client.server_info() # forces client to connect to server
    
    movieDetails = db.get_collection("movieDetails")
    print("Connected successfully to the 'Movies' database!")
    
    movieEmbeddings = db.get_collection("movieEmbeddings")
    print("Connected successfully to the 'Movie Embeddings' database!")

except pymongo.errors.ConnectionFailure as e:
    print(f"Could not connect to MongoDB: {e}")
    exit(1)

def add_style(movie):
    print()

def add_release_year(movie):
    release_date = movie.get("releaseDate")
    if release_date:
        try:
            date_obj = datetime.datetime.strptime(release_date, "%Y-%m-%d")
            release_year = str(date_obj.year)
        except ValueError:
            print(f"Incorrect date format for movie ID {movie['_id']}. Skipping.")
            return
    else:
        print(f"No release date for movie ID {movie['_id']}. Skipping.")
        return

    try:
        movieEmbeddings.update_one(
            {"movie_id": movie["_id"]},
            {"$set": {"releaseYear": release_year}}
        )
        print(f"release year for movie_id: {movie['_id']} added")
        
    except Exception as e:
        print(f"Error updating document {movie['_id']} in MongoDB: {e}")
        traceback.print_exc()
    
    
# Uncomment the update function you want to run

all_ids = [movie["_id"] for movie in movieDetails.find({}, {"_id": 1}).sort("_id", 1)]
batch_size = 100000
batch_index = 100000

for id in all_ids[batch_index:batch_index+batch_size]:
    batch_index += 1
    try:
        # Retrieve the full movie document using the current id
        movie = movieDetails.find_one({"_id": id})
        
        if movie:
            # add_style(movie)
            add_release_year(movie)
            # print() # Comment this line out when you run any of the update functions
        else:
            print(f"Movie with ID {id} not found.")
    except Exception as e:
        print("Error in processing the movie")
        continue

print(f"New batch index: {batch_index}")
    

# Close connection once finished
db_client.close()
print("MongoDB connection closed.")
