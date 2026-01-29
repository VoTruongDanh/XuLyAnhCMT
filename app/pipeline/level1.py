import logging
import torch
from app.config import settings

# Lazy load 
clip_classifier = None

def get_clip_classifier():
    global clip_classifier
    if clip_classifier is None:
        try:
            from transformers import pipeline
            print("Loading Level 1 Model (CLIP Zero-shot)...")
            # Using openai/clip-vit-base-patch32 for good balance of speed/accuracy
            # or 'laion/CLIP-ViT-B-32-laion2B-s34B-b79K' for multi-lingual if needed, but English is fine.
            clip_classifier = pipeline("zero-shot-image-classification", model="openai/clip-vit-base-patch32")
            print("Level 1 Model Loaded.")
        except Exception as e:
            print(f"Failed to load Level 1 Model: {e}")
            return None
    return clip_classifier

def run_level1_checks(img_cv, img_pil, filename="", file_format="", config_override=None):
    """
    Level 1: Style Detection (Real Photo vs Illustration/Art).
    Uses CLIP Zero-Shot Classification.
    """
    scores = {}
    reasons = []
    
    clf = get_clip_classifier()
    if clf is None:
        scores['l1_error'] = "Model Load Failed"
        return True, "ALLOW", reasons, scores

    try:
        # Define candidate labels
        # These prompts are robust for CLIP
        labels = [
            "a real photo taken by a camera", 
            "a drawing or illustration or artwork"
        ]
        
        results = clf(img_pil, candidate_labels=labels)
        # Result example: [{'score': 0.99, 'label': 'a real photo...'}, ...]
        
        real_score = 0.0
        art_score = 0.0
        
        for r in results:
            if "real photo" in r['label']:
                real_score = r['score']
            elif "drawing" in r['label']:
                art_score = r['score']
                
        scores['real_prob'] = float(real_score)
        scores['art_prob'] = float(art_score)
        
        # Threshold decision
        # If Art probability is overwhelmingly high
        ART_THRESHOLD = 0.70 # Lowered from 0.8 to catch 78% cases
        
        if art_score > ART_THRESHOLD:
            reasons.append(f"ILLUSTRATION_OR_ARTWORK ({round(art_score*100)}%)")
            return False, "HARD_BLOCK", reasons, scores
            
        return True, "ALLOW", reasons, scores

    except Exception as e:
        print(f"Level 1 Runtime Error: {e}")
        scores['l1_error'] = str(e)
        return True, "ALLOW", reasons, scores
