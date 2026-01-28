import logging
import time
import torch
from app.config import settings

# Lazy load transformers to keep startup fast (or manageable)
pipeline = None
classifier = None

def get_classifier():
    global classifier
    if classifier is None:
        try:
            from transformers import pipeline
            print("Loading Level 1 Model (AI vs Human)...")
            # Using a lightweight, effective model for AI detection
            # Using 'umm-maybe/AI-image-detector' which is often more balanced for real photos
            classifier = pipeline("image-classification", model="umm-maybe/AI-image-detector")
            print("Level 1 Model Loaded.")
        except Exception as e:
            print(f"Failed to load Level 1 Model: {e}")
            return None
    return classifier

def run_level1_checks(img_cv, img_pil, filename="", file_format="", config_override=None):
    """
    Level 1: AI Generated Image Detection.
    Uses 'Ateeqq/ai-vs-human-image-detector'.
    """
    scores = {}
    reasons = []
    
    # 1. Load Model
    clf = get_classifier()
    if clf is None:
        # If model fails to load, fail open (allow) or warn? 
        # For now, let's allow but log potential error.
        scores['l1_error'] = "Model Load Failed"
        return True, "ALLOW", reasons, scores

    try:
        # 2. Predict
        # Pipeline accepts PIL Image
        results = clf(img_pil)
        # Result format: [{'label': 'real', 'score': 0.99}, {'label': 'fake', 'score': 0.01}]
        # Check labels manually as order might vary
        
        ai_score = 0.0
        human_score = 0.0
        
        for r in results:
            label = r['label'].lower()
            score = r['score']
            if "fake" in label or "ai" in label or "artificial" in label:
                ai_score = score
            elif "real" in label or "human" in label:
                human_score = score
                
        scores['ai_prob'] = float(ai_score)
        scores['human_prob'] = float(human_score)
        
        # 3. Decision
        # Threshold can be tuned. Start with 0.8 to be safe against false positives.
        AI_THRESHOLD = 0.90 
        
        if ai_score > AI_THRESHOLD:
            reasons.append(f"AI_GENERATED_CONTENT ({round(ai_score*100)}%)")
            return False, "HARD_BLOCK", reasons, scores
            
        return True, "ALLOW", reasons, scores

    except Exception as e:
        print(f"Level 1 Runtime Error: {e}")
        scores['l1_error'] = str(e)
        return True, "ALLOW", reasons, scores
