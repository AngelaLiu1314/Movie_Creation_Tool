import json
import os
from io import BytesIO
import requests
from PIL import Image
import torch
from torchvision import transforms, models
from dotenv import load_dotenv
import pymongo
import certifi
from torchvision.models import ResNet18_Weights
from transformers import BlipProcessor, BlipForConditionalGeneration

from posterDetailsGenerate import analyze_poster_image, describe_image


# Load environment variables
load_dotenv()
mongodb_uri = os.getenv('Mongo_URI')

# MongoDB connection setup
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
    
imdbID = "tt2668120"
poster_json = analyze_poster_image(imdbID=imdbID)
print(poster_json)

db_client.close()
print("MongoDB connection closed.")