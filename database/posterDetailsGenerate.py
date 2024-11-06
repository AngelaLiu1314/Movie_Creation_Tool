import os
from dotenv import load_dotenv
import openai
import json
from google.cloud import vision
import pymongo
import certifi
from datetime import datetime
import requests
from io import BytesIO
from PIL import Image
import torch
from torchvision import transforms, models
from torchvision.models import ResNet18_Weights

load_dotenv() 
mongodb_uri = os.getenv('Mongo_URI') #retrieve mongodb uri from .env file

try:
    db_client = pymongo.MongoClient(mongodb_uri, tlsCAFile=certifi.where()) # this creates a client that can connect to our DB
    db = db_client.get_database("movies") # this gets the database named 'Movies'
    movieDetails = db.get_collection("movieDetails")
    posterDetails = db.get_collection("posterDetails")

    db_client.server_info() # forces client to connect to server
    print("Connected successfully to the 'Movies' database!")

except pymongo.errors.ConnectionFailure as e:
    print(f"Could not connect to MongoDB: {e}")
    exit(1)

# Define image transformations to match training
data_transforms = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor()
])

# Load pretrained ResNet18 model with updated syntax
model = models.resnet18(weights=ResNet18_Weights.IMAGENET1K_V1)
num_features = model.fc.in_features
model.fc = torch.nn.Sequential(
    torch.nn.Dropout(0.5),  # Dropout to match training
    torch.nn.Linear(num_features, 3)  # 3 classes: photography, illustration, 3D digital art
)

# Load model state
model.load_state_dict(torch.load('models/best_style_classifier.pth', map_location="cpu"))
model.eval()

# Device configuration
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
model = model.to(device)

# Define class names based on your dataset structure
class_names = ['3d_digital_art', 'illustration', 'photography']

def classify_style(imdbID: str):
    # Retrieve movie poster URL from MongoDB
    movie = movieDetails.find_one({"imdbID": imdbID})
    poster_url = movie.get("posterLink")
    title = movie.get("title")

    if not poster_url:
        print(f"No poster URL found for IMDb ID {imdbID}")
        return None

    try:
        # Download the poster image temporarily
        response = requests.get(poster_url)
        response.raise_for_status()
        img = Image.open(BytesIO(response.content))

        # Apply the transformations
        img_tensor = data_transforms(img).unsqueeze(0).to(device)

        # Run the model on the image
        with torch.no_grad():
            output = model(img_tensor)
            _, predicted = torch.max(output, 1)
            predicted_class = class_names[predicted.item()]

        # print(f"Predicted art style for the poster for {imdbID}, {title}: {predicted_class}")
        return predicted_class

    except requests.exceptions.RequestException as e:
        print(f"Error downloading image: {e}")
        return None

print("GOOGLE_APPLICATION_CREDENTIALS:", os.getenv("GOOGLE_APPLICATION_CREDENTIALS"))

try:
    gcloud_client = vision.ImageAnnotatorClient()
    print("Client initialized successfully.")
except Exception as e:
    print(f"Failed to initialize client: {e}")

def analyze_poster_image(imdbID: str):
    """
    Analyzes a poster image using Google Vision API and returns characteristics.
    """
    print("Starting analyze_poster_image function...")
    
    movie = movieDetails.find_one({"imdbID": imdbID})
    poster_url = movie.get("posterLink")
    
    if not poster_url:
        print(f"No poster URL found for IMDb ID {imdbID}")
        return None
    
    vision_client = vision.ImageAnnotatorClient()
    image = vision.Image()
    image.source.image_uri = poster_url
    
    # Initialize dictionary to hold extracted poster characteristics
    poster_characteristics = {}
    
    # Identifying color scheme using top 3 color responses
    try:
        color_response = vision_client.image_properties(image=image)
        print("Color response received") # , color_response)
        color_scheme = []
        for color_info in color_response.image_properties_annotation.dominant_colors.colors:
            rgb = color_info.color
            hex_code = '#{:02x}{:02x}{:02x}'.format(int(rgb.red), int(rgb.green), int(rgb.blue))
            color_scheme.append(hex_code)
        poster_characteristics["colorScheme"] = color_scheme[0:3]
    except Exception as e:
        print("Error in color analysis:", e)

    # Identifying image elements using object response
    try:
        object_response = vision_client.object_localization(image=image)
        print("object response received.")
        main_elements = [obj.name for obj in object_response.localized_object_annotations]
        poster_characteristics["mainElements"] = main_elements
    except Exception as e:
        print("Error in label detection:", e)
    
    # Run label detection
    try:
        label_response = vision_client.label_detection(image=image)
        print("Label reseponse received.")
        labels = [label.description for label in label_response.label_annotations]
        poster_characteristics["Labels"] = labels
    except Exception as e:
        print("Error in web labeling")
    
    # Identifying taglines using text_response    
    try:
        text_response = vision_client.text_detection(image=image)
        print("Text response received:") # , text_response)
        texts = [text.description for text in text_response.text_annotations]
        poster_characteristics["tagline"] = texts[0] if texts else None
    except Exception as e:
        print("Error in text detection:", e)
    
    # Identifying art style using the classifier function
    try:
        style = classify_style(imdbID)
        print("Art style classified")
        poster_characteristics["Art Style"] = style
    except Exception as e:
        print("Error in classifying:", e)

    # Getting the decade of the movie
    try:
        movie = movieDetails.find_one({"posterLink": poster_url})
        if movie:
            release_date = movie["releaseDate"]
            date_obj = datetime.strptime(release_date, "%Y-%m-%d")
            release_year = str(date_obj.year)
            release_decade = release_year[0:3] + "0"
            poster_characteristics["decade"] = release_decade
    except Exception as e:
        print("Error in getting the movie:", e)
        
    return poster_characteristics

test_id = "tt2668120"
poster_characteristics = analyze_poster_image(test_id)
print(poster_characteristics)

db_client.close()
print("MongoDB connection closed.")