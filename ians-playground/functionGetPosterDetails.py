import os
from openai import OpenAI

client = OpenAI()
import json

def get_movie_poster_details(poster_link):
    # Structured prompt to enforce the same parameters for all movie posters
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

    response = client.chat.completions.create(model="gpt-4",  # or "gpt-4" if you're using GPT-4
    messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": prompt}
    ],
    max_tokens=300)

    # Parse the GPT response and extract the text
    details = json.loads(response.choices[0].message.content.strip())

    return details # will return details in JSON object

def get_movie_poster_characteristics(poster_link):
    poster_details = get_movie_poster_details(poster_link)

    # Construct poster_document with default values for missing fields. This can be inserted to Poster_Key_Phrases except let's rename it to Poster_Key_Characteristics
    poster_document = {
        "title": poster_details.get("title", "unknown"),
        "tagline": poster_details.get("tagline", "unknown"),
        "genre": poster_details.get("genre", "unknown"),
        "director_style": poster_details.get("director_style", "unknown"),
        "color_palette": poster_details.get("color_palette", {
            "primary": "unknown",
            "secondary": "unknown",
            "accent": "unknown"
        }),
        "font": poster_details.get("font", {
            "title_font": "unknown",
            "tagline_font": "unknown",
            "credits_font": "unknown"
        }),
        "image_elements": poster_details.get("image_elements", {
            "main_character": "unknown",
            "background": "unknown"
        }),
        "atmosphere": poster_details.get("atmosphere", "unknown"),
        "iconography": poster_details.get("iconography", ["unknown"]),
        "art_style": poster_details.get("art_style", "unknown"),
        "period_style": poster_details.get("period_style", "unknown")
    }

    return poster_document

posterURL = "https://m.media-amazon.com/images/M/MV5BMzU3YWYwNTQtZTdiMC00NjY5LTlmMTMtZDFlYTEyODBjMTk5XkEyXkFqcGdeQXVyMTkxNjUyNQ@@._V1_SX300.jpg"
posterDeets = get_movie_poster_characteristics(posterURL)