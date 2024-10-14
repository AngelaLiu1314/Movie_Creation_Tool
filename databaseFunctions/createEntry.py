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

# Read in the main dataframe from which we'll get the IMDB IDs
mainDF = pd.read_csv(os.getenv("IMDB_PROCESSED_DF_PATH"), low_memory= False) # Please store your respective csv file path in your .env file

def get_omdb_response(imdbID):
    omdbAPIKey = os.getenv('OMDB-API-KEY')
    url = f"http://www.omdbapi.com/?&apikey={omdbAPIKey}&i={imdbID}&plot=full&r=json()"
    response = requests.get(url).json()
    indexInDF = mainDF.index[mainDF["imdb_id"] == imdbID]

    return response, indexInDF


def add_movie_details(imdbID, response, indexInDF): #defines what information we are looking to store
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

    imdbID = imdbID
    Title = response["Title"]
    Rating = response["Rated"]
    RTM = mainDF.loc[indexInDF, "runtime"].values[0]
    DOR = mainDF.loc[indexInDF, "release_date"].values[0]
    #store multiple genres in order to better calculate similarity score
    Genre = [genre.strip() for genre in response["Genre"].split(',')] 
    director = response["Director"]
    writers = [writer.strip() for writer in response["Writer"].split(",")]
    # Get 3 main actors from OMDB API
    actors = [actor.strip() for actor in response["Actors"].split(",")]

    Plot = response["Plot"]
    # Estimated_Budget = "Sample Budget" # hold for now
    Poster_Link = response["Poster"]
    # Poster_Key_Characteristics = get_movie_poster_details(Poster_Link) # hold until we have access to openai api
    
    movieDetail = {
        "imdbID": imdbID,
        "title": Title,
        "rating": Rating,
        "runtimeMinutes": RTM,
        "releaseDate": DOR,
        "genre": Genre,
        "director": director,
        "writers": writers,
        "actors": actors,
        "plot": Plot,
        # "Estimated Budget": Estimated_Budget, # hold for now
        "posterLink": Poster_Link,
        # "Poster Key Phrases": Poster_Key_Characteristics
    }

    try:
        result = movieDetails.insert_one(movieDetail)
        print(f"Movie added with ID: {result.inserted_id}")
    except pymongo.errors.PyMongoError as e:
        print(f"An error occurred while adding the movie: {e}")

# def main():
#     add_movie_details()
#     client.close()

# if __name__ == "__main__":
#     main()

# Start adding movie details to the database. Max daily responses for OMDB API is 1000, so we need to use an indexing variable to avoid repetitive addition
lastIndex = 850 # Please try to update it based on the printed lastIndex before closing out
for imdbID in mainDF.imdb_id[lastIndex:lastIndex + 800]:
    response, indexInDF = get_omdb_response(imdbID)
    if response["Response"] == "False":
        print(f"Error fetching data for imdbID: {imdbID}. Skipping...")
        continue        
    elif response["Response"] == "True":
        add_movie_details(imdbID, response, indexInDF)

lastIndex += 800
print(lastIndex)