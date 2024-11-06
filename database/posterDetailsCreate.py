import json
import os
from io import BytesIO
import requests
from PIL import Image
import torch
from torchvision import transforms, models
from dotenv import load_dotenv
import pymongo
import certifi
from torchvision.models import ResNet18_Weights

# Load environment variables
load_dotenv()
mongodb_uri = os.getenv('Mongo_URI')

# MongoDB connection setup
try:
    client = pymongo.MongoClient(mongodb_uri, tlsCAFile=certifi.where())
    db = client.get_database("movies")
    movieDetails = db.get_collection("movieDetails")
    posterDetails = db.get_collection("posterDetails")
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

        print(f"Predicted art style for the poster for {imdbID}, {title}: {predicted_class}")
        return predicted_class

    except requests.exceptions.RequestException as e:
        print(f"Error downloading image: {e}")
        return None

# Example usage
style = classify_style("tt0034492")

client.close()
print("MongoDB connection closed.")