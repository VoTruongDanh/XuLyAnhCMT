from transformers import pipeline
from PIL import Image
import os

FAKE_MODEL_NAME = "prithivMLmods/Deep-Fake-Detector-v2-Model"
# Use the image path from metadata
img_path = r"C:/Users/Pls/.gemini/antigravity/brain/1a114a4c-56ef-4d45-b812-6285720bacf1/uploaded_media_1769670228805.png"

print(f"Loading {FAKE_MODEL_NAME}...")
pipe = pipeline("image-classification", model=FAKE_MODEL_NAME)

print(f"Processing {img_path}...")
img = Image.open(img_path)
results = pipe(img)

print("--- Raw Results ---")
print(results)
