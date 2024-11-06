import json
import os
from dotenv import load_dotenv
import pymongo
from bson.objectid import ObjectId
import requests
import openai
import pandas as pd
from database.posterDetailsGenerate import get_movie_poster_details
import certifi

load_dotenv() 
mongodb_uri = os.getenv('Mongo_URI') #retrieve mongodb uri from .env file

# Connect to the database
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

# Define the deletion criteria. Deletion criteria is wrapped in a dictionary.
delete_criteria = {
    # Condition itself mimics the mongoDB shell commands
    "$or": [
        {"plot": "N/A"},          # Condition for "plot" field having "N/A"
        {"posterLink": "N/A"},     # Condition for "posterLink" field having "N/A"
        {"runtimeMinutes": 0},       # Condition for "runtimeMinutes being 0"
        {"posterImage": {"$exists": True}}
    ]
}

# Perform the delete operation
result = movieDetails.delete_many(delete_criteria)

# Log the number of deleted documents
print(f"Deleted {result.deleted_count} records that match the deletion criteria")

# Close the MongoDB connection
client.close()
print("MongoDB connection closed.")