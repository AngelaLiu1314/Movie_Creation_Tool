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
color_palette (object containing primary, secondary, and accent HEX color codes),\n\
font (object containing title_font, tagline_font, and credits_font),\n\
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