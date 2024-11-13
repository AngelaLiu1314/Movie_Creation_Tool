import os
import pymongo
import requests
import random
from io import BytesIO
from PIL import Image
from dotenv import load_dotenv
from torch.utils.data import Dataset, DataLoader
from transformers import AutoTokenizer, AutoModel
import torch
import torch.nn as nn
import torch.optim as optim
import torchvision.transforms as transforms
from torchvision import models
import certifi

# Load environment variables
load_dotenv()
mongodb_uri = os.getenv('Mongo_URI')

# Connect to MongoDB
print("Connecting to MongoDB...")
client = pymongo.MongoClient(mongodb_uri, tlsCAFile=certifi.where())
db = client["movies"]
movieDetails = db.get_collection("movieDetails")
print("Connected to MongoDB and accessed 'movieDetails' collection.")

# Initialize smaller tokenizer and text model (distilBERT) with fp16
print("Initializing distilBERT tokenizer and model for text encoding...")
tokenizer = AutoTokenizer.from_pretrained("distilbert-base-uncased")
text_encoder = AutoModel.from_pretrained("distilbert-base-uncased").half()
text_encoder.to("mps")

# Initialize lightweight vision model (EfficientNet) with fp16
print("Initializing EfficientNet for image encoding...")
vision_encoder = models.efficientnet_b0(pretrained=True).eval().half().to("mps")

# Define image preprocessing
transform = transforms.Compose([
    transforms.Resize((128, 128)),
    transforms.ToTensor(),
    transforms.ConvertImageDtype(torch.float16)
])

# Projection layer to align the output dimensions of the encoders
class ProjectionLayer(nn.Module):
    def __init__(self, input_dim, output_dim):
        super(ProjectionLayer, self).__init__()
        self.fc = nn.Linear(input_dim, output_dim)

    def forward(self, x):
        return self.fc(x)

# Initialize projection layer with appropriate dimensions
projection_layer = ProjectionLayer(vision_encoder.classifier[1].in_features, text_encoder.config.hidden_size).to("mps")

# Define the PosterDataset class
class PosterDataset(Dataset):
    def __init__(self, documents):
        self.documents = documents
        print(f"PosterDataset initialized with {len(documents)} documents.")

    def __len__(self):
        return len(self.documents)

    def __getitem__(self, idx):
        doc = self.documents[idx]
        image_url = doc.get("posterLink")
        prompt = doc.get("trainingPrompt")

        if not image_url or not prompt:
            raise ValueError(f"Missing data for document ID: {doc['_id']}")

        try:
            # Fetch and preprocess image
            response = requests.get(image_url, timeout=10)
            image = Image.open(BytesIO(response.content)).convert("RGB")
            image = transform(image)  # Image should now have shape (3, 128, 128)
            print(f"Fetched and preprocessed image for '{doc['title']}' directed by {doc['director']}.")

            # Tokenize and encode the prompt
            inputs = tokenizer(prompt, return_tensors="pt", padding="max_length", truncation=True, max_length=77)
            text_embeddings = text_encoder(inputs.input_ids.to("mps"), attention_mask=inputs.attention_mask.to("mps"))[0].squeeze(0).half()
            print(f"Tokenized and encoded prompt for '{doc['title']}'.")

            return {
                "pixel_values": image,
                "input_ids": text_embeddings
            }

        except Exception as e:
            print(f"Error processing image for '{doc['title']}': {e}")
            return self.__getitem__((idx + 1) % len(self.documents))

# Function to organize documents by genre
def organize_by_genre():
    print("Organizing documents by genre...")
    genre_pools = {}
    query = {"trainingPrompt": {"$exists": True}, "posterLink": {"$exists": True}}
    documents = movieDetails.find(query)

    for doc in documents:
        genres = doc.get("genre", [])
        for genre in genres:
            if genre not in genre_pools:
                genre_pools[genre] = []
            genre_pools[genre].append(doc)

    print(f"Organized documents into {len(genre_pools)} genre pools.")
    return genre_pools

# Function to load a random batch with samples from each genre pool
def load_batch(genre_pools, max_batch_size):
    print("Loading a new batch...")
    batch = []
    genres = list(genre_pools.keys())
    samples_per_genre = max(1, max_batch_size // len(genres))

    for genre in genres:
        genre_pool = genre_pools[genre]
        selected_movies = random.sample(genre_pool, min(samples_per_genre, len(genre_pool)))
        batch.extend(selected_movies)

    random.shuffle(batch)
    print(f"Loaded batch with {len(batch)} documents for training.")
    return batch[:max_batch_size]

# Fine-tuning function for a single batch using a custom training loop
def train_on_batch(documents, num_epochs=1):
    dataset = PosterDataset(documents)
    dataloader = DataLoader(dataset, batch_size=1, shuffle=True)
    optimizer = optim.AdamW(list(text_encoder.parameters()) + list(projection_layer.parameters()), lr=5e-5)
    print("Starting training for the current batch...")

    for epoch in range(num_epochs):
        print(f"Epoch {epoch + 1}/{num_epochs}")
        for batch in dataloader:
            optimizer.zero_grad()
            pixel_values = batch["pixel_values"].unsqueeze(0).to("mps")  # Reshape to [1, 3, 128, 128]
            input_ids = batch["input_ids"].to("mps")

            # Image encoding
            with torch.no_grad():
                image_features = vision_encoder(pixel_values).flatten()

            # Project image features to match text embedding size
            image_features_proj = projection_layer(image_features)

            # Calculate loss on the flattened projections
            loss = torch.nn.functional.mse_loss(image_features_proj, input_ids.flatten())
            print(f"Loss: {loss.item()}")
            loss.backward()
            optimizer.step()

    print("Completed training for the current batch.")

# Main function for batch training
def batch_training(max_batch_size=1000, num_epochs=1):
    print(f"Starting batch training with max batch size: {max_batch_size}")
    genre_pools = organize_by_genre()

    while True:
        documents = load_batch(genre_pools, max_batch_size)
        if not documents:
            print("No more documents left to train on.")
            break

        train_on_batch(documents, num_epochs)

# Run the batch training process
batch_training(max_batch_size=1000, num_epochs=1)

# Close MongoDB connection
client.close()
print("MongoDB connection closed.")