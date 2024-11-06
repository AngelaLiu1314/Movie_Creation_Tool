# About the Custom Functions Present in this Repository:
## Database Functions
### 1. get_omdb_response
**Input:**
- `imdbID (str)`: The IMDB ID of the movie for which data needs to be fetched.

**Processing:**
- Retrieve the OMDB API key from environment variables.  
    ```python
    omdbAPIKey = os.getenv('OMDB-API-KEY')
    ```
- Construct the URL for the OMDB API call using the given imdbID.
    ```python
    url = f"http://www.omdbapi.com/?i={imdbID}&plot=full&apikey={omdbAPIKey}"
    ```
- Make a request to the OMDB API and parse the response as JSON.
    ```python
    response = requests.get(url, timeout=10)
    return response.json(), indexInDF
    ```
- Find the index of the movie in the main DataFrame (mainDF) that matches the provided imdbID.
    ```python
    indexInDF = mainDF.index[mainDF["imdb_id"] == imdbID]
    ```
    
**Output:**  
```python
return response.json(), indexInDF
```
- `response (dict)`: The JSON response from the OMDB API containing movie details.
- `indexInDF (Index)`: The index/indices of the movie in mainDF that match the provided imdbID.

### 2. add_movie_details 
**Input:**
- `imdbID (str)`: The IMDB ID of the movie.
- `response (dict)`: The response from the OMDB API containing movie information.
- `indexInDF (int)`: The index position in the main DataFrame where additional movie information can be fetched.

**Processing:**
- Checks the called `imdbID` to avoid redundant database storing
    ```python
    existingMovie = movieDetails.find_one({"imdbID": imdbID})
    
    if existingMovie:
        print(f"Movie with imdbID {imdbID} already exists. Skipping insertion.")
        return    
    ```
- The function extracts data from the OMDB API response and the main DataFrame.
    ```python
    else:
        imdbID = imdbID
        Title = response["Title"]
        Rating = response["Rated"]
        RTM = mainDF.loc[indexInDF, "runtime"].values[0]
        DOR = mainDF.loc[indexInDF, "release_date"].values[0]
        # Store multiple genres in order to better calculate similarity score
        Genre = [genre.strip() for genre in response["Genre"].split(',')] 
        director = response["Director"]
        writers = [writer.strip() for writer in response["Writer"].split(",")]
        # Get main actors from OMDB API
        actors = [actor.strip() for actor in response["Actors"].split(",")]
        Plot = response["Plot"]
        Poster_Link = response["Poster"]
    ```
- Constructs a dictionary (movieDetail) with all movie-related details.
    ```python
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
        "posterLink": Poster_Link,
    }    
    ```
- Attempts to insert the constructed dictionary into a MongoDB collection.
    ```python
    try:
        result = movieDetails.insert_one(movieDetail)
        print(f"Movie added with ID: {result.inserted_id}")
    except pymongo.errors.PyMongoError as e:
        print(f"An error occurred while adding the movie: {e}")    
    ```

**Output:**  
- The function inserts the movieDetail document into a MongoDB collection and prints a confirmation message if successful.
- If there is an error during the insertion, it prints the error message.

### 3. get_movie_poster_details

**Input:**

- `poster_link (string)`: A URL to a movie poster.

**Processing:**

- The function builds a prompt using the poster URL to request detailed information about the poster.
    ```python
    # Define the prompt for the API call
    prompt = f"Analyze the movie poster at {poster_link} and provide the following information in a JSON format:\n\
    title,\n\
    tagline,\n\
    color_palette (dictionary/JSON object containing primary, secondary, and accent HEX color codes),\n\
    font (dictionary/ JSON object containing title_font, tagline_font, and credits_font),\n\
    image_elements (describe the main character and background elements),\n\
    atmosphere,\n\
    art_style,\n\
    period_style.\n\
    If any information is unavailable, return 'unknown' for that field."

    ```
- Sends the prompt to OpenAI’s API, which generates a response.
    ```python
        # Call OpenAI API
        response = openai.Completion.create(
            engine="text-davinci-003",
            prompt=prompt,
            max_tokens=300
        )
    ```
