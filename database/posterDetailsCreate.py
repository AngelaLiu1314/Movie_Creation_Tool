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

from posterDetailsGenerate import analyze_poster_image


# Load environment variables
load_dotenv()
mongodb_uri = os.getenv('Mongo_URI')

# MongoDB connection setup
try:
    db_client = pymongo.MongoClient(mongodb_uri, tlsCAFile=certifi.where())
    db = db_client.get_database("movies")
    movieDetails = db.get_collection("movieDetails")
    posterDetails = db.get_collection("posterDetails")
    print("Connected successfully to the 'Movies' database!")
except pymongo.errors.ConnectionFailure as e:
    print(f"Could not connect to MongoDB: {e}")
    exit(1)

imdbID = "tt2668120"
poster_json = analyze_poster_image(imdbID=imdbID)
print(poster_json)

db_client.close()
print("MongoDB connection closed.")