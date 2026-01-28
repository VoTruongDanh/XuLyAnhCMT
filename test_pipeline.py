import sys
import os
import torch
import numpy as np
from PIL import Image

# Add current dir to path
sys.path.append(os.getcwd())

from app.pipeline.level1 import run_level1_checks
from app.pipeline.level2 import run_level2_checks

print(f"Torch Version: {torch.__version__}")
print(f"CUDA Available: {torch.cuda.is_available()}")

# Create dummy image
img_pil = Image.new('RGB', (224, 224), color = (73, 109, 137))
img_cv = np.array(img_pil)

print("\n--- Testing Level 1 ---")
try:
    l1_passed, l1_decision, l1_reasons, l1_scores = run_level1_checks(img_cv, img_pil, filename="test.jpg")
    print(f"L1 Result: {l1_decision}")
    print(f"L1 Scores: {l1_scores}")
except Exception as e:
    print(f"L1 CRASHED: {e}")

print("\n--- Testing Level 2 ---")
try:
    l2_passed, l2_decision, l2_reasons, l2_scores = run_level2_checks(img_cv, img_pil, filename="test.jpg")
    print(f"L2 Result: {l2_decision}")
    print(f"L2 Scores: {l2_scores}")
except Exception as e:
    print(f"L2 CRASHED: {e}")
