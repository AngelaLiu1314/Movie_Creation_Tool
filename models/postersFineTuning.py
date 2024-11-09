import os
import pymongo
import requests
from io import BytesIO
from PIL import Image
from dotenv import load_dotenv
from torch.utils.data import Dataset, DataLoader
from diffusers import StableDiffusionPipeline, StableDiffusionTrainer
from transformers import AutoTokenizer
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

# Function to load a batch with at least one movie per director, adding additional movies until batch size is met
def load_batch(max_batch_size):
    """
    Loads a batch of documents with at least one movie per director, adding additional
    movies from directors with multiple records until reaching the specified batch size.
    """
    # Initialize batch and a tracker for each director's processed count
    batch = []
    director_movie_counts = {}
    
    # Find all unique directors with a movie that has 'trainingPrompt' and 'posterLink'
    pipeline = [
        {"$match": {"trainingPrompt": {"$exists": True}, "posterLink": {"$exists": True}}},
        {"$group": {"_id": "$director"}}
    ]
    directors = movieDetails.aggregate(pipeline)
    director_list = [director["_id"] for director in directors]
    
    # Ensure at least one movie per director in the batch
    for director in director_list:
        # Fetch all movies for the current director, sorted by `_id` to ensure consistent ordering
        cursor = movieDetails.find(
            {"director": director, "trainingPrompt": {"$exists": True}, "posterLink": {"$exists": True}}
        ).sort("_id", 1)
        
        movies = list(cursor)
        
        # Add the first movie for each director to the batch
        if movies:
            batch.append(movies[0])
            director_movie_counts[director] = 1  # Track how many movies have been added for this director
    
    # Add additional movies from directors until batch size is reached
    batch_size = len(batch)
    while batch_size < max_batch_size:
        added_any = False  # Track if we add any movie in this loop

        # Try to add one more movie per director where possible
        for director in director_list:
            current_count = director_movie_counts.get(director, 0)
            cursor = movieDetails.find(
                {"director": director, "trainingPrompt": {"$exists": True}, "posterLink": {"$exists": True}}
            ).sort("_id", 1).skip(current_count).limit(1)  # Skip already added movies for this director

            additional_movies = list(cursor)
            if additional_movies:
                batch.append(additional_movies[0])
                director_movie_counts[director] = current_count + 1
                batch_size += 1
                added_any = True  # Movie was added

                if batch_size >= max_batch_size:
                    break  # Exit if batch size is reached

        # If we could not add any new movie in this pass, stop to avoid infinite loop
        if not added_any:
            break

    print(f"Loaded {len(batch)} documents for training.")
    return batch if batch else None

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
def batch_training(max_batch_size=1000):
    """
    Main loop for batch training, iterating through documents in batches.
    """
    print(f"Starting batch training with max batch size: {max_batch_size}")

    # Loop until there are no more documents left to train on
    while True:
        # Load a batch of documents with the specified constraints
        documents = load_batch(max_batch_size)
        if not documents:
            print("No more documents left to train on.")
            break

        # Train on the current batch
        train_on_batch(documents)

# Run the batch training process
batch_training(max_batch_size=1000)

# Close MongoDB connection
client.close()
print("MongoDB connection closed.")