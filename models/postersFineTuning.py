import os
import pymongo
import requests
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
pipeline.to("cuda")  # Move model to GPU if available
print("Model and tokenizer initialized.")

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

        # Tokenize the prompt
        inputs = tokenizer(prompt, return_tensors="pt", padding="max_length", truncation=True, max_length=77)
        print(f"Tokenized prompt for '{doc['title']}'.")

        return {
            "pixel_values": pipeline.feature_extractor(image, return_tensors="pt")["pixel_values"].squeeze(0),
            "input_ids": inputs["input_ids"].squeeze(0)
        }

# Function to load a batch with at least one movie per director, adding additional movies until batch size is met
def load_batch(max_batch_size):
    print("Loading a new batch...")
    batch = []
    director_movie_counts = {}

    pipeline = [
        {"$match": {"trainingPrompt": {"$exists": True}, "posterLink": {"$exists": True}}},
        {"$group": {"_id": "$director"}}
    ]
    directors = movieDetails.aggregate(pipeline)
    director_list = [director["_id"] for director in directors]
    print(f"Found {len(director_list)} unique directors.")

    for director in director_list:
        cursor = movieDetails.find(
            {"director": director, "trainingPrompt": {"$exists": True}, "posterLink": {"$exists": True}}
        ).sort("_id", 1)
        movies = list(cursor)

        if movies:
            batch.append(movies[0])
            director_movie_counts[director] = 1
            print(f"Added first movie for director '{director}'.")

    batch_size = len(batch)
    while batch_size < max_batch_size:
        added_any = False
        for director in director_list:
            current_count = director_movie_counts.get(director, 0)
            cursor = movieDetails.find(
                {"director": director, "trainingPrompt": {"$exists": True}, "posterLink": {"$exists": True}}
            ).sort("_id", 1).skip(current_count).limit(1)

            additional_movies = list(cursor)
            if additional_movies:
                batch.append(additional_movies[0])
                director_movie_counts[director] = current_count + 1
                batch_size += 1
                added_any = True
                print(f"Added additional movie for director '{director}' (total now: {current_count + 1}).")

                if batch_size >= max_batch_size:
                    break

        if not added_any:
            print("No additional movies could be added in this pass.")
            break

    print(f"Loaded batch with {len(batch)} documents for training.")
    return batch if batch else None

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
            pixel_values = batch["pixel_values"].to("cuda")
            input_ids = batch["input_ids"].to("cuda")

            # Forward pass
            noise = torch.randn_like(pixel_values).to("cuda")
            timesteps = torch.randint(0, 1000, (pixel_values.shape[0],), device="cuda").long()

            loss = pipeline.unet(pixel_values, timesteps, encoder_hidden_states=input_ids, noise=noise).loss
            loss.backward()
            optimizer.step()

            print(f"Batch Loss: {loss.item()}")

    print("Completed training for the current batch.")

# Main function for batch training
def batch_training(max_batch_size=1000, num_epochs=1):
    print(f"Starting batch training with max batch size: {max_batch_size}")

    while True:
        documents = load_batch(max_batch_size)
        if not documents:
            print("No more documents left to train on.")
            break

        train_on_batch(documents, num_epochs)

# Run the batch training process
batch_training(max_batch_size=1000, num_epochs=1)

# Close MongoDB connection
client.close()
print("MongoDB connection closed.")