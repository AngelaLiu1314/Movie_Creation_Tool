import torch
from torch.utils.data import DataLoader
from torchvision import datasets, transforms

import torch.nn as nn
import torchvision.models as models
from torchvision.models import ResNet18_Weights
import torch.optim as optim

# Define image transformations
# Resize to 224x224 pixels and convert to a tensor (numeric format for the model)
data_transforms = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.RandomHorizontalFlip(),
    transforms.RandomRotation(10),
    transforms.ColorJitter(brightness=0.2, contrast=0.2, saturation=0.2, hue=0.1),
    transforms.ToTensor()
])

# Load dataset from the posters folder
dataset = datasets.ImageFolder(root='models/posters', transform=data_transforms)

# Split dataset into training and validation sets
train_size = int(0.8 * len(dataset))
val_size = len(dataset) - train_size
train_dataset, val_dataset = torch.utils.data.random_split(dataset, [train_size, val_size])

# Create DataLoader for batch processing
train_loader = DataLoader(train_dataset, batch_size=32, shuffle=True)
val_loader = DataLoader(val_dataset, batch_size=32, shuffle=False)

# Load pretrained ResNet18 model
model = models.resnet18(weights=ResNet18_Weights.IMAGENET1K_V1)

# Modify the final layer to output 3 classes (one for each folder)
num_features = model.fc.in_features
model.fc = nn.Sequential(
    nn.Dropout(0.5),  # Dropout to help prevent overfitting
    nn.Linear(num_features, 3) # 3 classes: photography, illustration, 3D digital art
)  

# Send model to GPU if available
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
model = model.to(device)

# Define loss function and optimizer
criterion = nn.CrossEntropyLoss()
optimizer = optim.Adam(model.parameters(), lr=0.001)

# Implement learning rate scheduler
scheduler = torch.optim.lr_scheduler.StepLR(optimizer, step_size=5, gamma=0.1)

# Validation function
def validate_model(model, val_loader):
    model.eval()
    correct = 0
    total = 0
    with torch.no_grad():
        for images, labels in val_loader:
            images, labels = images.to(device), labels.to(device)
            outputs = model(images)
            _, predicted = outputs.max(1)
            total += labels.size(0)
            correct += predicted.eq(labels).sum().item()
    val_accuracy = 100 * correct / total
    print(f"Validation Accuracy: {100 * correct / total:.2f}%\n")
    return val_accuracy

# Function to train the model
def train_model(model, train_loader, val_loader, criterion, optimizer, num_epochs=10, patience = 3):
    best_val_accuracy = 0.0
    patience_counter = 0
    
    for epoch in range(num_epochs):
        model.train()
        running_loss = 0.0
        correct = 0
        total = 0

        for images, labels in train_loader:
            images, labels = images.to(device), labels.to(device)

            # Forward pass (get predictions)
            outputs = model(images)
            loss = criterion(outputs, labels)

            # Backward pass (adjust model)
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()

            running_loss += loss.item()
            _, predicted = outputs.max(1)
            total += labels.size(0)
            correct += predicted.eq(labels).sum().item()

        train_accuracy = 100 * correct / total
        print(f"Epoch [{epoch+1}/{num_epochs}], Loss: {running_loss/len(train_loader):.4f}, Accuracy: {train_accuracy:.2f}%")

        # Validate the model after each epoch
        val_accuracy = validate_model(model, val_loader)
        scheduler.step()  # Adjust learning rate

        # Early stopping check
        if val_accuracy > best_val_accuracy:
            best_val_accuracy = val_accuracy
            patience_counter = 0  # Reset counter if validation accuracy improves
            torch.save(model.state_dict(), 'models/best_style_classifier.pth')  # Save best model
            print("New best model saved.")
        else:
            patience_counter += 1
            if patience_counter >= patience:
                print("Early stopping triggered.")
                break
    print("Training complete.")
        
# Train the model
train_model(model, train_loader, val_loader, criterion, optimizer, num_epochs=10, patience=3)