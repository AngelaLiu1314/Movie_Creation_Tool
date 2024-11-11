import os
import pymongo
import requests
import random
from io import BytesIO
from PIL import Image
from dotenv import load_dotenv
from torch.utils.data import Dataset, DataLoader
from diffusers import StableDiffusionPipeline
from transformers import CLIPTokenizer, CLIPTextModel
import torch
import torch.optim as optim
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

# Initialize Stable Diffusion pipeline and CLIP tokenizer/model
print("Initializing Stable Diffusion pipeline and CLIP text model/tokenizer...")
model_id = "CompVis/stable-diffusion-v1-4"
pipeline = StableDiffusionPipeline.from_pretrained(model_id)
tokenizer = CLIPTokenizer.from_pretrained("openai/clip-vit-large-patch14")
text_encoder = CLIPTextModel.from_pretrained("openai/clip-vit-large-patch14")
pipeline.to("mps")  # Use MPS (Metal Performance Shaders) for Apple Silicon
print("Model and tokenizer initialized on MPS backend.")

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

        # Fetch image from URL
        response = requests.get(image_url, timeout=10)
        image = Image.open(BytesIO(response.content)).convert("RGB")
        print(f"Fetched image for '{doc['title']}' directed by {doc['director']}.")

        # Tokenize and encode the prompt
        inputs = tokenizer(prompt, return_tensors="pt", padding="max_length", truncation=True, max_length=77)
        text_embeddings = text_encoder(inputs.input_ids.to("mps"))[0]  # Move to MPS
        print(f"Tokenized and encoded prompt for '{doc['title']}'.")

        return {
            "pixel_values": pipeline.feature_extractor(image, return_tensors="pt")["pixel_values"].squeeze(0).to("mps"),
            "input_ids": text_embeddings.squeeze(0)
        }

# Function to organize documents by genre
def organize_by_genre():
    print("Organizing documents by genre...")
    genre_pools = {}

    # Query documents with trainingPrompt and posterLink
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

    # Calculate approximate samples per genre based on total batch size
    samples_per_genre = max(1, max_batch_size // len(genres))

    for genre in genres:
        genre_pool = genre_pools[genre]
        if len(genre_pool) > samples_per_genre:
            selected_movies = random.sample(genre_pool, samples_per_genre)
        else:
            selected_movies = genre_pool  # If fewer than needed, take all

        batch.extend(selected_movies)

    # Shuffle the batch for randomness
    random.shuffle(batch)
    print(f"Loaded batch with {len(batch)} documents for training.")
    return batch[:max_batch_size]

# Fine-tuning function for a single batch using a custom training loop
def train_on_batch(documents, num_epochs=1):
    dataset = PosterDataset(documents)
    dataloader = DataLoader(dataset, batch_size=4, shuffle=True)

    # Set up the optimizer
    optimizer = optim.AdamW(pipeline.unet.parameters(), lr=5e-5)
    print("Starting training for the current batch...")

    for epoch in range(num_epochs):
        print(f"Epoch {epoch + 1}/{num_epochs}")
        for batch in dataloader:
            optimizer.zero_grad()

            # Get inputs
            pixel_values = batch["pixel_values"]
            input_ids = batch["input_ids"]

            # Forward pass
            noise = torch.randn_like(pixel_values).to("mps")
            timesteps = torch.randint(0, 1000, (pixel_values.shape[0],), device="mps").long()

            loss = pipeline.unet(pixel_values, timesteps, encoder_hidden_states=input_ids, noise=noise).loss
            loss.backward()
            optimizer.step()

            print(f"Batch Loss: {loss.item()}")

    print("Completed training for the current batch.")

# Main function for batch training
def batch_training(max_batch_size=1000, num_epochs=1):
    print(f"Starting batch training with max batch size: {max_batch_size}")

    # Organize documents into genre pools
    genre_pools = organize_by_genre()

    # Loop until all documents are exhausted or training is complete
    while True:
        # Load a batch of documents from genre pools
        documents = load_batch(genre_pools, max_batch_size)
        if not documents:
            print("No more documents left to train on.")
            break

        # Train on the current batch
        train_on_batch(documents, num_epochs)

# Run the batch training process
batch_training(max_batch_size=1000, num_epochs=1)

# Close MongoDB connection
client.close()
print("MongoDB connection closed.")