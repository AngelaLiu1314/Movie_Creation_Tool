import os
import pymongo
import requests
from io import BytesIO
from PIL import Image
from dotenv import load_dotenv
from torch.utils.data import Dataset, DataLoader
from diffusers import StableDiffusionPipeline, StableDiffusionTrainer
from transformers import AutoTokenizer
import torch
import certifi
from tqdm import tqdm

# Load environment variables
load_dotenv()
mongodb_uri = os.getenv('Mongo_URI')

# Connect to MongoDB
client = pymongo.MongoClient(mongodb_uri, tlsCAFile=certifi.where())
db = client["movies"]
movieDetails = db.get_collection("movieDetails")

# Initialize Stable Diffusion pipeline and tokenizer
model_id = "CompVis/stable-diffusion-v1-4"
pipeline = StableDiffusionPipeline.from_pretrained(model_id)
tokenizer = AutoTokenizer.from_pretrained(model_id)

# Define the PosterDataset class
class PosterDataset(Dataset):
    def __init__(self, documents):
        """
        Initialize with a list of documents from MongoDB. Each document contains
        'trainingPrompt' and 'posterLink' fields for the prompt and image URL.
        """
        self.documents = documents

    def __len__(self):
        return len(self.documents)

    def __getitem__(self, idx):
        """
        Fetches and processes an item by its index, including:
        - Downloading the poster image
        - Tokenizing the prompt
        """
        doc = self.documents[idx]
        image_url = doc.get("posterLink")
        prompt = doc.get("trainingPrompt")

        if not image_url or not prompt:
            raise ValueError(f"Missing data for document ID: {doc['_id']}")

        # Fetch image from URL
        response = requests.get(image_url, timeout=10)
        image = Image.open(BytesIO(response.content)).convert("RGB")

        # Tokenize the prompt
        inputs = tokenizer(prompt, return_tensors="pt", padding="max_length", truncation=True, max_length=77)

        return {
            "pixel_values": pipeline.feature_extractor(image, return_tensors="pt")["pixel_values"].squeeze(0),
            "input_ids": inputs["input_ids"].squeeze(0)
        }

# Function to load a batch of documents with training prompts
def load_batch(batch_size, start_after_id=None):
    """
    Loads a batch of documents from MongoDB with existing 'trainingPrompt' and 'posterLink'.
    """
    query = {"trainingPrompt": {"$exists": True}, "posterLink": {"$exists": True}}
    if start_after_id:
        query["_id"] = {"$gt": start_after_id}

    cursor = movieDetails.find(query).sort("_id", 1).limit(batch_size)
    documents = list(cursor)
    if documents:
        print(f"Loaded {len(documents)} documents for training.")
        return documents
    else:
        return None

# Fine-tuning function for a single batch
def train_on_batch(documents):
    """
    Trains the model on a single batch of documents using Stable Diffusion's Trainer.
    """
    # Initialize dataset and dataloader for the batch
    dataset = PosterDataset(documents)
    dataloader = DataLoader(dataset, batch_size=4, shuffle=True)

    # Initialize the trainer
    trainer = StableDiffusionTrainer(
        model=pipeline.unet,
        dataloader=dataloader,
        text_encoder=pipeline.text_encoder,
        vae=pipeline.vae,
        noise_scheduler=pipeline.noise_scheduler,
        tokenizer=tokenizer,
        num_train_epochs=1,  # Adjust based on needs
        gradient_accumulation_steps=4,
    )

    # Train on this batch
    trainer.train()
    print("Batch training complete.")

# Main function for batch training
def batch_training(batch_size=1000):
    """
    Main loop for batch training, iterating through documents in batches.
    """
    start_after_id = None

    # Loop until there are no more documents left to train on
    while True:
        # Load a batch of documents
        documents = load_batch(batch_size, start_after_id)
        if not documents:
            print("No more documents left to train on.")
            break

        # Train on the current batch
        train_on_batch(documents)

        # Update starting point for the next batch
        start_after_id = documents[-1]["_id"]

# Run the batch training process
batch_training(batch_size=1000)

# Close MongoDB connection
client.close()
print("MongoDB connection closed.")