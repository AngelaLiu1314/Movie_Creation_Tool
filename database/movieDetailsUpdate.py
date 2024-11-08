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
                image.save(img_byte_array, format="JPEG")
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

def update_documents_trainingPrompt(start_after_id = start_after_id):
    query = {"_id": {"$gt": ObjectId(start_after_id)}}
    cursor = movieDetails.find(query).sort("_id", 1).limit(10000)
    
    last_processed_id = None
    
    for document in cursor:
        try:
            imdbID = document.get("imdbID", "unknown")
            genres = document.get("genre", ["unknown"])  # Using first genre or 'unknown' if missing
            directors = document.get("director", "unknown")
            plot = document.get("plot", "No plot available")
            
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
                    {"_id": document["_id"]},
                    {"$set": {"trainingPrompt": training_prompt}}
                )
            except Exception as e:
                print(f"Error updating document {document['_id']} in MongoDB: {e}")
                traceback.print_exc()
                continue
            
            last_processed_id = document["_id"]
            
            print(f"Updated document {document['_id']} with training prompt.")
        except Exception as e:
            print(f"Error processing document {document.get('_id')}: {e}")
            traceback.print_exc()
            continue  

    if last_processed_id:
        print(f"Last processed ObjectId: {last_processed_id}")
        
    print("Batch processing complete.")

# uncomment the update function you want to run
# update_documents_posterImage()

start_after_id = "670d426128ad7f7da577c9cd"
update_documents_trainingPrompt(start_after_id)

# Close connection once finished
db_client.close()
print("MongoDB connection closed.")
