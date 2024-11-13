import json
import os
import traceback
from dotenv import load_dotenv
import pymongo
from bson.objectid import ObjectId
import requests
import openai
import pandas as pd
import certifi
from PIL import Image
from io import BytesIO
import torch
from torchvision import transforms, models
from torchvision.models import ResNet18_Weights
from transformers import BlipProcessor, BlipForConditionalGeneration

load_dotenv() 
mongodb_uri = os.getenv('Mongo_URI') #retrieve mongodb uri from .env file

try:
    db_client = pymongo.MongoClient(mongodb_uri, tlsCAFile=certifi.where()) # this creates a client that can connect to our DB
    db = db_client.get_database("movies") # this gets the database named 'Movies'
    movieDetails = db.get_collection("movieDetails")

    db_client.server_info() # forces client to connect to server
    print("Connected successfully to the 'Movies' database!")
    
    posterDetails = db.get_collection("posterDetails")
    print("Connected successfully to the 'Posters' database!")

except pymongo.errors.ConnectionFailure as e:
    print(f"Could not connect to MongoDB: {e}")
    exit(1)

# Read in the main dataframe from which we'll get the IMDB IDs
mainDF = pd.read_csv(os.getenv("IMDB_PROCESSED_DF_PATH"), low_memory= False) # Please store your respective csv file path in your .env file

def update_documents_posterImage(movie):
    poster_link = movie.get("posterLink")

    if poster_link and poster_link != "N/A":
        response = requests.get(poster_link)
        try:
            image = Image.open(BytesIO(response.content))
            # Converting to bytes
            img_byte_array = BytesIO()
            image.save(img_byte_array, format="JPEG")
            img_data = img_byte_array.getvalue()

            # Updating document
            movieDetails.update_one(
                {"_id": movie["_id"]},
                {"$set": {"posterImage": img_data}}
            )
            
            print(f"Processed document ID: {movie["_id"]}")
            
        except:
            movieDetails.update_one(
                {"_id": movie["_id"]},
                {"$set": {"posterImage": "N/A"}}
            )
            print("Couldn't get the image. Storing as N/A")

# Define image transformations to match training
data_transforms = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor()
])

# Load pretrained ResNet18 model with updated syntax
model_analysis = models.resnet18(weights=ResNet18_Weights.IMAGENET1K_V1)
num_features = model_analysis.fc.in_features
model_analysis.fc = torch.nn.Sequential(
    torch.nn.Dropout(0.5),  # Dropout to match training
    torch.nn.Linear(num_features, 3)  # 3 classes: photography, illustration, 3D digital art
)

# Load model state
model_analysis.load_state_dict(torch.load('models/best_style_classifier.pth', map_location="cpu"))
model_analysis.eval()

# Device configuration
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
model_analysis = model_analysis.to(device)

# Define class names based on your dataset structure
class_names = ['3d_digital_art', 'illustration', 'realistic_photography']

def classify_style(movie):
    # Retrieve movie poster URL from MongoDB
    imdbID = movie["imdbID"]
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
            output = model_analysis(img_tensor)
            _, predicted = torch.max(output, 1)
            predicted_class = class_names[predicted.item()]

        print(f"Predicted art style for the poster for {imdbID}, {title}: {predicted_class}")
        
        try:
            movieDetails.update_one(
                {"_id": movie["_id"]},
                {"$set": {"posterStyle": predicted_class}}
            )
        except Exception as e:
            print(f"Error updating document {movie['_id']} in MongoDB: {e}")
            traceback.print_exc()
        
        print(f"Updated document {movie['_id']} with poster style.")

    except requests.exceptions.RequestException as e:
        print(f"Error downloading image: {e}")
        return None

def update_documents_trainingPrompt(movie):
    try:
        imdbID = movie["imdbID"]
        genres = movie["genre"]
        directors = movie["director"]
        plot = movie["plot"]
        
        if len(genres) > 1:
            genre_str = ", ".join(genres)
        else:
            genre_str = str(genres[0])
    
        if isinstance(directors, list):
            if len(directors) == 1:
                director_str = directors[0]
            elif len(directors) == 2:
                director_str = f"{directors[0]} and {directors[1]}"
            else:
                director_str = ", ".join(directors[:-1]) + f", and {directors[-1]}"
        else:
            director_str = directors

        # Generate the training prompt
        training_prompt = f"{genre_str} movie directed by {director_str}. Plot: {plot}"

        try:
            movieDetails.update_one(
                {"_id": movie["_id"]},
                {"$set": {"trainingPrompt": training_prompt}}
            )
        except Exception as e:
            print(f"Error updating document {movie['_id']} in MongoDB: {e}")
            traceback.print_exc()
        
        print(f"Updated document {movie['_id']} with training prompt.")
    except Exception as e:
        print(f"Error processing document {movie.get('_id')}: {e}")
        traceback.print_exc()
        
    print("Batch processing complete.")

# Uncomment the update function you want to run

start_after_id = "670d426128ad7f7da577c9cd"

query_filter = {"_id": {"$gte": ObjectId(start_after_id)}}
batch_size = 300000
cursor = movieDetails.find(query_filter).sort("_id", 1).limit(batch_size)

while True:
    batch = list(cursor)
    if not batch:
        break
    for movie in batch:
        try:
            # update_documents_posterImage(movie)
            classify_style(movie)
            # update_documents_trainingPrompt(movie)
            # print() # Comment this line out when you run any of the update functions
        except Exception as e:
            print("Error in processing the movie")
            continue
    

# Close connection once finished
db_client.close()
print("MongoDB connection closed.")
