import json
import os
from dotenv import load_dotenv
import pymongo
from bson.objectid import ObjectId

import openai


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

def get_movie_poster_details(poster_link):
    '''
    Input:
    poster_link (string): A URL to a movie poster.

    Processing:
    Prompt Creation: The function builds a prompt using the poster URL to request detailed information about the poster (e.g., title, genre, color palette).
    API Call: It sends this prompt to OpenAI’s API, which generates a response.
    Response Parsing: The function parses the response into a Python dictionary.

    Output:
    details (dictionary/JSON): A dictionary containing key information about the movie poster (e.g., title, genre, color palette, fonts) -- subject to change
    '''
    prompt = f"Provide the following information about the poster {poster_link} as JSON:\n\
    title,\n\
    tagline,\n\
    genre,\n\
    director_style,\n\
    color_palette (nested object containing HEX codes of primary, secondary, and accent colors),\n\
    font (nested object containing title_font, tagline_font, credits_font),\n\
    image_elements (e.g., main character, background),\n\
    atmosphere,\n\
    iconography,\n\
    art_style,\n\
    period_style.\n\
    If any information is unavailable, use 'unknown' as the value."
    
    response = openai.Completion.create(
        engine="text-davinci-003",
        prompt=prompt,
        max_tokens=300
    )
    
    # Parse GPT response to JSON
    details = json.loads(response['choices'][0]['text'].strip())
    
    return details

def add_movie_details(): #defines what information we are looking to store
    # Change necessary to iterate through a dataframe of existing movie data (including input) – will be implemented later
    '''
    Input:
    Later, this function will iterate through a DataFrame to fetch movie data.
    
    Processing:
    Movie Data Creation: The function assigns sample data (e.g., imdb_id, title, rating, etc.) for the movie.
    Poster Details Fetching: It calls get_movie_poster_details() to retrieve key characteristics for the movie poster based on the poster link.
    Document Construction: A dictionary (movieDetail) is created with all movie information, including poster details.
    
    Output:
    The function inserts the constructed movieDetail document into a MongoDB collection and prints a confirmation of the insertion.
    '''
    
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
    # Get 3 main actors from OMDB API

    Plot = "Sample Plot goes here."
    Estimated_Budget = "Sample Budget"
    Poster_Link = "Sample Poster Link"
    Poster_Key_Characteristics = get_movie_poster_details(Poster_Link)
    
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
        "Poster": Poster_Link,
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