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
'''
Schema Reminder:

Database Name: movies
Collection Name: movieDetails
movieDetails = {
        "imdbID": str,
        "title": str,
        "rating": str,
        "runtimeMinutes": float,
        "releaseDate": datetime,
        "genre": [
            str,
            str,
            str  
            ],
        "director": "Name of the Director",
        "writers": [
            str,
            str,
            str
            ],
        "actors": {
            str,
            str,
            str
                },
        "plot": str,
        "posterlink": str
        "posterCharactertistics": not yet created --> needs to be primary purpose of this file. But might end up being a collection of their own
            { (possible design)
                "title": str,
                "tagline": str,
                "genre": str,
                "director_style": str,
                "color_palette": {
                    "primary": str,
                    "secondary": str,
                    "accent": str
                }),
                "font": {
                    "title_font": str,
                    "tagline_font": str,
                    "credits_font": str
                }),
                "image_elements": {
                    "main_character": str,
                    "background": str
                }),
                "atmosphere": str,
                "iconography": str,
                "art_style": str,
                "period_style": str 
            }
    }
'''

