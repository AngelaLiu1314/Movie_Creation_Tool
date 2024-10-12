import os
from dotenv import load_dotenv
import pymongo
from bson.objectid import ObjectId

load_dotenv() 
mongodb_uri = os.getenv('MONGODB_URI') #retrieve mongodb uri from .env file

try:
    client = pymongo.MongoClient(mongodb_uri) # this creates a client that can connect to our DB
    db = client.get_database("Movies") # this gets the database named 'Movies'
    movieDetails = db.get_collection("MovieDetail")

    client.server_info() # forces client to connect to server
    print("Connected successfully to the 'Movies' database!")

except pymongo.errors.ConnectionFailure as e:
    print(f"Could not connect to MongoDB: {e}")
    exit(1)

def add_movie_details(): #defines what information we are looking to store
    imdb_id = "Sample id"
    Title = "Sample Title"
    Rating = "Sample Rating"
    RTM = "Sample RTM"
    DOR = "Sample DOR"
    Genre = ["Genre1", "Genre2", "Genre3"] #store multiple genres in order to better calculate similarity score
    Director = "Sample Director"
    Writers = ["Writer1", "Writer2", "Writer3"]
    Actors = [{
            "Actor 1": "Sample Actor1",
            "Actor 2": "Sample Actor 2",
            "Actor 3": "Sample Actor 3"
            }]
    Plot = "Sample Plot goes here."
    Estimated_Budget = "Sample Budget"
    Poster = "Sample Poster Link"
    Poster_Key_Characteristics = [
                        "Orange and blue contrast",
                        "Futuristic sans-serif font",
                        "Ryan Gosling front and center",
                        "Harrison Ford's return",
                        "Neon city skyline",
                        "Sci-Fi action vibes",
                        "Layered character composition",
                        "Dark and moody aesthetic",
                        "Bold, blocky title font",
                        "Dystopian urban landscape"
                        ]
    
    movieDetail = {
        "imdb_id": imdb_id,
        "title": Title,
        "Rating": Rating,
        "RTM": RTM,
        "DOR": DOR,
        "Genre": Genre,
        "Director": "Name of the Director",
        "Writer(s)": Writers,
        "Actors": Actors,
        "Plot": Plot,
        "Estimated Budget": Estimated_Budget,
        "Poster": Poster,
        "Poster Key Phrases": Poster_Key_Characteristics
    }

    try:
        result = movieDetails.insert_one(movieDetail)
        print(f"Movie added with ID: {result.inserted_id}")
    except pymongo.errors.PyMongoError as e:
        print(f"An error occurred while adding the movie: {e}")

def main():
    add_movie_details()
    client.close()

if __name__ == "__main__":
    main()