import uvicorn
import os
import faiss
import numpy as np
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import pymongo
from sentence_transformers import SentenceTransformer
from dotenv import load_dotenv
from typing import List, Optional
import certifi

load_dotenv() 
app = FastAPI()
mongodb_uri = os.getenv('Mongo_URI') #retrieve mongodb uri from .env file

try:
    db_client = pymongo.MongoClient(mongodb_uri, tlsCAFile=certifi.where()) 
    db = db_client.get_database("movies") 
    movieDetails = db.get_collection("movieDetails")
    db_client.server_info() 
    print("Connected successfully to the 'Movies' database!")
    
    posterDetails = db.get_collection("posterDetails")
    print("Connected successfully to the 'Posters' database!")
    
    movieEmbeddings = db.get_collection("movieEmbeddings")
    print("Connected successfully to the 'Movie Embeddings' database!")
    
except pymongo.errors.ConnectionFailure as e:
    print(f"Could not connect to MongoDB: {e}")
    exit(1)

embedding_model = SentenceTransformer('all-MiniLM-L6-v2')

# Function to build FAISS index
def build_faiss_index(embeddings):
    d = embeddings.shape[1]
    index = faiss.IndexFlatL2(d)
    index.add(embeddings)
    return index

# Request body for plot and genre input
class MovieQuery(BaseModel):
    plot: str
    genre: Optional[str] = None

# Endpoint to find similar movies
@app.post("/generate_prompt")
async def generate_prompt(query: MovieQuery):
    plot_embedding = embedding_model.encode(query.plot).astype("float32")
    
    # Filter embeddings by genre if genre is provided
    filtered_embeddings = []
    filtered_imdb_ids = []
    
    # If a genre is called in query, only extract those with that genre in the list of genres
    if query.genre:
        cursor = movieEmbeddings.find({"genres": query.genre})
    else:
        cursor = movieEmbeddings.find()
    
    for movie in cursor:
        filtered_embeddings.append(movie["embedding"])
        filtered_imdb_ids.append(movie["imdbID"])
    
    if not filtered_embeddings:
        raise HTTPException(status_code=404, detail="No movies found for the selected genre")
    
    # Build FAISS index on filtered embeddings
    faiss_index = build_faiss_index(np.array(filtered_embeddings).astype("float32"))
    
    # Search for the top 5 closest movies
    _, indices = faiss_index.search(np.expand_dims(plot_embedding, axis=0), 5)
    top_n_ids = [filtered_imdb_ids[i] for i in indices[0]]
    
    # Fetch movie titles
    movie_titles = []
    movies = movieDetails.find({"imdbID": {"$in": top_n_ids}})
    for movie in movies:
        movie_titles.append(movie["title"])
    
    # Create prompt for Flux API
    prompt = f"Create a poster for a movie with this plot: {query.plot}. The top 5 closest movies are {', '.join(movie_titles)}. Generate a poster that is as close to the posters for these movies."
    
    return {"imdbIDs": top_n_ids, "movieTitles": movie_titles, "prompt": prompt}
    
@app.get("/get_available_genres")
async def get_available_genres():
    '''This function will get all the values of unique genre values that can be found under the genres field and return them in a list'''
    
    # Initialize an empty set to collect unique genres
    unique_genres = set()
    
    # Query the movieEmbeddings collection to retrieve all genres
    cursor = movieEmbeddings.find({}, {"genres": 1})  # Only fetch the 'genres' field

    # Iterate over each document to add genres to the set
    for document in cursor:
        genres = document.get("genres", [])
        unique_genres.update(genres)  # Add each genre to the set

    # Convert the set to a sorted list and return it
    return sorted(unique_genres)