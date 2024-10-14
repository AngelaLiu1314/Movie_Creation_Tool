import json
import os
from dotenv import load_dotenv
import pymongo
from bson.objectid import ObjectId
import requests
import openai
import pandas as pd

load_dotenv() 
mongodb_uri = os.getenv('MONGODB_URI') #retrieve mongodb uri from .env file

try:
    client = pymongo.MongoClient(mongodb_uri) # this creates a client that can connect to our DB
    db = client.get_database("movies") # this gets the database named 'Movies'
    movieDetails = db.get_collection("movieDetails")

    client.server_info() # forces client to connect to server
    print("Connected successfully to the 'Movies' database!")

except pymongo.errors.ConnectionFailure as e:
    print(f"Could not connect to MongoDB: {e}")
    exit(1)

# We need this separate file for updating the collection because the poster details will be added after the fact