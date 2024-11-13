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
    print()
    
# Uncomment the update function you want to run

start_after_id = "672e783692eedf81f91b1b6a"

query_filter = {"_id": {"$gte": ObjectId(start_after_id)}}
batch_size = 300000
cursor = movieDetails.find(query_filter).sort("_id", 1).limit(batch_size)

while True:
    batch = list(cursor)
    if not batch:
        break
    for movie in batch:
        try:
            # update_documents_posterImage(movie)
            # classify_style(movie)
            # update_documents_trainingPrompt(movie)
            print() # Comment this line out when you run any of the update functions
        except Exception as e:
            print("Error in processing the movie")
            continue
    

# Close connection once finished
db_client.close()
print("MongoDB connection closed.")
