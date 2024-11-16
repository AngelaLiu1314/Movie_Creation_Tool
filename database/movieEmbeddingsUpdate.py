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
    
    
# Uncomment the update function you want to run

def update_schema(movie):
    updated_doc = {
        "movie_id": movie.get("movie_id"),
        "title": movie.get("title"),
        "imdbID": movie.get("imdbID"),
        "embedding": movie.get("embedding")
    }
    
    try:
        movieEmbeddings.update_one(
            {"_id": movie["_id"]},
            {"$set": updated_doc}
        )
        print(f"schema updated for {movie["_id"]}!")
    except Exception as e:
        print("Error processing", e)

update_method = "cursor"
# update_method = "id indexing"

if update_method == "id indexing":
    all_ids = [movie["_id"] for movie in movieEmbeddings.find({}, {"_id": 1}).sort("_id", 1)]
    batch_size = 100000
    batch_index = 200000

    for id in all_ids[batch_index:batch_index+batch_size]:
        batch_index += 1
        try:
            # Retrieve the full movie document using the current id
            movie = movieDetails.find_one({"_id": id})
            
            if movie:
                print() # Comment this line out when you run any of the update functions
            else:
                print(f"Movie with ID {id} not found.")
        except Exception as e:
            print("Error in processing the movie")
            continue

    print(f"New batch index: {batch_index}")
elif update_method == "cursor":
    cursor = movieEmbeddings.find({}, {"_id": 1, "movie_id": 1, "title": 1, "imdbID": 1, "embedding": 1})
    for movie in cursor:
        update_schema(movie)
    

# Close connection once finished
db_client.close()
print("MongoDB connection closed.")
