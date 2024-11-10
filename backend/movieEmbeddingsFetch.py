from contextlib import asynccontextmanager
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
from database.movieEmbeddingsCreate import load_embeddings, build_faiss_index

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

# Request body for plot and genre input
class MovieQuery(BaseModel):
    plot: str
    genre: Optional[str] = None
    
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Load embeddings and initialize FAISS at startup
    global faiss_index, imdb_ids
    embeddings, imdb_ids = load_embeddings()
    faiss_index = build_faiss_index(embeddings)

    yield

    # Close MongoDB connection on shutdown
    db_client.close()
    print("MongoDB connection closed.")

app.router.lifespan_context = lifespan

# Endpoint to find similar movies
@app.post("/find_similar_movies")
async def find_similar_movies(query: MovieQuery):
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
    
