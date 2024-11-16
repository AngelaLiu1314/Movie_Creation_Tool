import uvicorn
import os
import faiss
import numpy as np
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
import pymongo
from sentence_transformers import SentenceTransformer
from dotenv import load_dotenv
from typing import List, Optional
import certifi
from fastapi.middleware.cors import CORSMiddleware
import logging


'''
You fire it up by running 
uvicorn backend.movieEmbeddingsFetch:app --reload
'''

load_dotenv() 
app = FastAPI()
mongodb_uri = os.getenv('Mongo_URI') #retrieve mongodb uri from .env file

origins = [
    "http://localhost:3000"  #give access to different IPs here
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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

# Configure logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configure embedding generator
embedding_model = SentenceTransformer('all-MiniLM-L6-v2')

# Function to build FAISS index
def build_faiss_index(embeddings):
    d = embeddings.shape[1]
    index = faiss.IndexFlatL2(d)
    index.add(embeddings)
    return index

# Request body for plot and genre input
class MovieQuery(BaseModel):
    title: str
    plot: str
    genre: Optional[str] = Field(None, description="Genre of the movie")
    style: Optional[str] = Field(None, description="Poster style preference")
    isRetro: bool = Field(False, description="Filter for retro movies (1970-1989)")

def get_filtered_ids(query: MovieQuery):
    try:
        filter_query = {}

        if query.genre:
            filter_query["genre"] = query.genre

        if query.style:
            if query.style == "3D Digital Art":
                filter_query["posterStyle"] = "3d_digital_art"
            elif query.style == "Realistic Photography":
                filter_query["posterStyle"] = "realistic_photography"
            elif query.style == "Illustration (Animated)":
                filter_query["posterStyle"] = "illustration"
        
        if query.isRetro == True:
            filter_query["releaseDate"] = {"$gte": "1970-01-01", "$lte": "1989-12-31"}

        cursor = movieDetails.find(filter_query, {"imdbID": 1})
        
        filtered_ids = []
        for movie in cursor:
            filtered_ids.append(movie["imdbID"])

        if not filtered_ids:
            raise HTTPException(status_code=404, detail="No movies matched the filters.")

        return filtered_ids
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error during filtering: {str(e)}")

# Endpoint to find similar movies
@app.post("/generate_prompt")
async def generate_prompt(query: MovieQuery):
    if not query.plot or query.plot.strip() == "" or not query.title or query.title.strip() == "":
        raise HTTPException(status_code=400, detail="Your title or plot description cannot be empty.")
    
    query_embedding = embedding_model.encode(query.plot).astype("float32")
    
    # Retrieve filtered IDs from movieDetails
    filtered_ids = get_filtered_ids(query)
    
    if not filtered_ids:
        raise HTTPException(status_code=404, detail="No movies matched the filters.")
    
    # Retrieve embeddings for the filtered IDs from movieEmbeddings
    filtered_embeddings = []
    filtered_embeddings_ids = []
    missing_embeddings_ids = []

    embeddings_cursor = movieEmbeddings.find({"imdbID": {"$in": filtered_ids}}, {"embedding": 1, "imdbID": 1})
    for movie_embedding in embeddings_cursor:
        if "embedding" in movie_embedding and "imdbID" in movie_embedding:
            filtered_embeddings.append(movie_embedding["embedding"])
            filtered_embeddings_ids.append(movie_embedding["imdbID"])
        else:
            missing_embeddings_ids.append(movie_embedding.get("imdbID"))

    if missing_embeddings_ids:
        logger.warning(f"Missing embeddings for IDs: {missing_embeddings_ids}")
    
    if not filtered_embeddings:
        raise HTTPException(status_code=404, detail="No valid embeddings found for the filtered movies.")
    
    # Build FAISS Index
    try:
        faiss_index = build_faiss_index(np.array(filtered_embeddings).astype("float32"))
        _, indices = faiss_index.search(np.expand_dims(query_embedding, axis=0), 5)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error building FAISS index or performing search: {str(e)}")
    
    top_n_ids = []
    for i in indices[0]:
        top_n_ids.append(filtered_embeddings_ids[i])
    
    # Fetch movie titles and directors
    titles_and_directors = {}
    movies_cursor = movieDetails.find({"imdbID": {"$in": top_n_ids}}, {"title": 1, "director": 1, "imdbID": 1})
    for movie in movies_cursor:
        imdbID = movie["imdbID"]
        titles_and_directors[imdbID] = {
            "title": movie.get("title", "unknown title"),
            "director": movie.get("director", "unknown director")
        }
    
    # Create description using the top movies
    top_movies_description = ""
    for imdbID, details in titles_and_directors.items():
        title = details.get("title", "unknown title")
        director = details.get("director", "unknown director")
        if top_movies_description:
            top_movies_description += ", "
        top_movies_description += f"{title} by {director}"
    
    # Create prompt for Flux API
    if query.style == "Illustration (Animated)":
        prompt = f"Create a poster for a movie with this plot: {query.plot}. The top 5 closest movies are {top_movies_description}. Generate a poster that stylistically resembles the posters for these movies. The poster should be in a style of flat-image illustration style. The text '{query.title}' must be clearly visible as the title."
    else:
        prompt = f"Create a poster for a movie with this plot: {query.plot}. The top 5 closest movies are {top_movies_description}. Generate a poster that stylistically resembles the posters for these movies. The text '{query.title}' must be clearly visible as the title."
    
    print(f"Generated Prompt: {prompt}")
    
    return {"imdbIDs": top_n_ids, "movieTitles": [details["title"] for details in titles_and_directors.values()], "prompt": prompt}
    
    
@app.get("/get_available_genres")
async def get_available_genres():
    '''This function will get all the values of unique genre values that can be found under the genres field and return them in a list'''
    
    # Initialize an empty set to collect unique genres
    unique_genres = set()
    
    # Query the movieEmbeddings collection to retrieve all genres
    cursor = movieDetails.find({}, {"genre": 1})  # Only fetch the 'genres' field

    # Iterate over each document to add genres to the set
    for document in cursor:
        genre = document.get("genre", [])
        unique_genres.update(genre)  # Add each genre to the set

    # Convert the set to a sorted list and return it
    return sorted(unique_genres)