- The function parses the response into a Python dictionary.
    ```python
        # Parse GPT response to JSON
        try:
            details = json.loads(response['choices'][0]['text'].strip())
            
            # Transform details into the desired format for posterCharacteristics
            poster_characteristics = {
                "title": details.get("title", "unknown"),
                "tagline": details.get("tagline", "unknown"),
                "colorScheme": [
                    details.get("color_palette", {}).get("primary", "unknown"),
                    details.get("color_palette", {}).get("secondary", "unknown"),
                    details.get("color_palette", {}).get("accent", "unknown")
                ],
                "font": [
                    details.get("font", {}).get("title_font", "unknown"),
                    details.get("font", {}).get("tagline_font", "unknown"),
                    details.get("font", {}).get("credits_font", "unknown")
                ],
                "atmosphere": details.get("atmosphere", "unknown"),
                "imageElement": {
                    "main": details.get("image_elements", {}).get("main_character", "unknown"),
                    "background": details.get("image_elements", {}).get("background", "unknown")
                },
                "artStyle": details.get("art_style", "unknown"),
                "periodStyle": details.get("period_style", "unknown")
            }

    ```

**Output:**
- A dictionary containing key information about the movie poster in the desired format.  
    ```python
    return poster_characteristics
    ```

### 4. add_movie_poster_characteristics (WiP)

**Input:**
- `imdbID (str)`: A string representing the unique identifier of the movie. It is used to query the `movieDetails` collection to find the corresponding movie and its `posterLink`.

**Processing:**

- Constructs the `poster_url` by embedding the imdbID into the FastAPI URL endpoint for poster characteristics:
- This URL is used to send a POST request to add or update poster characteristics on the FastAPI server.

    ```python
    poster_url = f"{FASTAPI_URL}/posters/{imdbID}"
    ```
- The function first queries the `posterDetails` collection to check if a poster entry for the given `imdbID` already exists.
- If the entry exists, it skips the insertion to avoid redundancy:

    ```python
    existingMovie = posterDetails.find_one({"imdbID": imdbID})
    if existingMovie:
        print(f"Movie with imdbID {imdbID} already exists. Skipping insertion.")
        return
    ```
- If no existing poster details are found, the function queries the `movieDetails` collection for the movie corresponding to the `imdbID`:
- If the movie is not found, the function prints a message and returns without further action.

    ```python
    movie = movieDetails.find_one({"imdbID": imdbID})
    ```
- The function retrieves the `posterLink` from the movie document. If the posterLink is either not available or is "N/A", the function skips further processing and returns:

    ```python
    poster_link = movie.get('posterLink', None)
    if not poster_link or poster_link == "N/A":
        print(f"Poster link not found for movie with IMDb ID {imdbID}.")
        return
    ```
- The function then calls the `get_movie_poster_details(poster_link)` function to obtain a dictionary of poster characteristics by analyzing the poster image. This function interacts with an OpenAI service to get detailed information about the poster:

    ```python
    poster_characteristics = get_movie_poster_details(poster_link)
    ```
- After generating the poster characteristics, the function adds the `imdbID` and `posterLink` to the returned dictionary to ensure it matches the expected schema:

    ```python
    poster_characteristics["imdbID"] = imdbID
    poster_characteristics["posterLink"] = poster_link
    ```

- The function makes a POST request to the FastAPI endpoint `/posters/{imdbID}` with the generated poster characteristics in the JSON payload:

    ```python
    response = requests.post(poster_url, json=poster_characteristics)
    ```

- If the POST request succeeds (status code 200), the function prints a success message and the updated movie details. If the request fails (non-200 status code), it prints an error message with the response status code and error text:

    ```python
    if response.status_code == 200:
        print(f"Successfully updated movie {imdbID} poster characteristics.")
        print(response.json())
    else:
        print(f"Failed to update movie {imdbID}. Status Code: {response.status_code}")
        print(response.text)
    ```


**Output:**

1.	**Success**: If the movie’s poster characteristics are successfully added/updated, it prints a success message along with the JSON response from the FastAPI server.

2.	**Failure**: If an error occurs during the request or if the `posterLink` or movie is not found, it prints the relevant error message and skips the insertion.




## API Functions

### 

###

###

###

###

###



<details>
<summary>
template
</summary>

**Input:**

**Processing:**

- 
    ```python

    ```
- 
    ```python

    ```
- 
    ```python

    ```
- 
    ```python

    ```

**Output:**
</summary></details>