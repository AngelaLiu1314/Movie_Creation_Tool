import openai
import json

def get_movie_poster_details(poster_link):
    '''
    Input:
    poster_link (string): A URL to a movie poster.

    Processing:
    The function builds a prompt using the poster URL to request detailed information about the poster.
    It sends the prompt to OpenAI’s API, which generates a response.
    The function parses the response into a Python dictionary.

    Output:
    A dictionary containing key information about the movie poster in the desired format.
    '''
    
    # Define the prompt for the API call
    prompt = f"Analyze the movie poster at {poster_link} and provide the following information in a JSON format:\n\
    title,\n\
    tagline,\n\
    genre,\n\
    director_style,\n\
    color_palette (object containing primary, secondary, and accent HEX color codes),\n\
    font (object containing title_font, tagline_font, and credits_font),\n\
    image_elements (describe the main character and background elements),\n\
    atmosphere,\n\
    iconography,\n\
    art_style,\n\
    period_style.\n\
    If any information is unavailable, return 'unknown' for that field."

    # Call OpenAI API
    response = openai.Completion.create(
        engine="text-davinci-003",
        prompt=prompt,
        max_tokens=300
    )
    
    # Parse GPT response to JSON
    try:
        details = json.loads(response['choices'][0]['text'].strip())
        
        # Transform details into the desired format for posterCharacteristics
        poster_characteristics = {
            "title": details.get("title", "unknown"),
            "tagline": details.get("tagline", "unknown"),
            "genre": details.get("genre", "unknown"),
            "directorStyle": details.get("director_style", "unknown"),
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
        
        return poster_characteristics
    
    except (json.JSONDecodeError, KeyError) as e:
        print(f"Error parsing the API response: {e}")
        return {}