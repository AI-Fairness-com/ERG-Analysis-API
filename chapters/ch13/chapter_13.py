"""Chapter 13: Deep learning with a Vision Transformer.

Code from Chapter 13 of "Hands-On Electroretinography in the Age of
AI", in the order of the book: fine-tuning the ViT with class weights,
differential learning rates and early stopping; the DenseNet121
comparison model; and the FID check for synthetic spectrograms.
A few random images are made before training so that the script runs
on its own; replace them with your spectrogram loaders. The first run
downloads the pretrained weights. A GPU is strongly advised (Colab).
"""

import os
import torch
import torch.nn as nn
import timm
from torch.optim import AdamW
from torch.optim.lr_scheduler import CosineAnnealingLR

NUM_CLASSES = 6      # 2 for Stage 1, 6 for Stage 2
NUM_EPOCHS = 100
PATIENCE = 10        # stop after 10 epochs without improvement
device = 'cuda' if torch.cuda.is_available() else 'cpu'

# train_loader and val_loader yield (spectrogram batch, label batch).
# Spectrogram batches have shape (batch, 3, 224, 224).
# train_labels is a 1D tensor with the class of every training
# example, including any synthetic examples added within the
# Chapter 10 cap, so the weights are computed after they are added.

# ── Simulated data so that this script runs on its own ─────────────────
# The book's code uses train_loader, val_loader and train_labels from
# the project's spectrogram dataset (Chapter 8). Real spectrograms are
# not shipped with the repository, so the block below makes a few random
# images of the right shape. The model learns nothing from them; they
# only show that the code runs. Replace them with your own loaders.
from torch.utils.data import DataLoader, TensorDataset

_gen = torch.Generator().manual_seed(42)
_X = torch.rand(24, 3, 224, 224, generator=_gen)
_y = torch.arange(24) % NUM_CLASSES
train_labels = _y[:18]
train_loader = DataLoader(TensorDataset(_X[:18], _y[:18]), batch_size=6,
                          shuffle=True)
val_loader = DataLoader(TensorDataset(_X[18:], _y[18:]), batch_size=6)

# Class weights: rarer classes receive larger weights in the loss
counts = torch.bincount(train_labels, minlength=NUM_CLASSES).float()
class_weights = counts.sum() / (NUM_CLASSES * counts.clamp(min=1))

# Load the pretrained model and replace its head with a new one
model = timm.create_model('vit_small_r26_s32_224', pretrained=True,
                          num_classes=NUM_CLASSES).to(device)

# Differential learning rates: the backbone rate is 10 times lower
backbone_params = [p for n, p in model.named_parameters()
                   if not n.startswith('head')]
head_params = [p for n, p in model.named_parameters()
               if n.startswith('head')]

optimizer = AdamW([
    {'params': backbone_params, 'lr': 1e-5},
    {'params': head_params, 'lr': 1e-4},
], weight_decay=1e-2)
scheduler = CosineAnnealingLR(optimizer, T_max=NUM_EPOCHS,
                              eta_min=1e-7)
criterion = nn.CrossEntropyLoss(weight=class_weights.to(device))

# Training loop with early stopping on validation loss
os.makedirs('models', exist_ok=True)
best_val_loss = float('inf')
patience_count = 0

for epoch in range(NUM_EPOCHS):
    model.train()
    train_loss = 0.0
    for X_batch, y_batch in train_loader:
        X_batch, y_batch = X_batch.to(device), y_batch.to(device)
        optimizer.zero_grad()
        loss = criterion(model(X_batch), y_batch)
        loss.backward()
        # Clipping limits very large updates (Steiner et al., 2022)
        nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
        optimizer.step()
        train_loss += loss.item()
    train_loss /= len(train_loader)

    model.eval()
    val_loss = 0.0
    with torch.no_grad():
        for X_val, y_val in val_loader:
            logits = model(X_val.to(device))
            val_loss += criterion(logits, y_val.to(device)).item()
    val_loss /= len(val_loader)
    scheduler.step()

    # Keep the checkpoint with the lowest validation loss
    if val_loss < best_val_loss:
        best_val_loss = val_loss
        patience_count = 0
        torch.save(model.state_dict(), 'models/vit_best.pt')
    else:
        patience_count += 1

    print(f'Epoch {epoch:3d}  train_loss={train_loss:.4f}  '
          f'val_loss={val_loss:.4f}  '
          f'patience={patience_count}/{PATIENCE}')
    if patience_count >= PATIENCE:
        print(f'Early stopping at epoch {epoch}.')
        break

import timm
import torch.nn as nn

NUM_CLASSES = 6      # 2 for Stage 1, 6 for Stage 2

densenet = timm.create_model('densenet121', pretrained=True,
                             num_classes=NUM_CLASSES)
# Replace the classifier with one that adds dropout before the
# final linear layer (a design choice of this project)
densenet.classifier = nn.Sequential(
    nn.Dropout(p=0.3),
    nn.Linear(densenet.num_features, NUM_CLASSES),
)

# FID computation for synthetic spectrogram quality validation
from pytorch_fid import fid_score

FID_THRESHOLD = 50.0     # design choice of this project (§13.6.2)


def compute_fid(real_image_dir: str,
                fake_image_dir: str,
                device: str = 'cuda') -> float:
    """
    Compute the Frechet Inception Distance between real and
    synthetic spectrograms. A value below FID_THRESHOLD is
    required before synthetic data join the training set.
    """
    fid = fid_score.calculate_fid_given_paths(
        [real_image_dir, fake_image_dir],
        batch_size=32,
        device=device,
        dims=2048,
    )
    status = 'PASS' if fid < FID_THRESHOLD else 'FAIL, retrain GAN'
    print(f'FID = {fid:.2f} [{status}]')
    return fid
