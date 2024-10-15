import json
import os
from dotenv import load_dotenv
import pymongo
from bson.objectid import ObjectId
import requests
import openai
import pandas as pd

load_dotenv() 
mongodb_uri = os.getenv('Mongo_URI') #retrieve mongodb uri from .env file

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
    '''
    Input:
    imdbID (str): The IMDB ID of the movie for which data needs to be fetched.

    Processing:
    - Retrieve the OMDB API key from environment variables.
    - Construct the URL for the OMDB API call using the given imdbID.
    - Make a request to the OMDB API and parse the response as JSON.
    - Find the index of the movie in the main DataFrame (mainDF) that matches the provided imdbID.
    
    Output:
    - response (dict): The JSON response from the OMDB API containing movie details.
    - indexInDF (Index): The index/indices of the movie in mainDF that match the provided imdbID.
    '''

    omdbAPIKey = os.getenv('OMDB-API-KEY')
    url = f"http://www.omdbapi.com/?i={imdbID}&plot=full&apikey={omdbAPIKey}"
    try:
        # Set a reasonable timeout, e.g., 10 seconds
        response = requests.get(url, timeout=10)
        indexInDF = mainDF.index[mainDF["imdb_id"] == imdbID]
        return response.json(), indexInDF
    except requests.exceptions.ReadTimeout:
        print(f"Request timed out for IMDB ID: {imdbID}")
        indexInDF = mainDF.index[mainDF["imdb_id"] == imdbID]
        return None, indexInDF
    except requests.exceptions.RequestException as e:
        print(f"An error occurred: {e}")
        indexInDF = mainDF.index[mainDF["imdb_id"] == imdbID]
        return None, indexInDF


def add_movie_details(imdbID, response, indexInDF): #defines what information we are looking to store
    '''
    Input:
    - imdbID (str): The IMDB ID of the movie.
    - response (dict): The response from the OMDB API containing movie information.
    - indexInDF (int): The index position in the main DataFrame where additional movie information can be fetched.
    
    Processing:
    - The function extracts data from the OMDB API response and the main DataFrame.
    - Constructs a dictionary (movieDetail) with all movie-related details.
    - Attempts to insert the constructed dictionary into a MongoDB collection.

    Output:
    - The function inserts the movieDetail document into a MongoDB collection and prints a confirmation message if successful.
    - If there is an error during the insertion, it prints the error message.
    '''
    # imdb id check to avoid redundant database storing
    existingMovie = movieDetails.find_one({"imdbID": imdbID})
    if existingMovie:
        print(f"Movie with imdbID {imdbID} already exists. Skipping insertion.")
        return
    else:
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


# Start adding movie details to the database. Max daily responses for OMDB API is 1000, so we need to use an indexing variable to avoid repetitive addition
lastIndex = 78102 # Please try to update it based on the printed lastIndex before closing out
dailyBatchSize = 100000

for imdbID in mainDF.imdb_id[lastIndex:lastIndex + dailyBatchSize]:
    response, indexInDF = get_omdb_response(imdbID)
    # Check if response is None before proceeding
    if response is None:
        print(f"No valid response for imdbID: {imdbID}. Skipping...")
        continue
    
    # When the OMDB API retrieves information but is "False"
    if response["Response"] == "False":
        print(f"Error fetching data for imdbID: {imdbID}. Skipping...")
        continue        
    # Proceed only if the response is valid
    elif response["Response"] == "True":
        add_movie_details(imdbID, response, indexInDF)

lastIndex += dailyBatchSize
print(lastIndex)

client.close()
print("MongoDB connection closed.")