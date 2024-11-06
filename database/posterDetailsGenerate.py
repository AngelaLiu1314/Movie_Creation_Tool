import openai
import json
from google.cloud import vision

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
    color_palette (dictionary/JSON object containing primary, secondary, and accent HEX color codes),\n\
    font (dictionary/ JSON object containing title_font, tagline_font, and credits_font),\n\
    image_elements (describe the main character and background elements),\n\
    atmosphere,\n\
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
        
        # Transform details into the desired format for posterCharacteristics. Make sure to edit this and BaseModel in apiMain.py together
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
        
        return poster_characteristics
    
    except (json.JSONDecodeError, KeyError) as e:
        print(f"Error parsing the API response: {e}")
        return {}

def analyze_poster_image(poster_link):
    """
    Analyzes a poster image using Google Vision API and returns characteristics.
    """
    vision_client = vision.ImageAnnotatorClient()
    image = vision.Image()
    image.source.image_uri = poster_link
    
    # Initialize dictionary to hold extracted poster characteristics
    poster_characteristics = {}

    # Analyze color properties
    color_response = vision_client.image_properties(image=image)
    color_scheme = []
    for color_info in color_response.image_properties_annotation.dominant_colors.colors:
        rgb = color_info.color
        hex_code = '#{:02x}{:02x}{:02x}'.format(int(rgb.red), int(rgb.green), int(rgb.blue))
        color_scheme.append(hex_code)
    poster_characteristics["colorScheme"] = color_scheme

    # Analyze image content (label detection)
    label_response = vision_client.label_detection(image=image)
    image_elements = [label.description for label in label_response.label_annotations]
    poster_characteristics["imageElement"] = {"elements": image_elements}

    # Analyze text (OCR) on the poster
    text_response = vision_client.text_detection(image=image)
    texts = [text.description for text in text_response.text_annotations]
    poster_characteristics["tagline"] = texts[0] if texts else None  # Use first detected text as tagline if available

    return poster_characteristics

analyze_poster_image("https://m.media-amazon.com/images/M/MV5BNDk3MDFlYjgtMWQ3Mi00ODgxLWE4NDEtNzA0YjM2NzNhZGM4XkEyXkFqcGdeQXVyMTYyMDQ1OTAz._V1_SX300.jpg")