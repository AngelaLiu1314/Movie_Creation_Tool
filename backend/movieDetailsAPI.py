from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from pydantic import Field
from typing import List, Optional, Union, Dict
import pymongo
import certifi
from pymongo import MongoClient
from bson import ObjectId
from dotenv import load_dotenv
import os
import base64

'''
You fire it up by running uvicorn backend.movieDetailsAPI:app --reload
'''

# Load environment variables from .env file
load_dotenv()

# Initialize FastAPI app
app = FastAPI()

# Fetch MongoDB URI from environment variables
try:
    mongo_uri = os.getenv("Mongo_URI")
    client = pymongo.MongoClient(mongo_uri, tlsCAFile=certifi.where())
    db = client["movies"]
    movieDetails = db["movieDetails"]
    posterDetails = db["posterDetails"]

    client.server_info() # forces client to connect to server
    print("Connected successfully to the 'Movies' database!")

except pymongo.errors.ConnectionFailure as e:
    print(f"Could not connect to MongoDB: {e}")
    exit(1)

# Root endpoint to welcome users to the API
@app.get("/")
def read_root():
    return {"message": "Welcome to the Movies API. Visit /movies to explore the collection."}

# Pydantic model for a movie
class Movie(BaseModel):
    imdbID: str
    title: str
    rating: str
    runtimeMinutes: Union[str, float]
    releaseDate: str
    genre: List[str]
    director: str
    writers: List[str]
    actors: List[str]
    plot: str
    posterLink: str
    trainingPrompt: Optional[str]

# Get all movies
@app.get("/movies", response_model=List[Movie])
def get_movies():
    movies = list(movieDetails.find({}))
    if not movies:
        raise HTTPException(status_code=404, detail="No movies found")

    return [Movie(**movie) for movie in movies]

# Get a movie by IMDb ID
@app.get("/movies/{imdbID}", response_model=Movie)
def get_movie_by_imdbID(imdbID: str):
    imdbID = imdbID.strip()
    movie = movieDetails.find_one({"imdbID": imdbID})
    if not movie:
        raise HTTPException(status_code=404, detail="Movie not found")

    return Movie(**movie)

# Add a new movie
@app.post("/movies", response_model=Movie)
def add_movie(movie: Movie):
    if movieDetails.find_one({"imdbID": movie.imdbID}):
        raise HTTPException(status_code=400, detail="Movie already exists")
    movieDetails.insert_one(movie.model_dump())
    return movie

# Update a movie by IMDb ID
@app.put("/movies/{imdbID}", response_model=Movie)
def update_movie(imdbID: str, movie: Movie):
    imdbID = imdbID.strip()
    updated_movie = movieDetails.find_one_and_update(
        {"imdbID": imdbID}, {"$set": movie.model_dump()}, return_document=True
    )
    if not updated_movie:
        raise HTTPException(status_code=404, detail="Movie not found")

    return Movie(**updated_movie)


# Delete a movie by IMDb ID
@app.delete("/movies/{imdbID}")
def delete_movie(imdbID: str):
    imdbID = imdbID.strip()
    result = movieDetails.delete_one({"imdbID": imdbID})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Movie not found")
    return {"message": "Movie deleted successfully"}

print(get_movie_by_imdbID("tt32513166"))

