import torch
from torch.utils.data import DataLoader
from torchvision import datasets, transforms

# Define image transformations
# Resize to 224x224 pixels and convert to a tensor (numeric format for the model)
data_transforms = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor()
])

# Load dataset from the posters folder
dataset = datasets.ImageFolder(root='models/posters', transform=data_transforms)

# Split dataset into training and validation sets
train_size = int(0.8 * len(dataset))
val_size = len(dataset) - train_size
train_dataset, val_dataset = torch.utils.data.random_split(dataset, [train_size, val_size])
