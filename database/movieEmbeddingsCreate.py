import json
import os
from dotenv import load_dotenv
import pymongo
from bson.objectid import ObjectId
import requests
import openai
import pandas as pd
import certifi
from sentence_transformers import SentenceTransformer
import numpy as np
import faiss

# DB Connection

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
    
    movieEmbeddings = db.get_collection("movieEmbeddings")
    print("Connected successfully to the 'Movie Embeddings' database!")

except pymongo.errors.ConnectionFailure as e:
    print(f"Could not connect to MongoDB: {e}")
    exit(1)

# Custom Functions

# Initialize embedding model (Sentence Transformers)
embedding_model = SentenceTransformer('all-MiniLM-L6-v2')

# Function to create an embedding for a plot description
def create_embedding(plot: str):
    return embedding_model.encode(plot).tolist()  # Returns list for MongoDB compatibility

# Function to process a single movie document and store its embedding if not already present
def process_movie_details(movie):
    imdb_id = movie["imdbID"]
    
    existing_movie = movieEmbeddings.find_one({"imdbID": imdb_id})
    if existing_movie:
        print(f"Skipping {movie['title']} ({imdb_id}): embedding already exists.")
        return  # Skip if embedding exists
    
    # Create and store embedding
    embedding = create_embedding(movie["plot"])
    movieEmbeddings.insert_one({
        "movie_id": movie["_id"],
        "title": movie["title"],
        "imdbID": imdb_id,
        "embedding": embedding,
        "genres": movie["genre"]
    })
    
    print(f"Stored embedding for {movie['title']} ({imdb_id})")

# Function to load embeddings from MongoDB and return them with corresponding imdbIDs
def load_embeddings():
    embeddings= []
    imdb_ids = []
    for entry in movieEmbeddings.find():
        embeddings.append(entry["embedding"])
        imdb_ids.append(entry["imdbID"])
    return np.array(embeddings).astype("float32"), imdb_ids

# Function to build and return FAISS index
def build_faiss_index(embeddings):
    d = embeddings.shape[1]  # Dimensionality of embeddings
    index = faiss.IndexFlatL2(d)
    index.add(embeddings)  # Add embeddings to the index
    return index

# Main Code Block with iterative feature and FAISS index setup
# Set up starting point
start_id = "670d426328ad7f7da577c9d1"
query_filter = {"_id": {"$gte": ObjectId(start_id)}}

for movie in movieDetails.find(query_filter).sort("_id", 1):
    process_movie_details(movie)

embeddings, imdb_ids = load_embeddings()
faiss_map = build_faiss_index(embeddings)
print("FAISS index created successfully!")

# Close connection once finished
db_client.close()
print("MongoDB connection closed.")

