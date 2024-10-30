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
from PIL import Image
from io import BytesIO

load_dotenv() 
mongodb_uri = os.getenv('Mongo_URI') #retrieve mongodb uri from .env file

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

# Read in the main dataframe from which we'll get the IMDB IDs
mainDF = pd.read_csv(os.getenv("IMDB_PROCESSED_DF_PATH"), low_memory= False) # Please store your respective csv file path in your .env file

start_after_id = ObjectId("670c676c660f80b2ceeec2a4")

def update_documents_posterImage(batch_size = 100000, start_after_id= start_after_id):
    query = {"_id": {"$gt": start_after_id}}
    cursor = movieDetails.find(query).limit(batch_size)

    batch_processed = False

    for document in cursor:
        poster_link = document.get("posterLink")

        if poster_link and poster_link != "N/A":
            response = requests.get(poster_link)
            try:
                image = Image.open(BytesIO(response.content))
                # Converting to bytes
                img_byte_array = BytesIO()
                image.save(img_byte_array, format="PNG")
                img_data = img_byte_array.getvalue()

                # Updating document
                movieDetails.update_one(
                    {"_id": document["_id"]},
                    {"$set": {"posterImage": img_data}}
                )
                
                print(f"Processed document ID: {document["_id"]}")
                
            except:
                movieDetails.update_one(
                    {"_id": document["_id"]},
                    {"$set": {"posterImage": "N/A"}}
                )
                print("Couldn't get the image. Storing as N/A")
        
        # update the last processed ID
        start_after_id = document["_id"]
        batch_processed = True

    if not batch_processed:
        print("No more documents to process.")
    else:
        print(f"Last processed start_after_id: {start_after_id}")
    ''''''

# run update function
update_documents_posterImage()

# Close connection once finished
client.close()
print("MongoDB connection closed.")
