import logging
import time
import torch
from app.config import settings

# Lazy load transformers to keep startup fast (or manageable)
# Lazy load transformers
pipeline = None
MODELS_CACHE = {}

DEFAULT_MODEL = "ensemble"

def get_classifier(model_name=DEFAULT_MODEL):
    global MODELS_CACHE
    
    if model_name not in MODELS_CACHE:
        try:
            from transformers import pipeline
            print(f"Loading Level 2 Model ({model_name})...")
            classifier = pipeline("image-classification", model=model_name)
            MODELS_CACHE[model_name] = classifier
            print(f"Level 2 Model ({model_name}) Loaded.")
        except Exception as e:
            print(f"Failed to load Level 2 Model ({model_name}): {e}")
            return None
            
    return MODELS_CACHE[model_name]

def run_level2_checks(img_cv, img_pil, filename="", file_format="", config_override=None):
    """
    Level 2: AI Generated Image Detection.
    Allows selecting different models via config_override['ai_model'].
    """
    scores = {}
    reasons = []
    
    # Determine which model to use
    model_name = DEFAULT_MODEL
    if config_override and 'ai_model' in config_override:
        model_name = config_override['ai_model']
    
    # --- ENSEMBLE LOGIC ---
    if model_name == "ensemble":
        model_a_name = "Ateeqq/ai-vs-human-image-detector"
        model_b_name = "umm-maybe/AI-image-detector"
        
        clf_a = get_classifier(model_a_name)
        clf_b = get_classifier(model_b_name)
        
        if clf_a is None or clf_b is None:
             scores['l2_error'] = "Ensemble Model Load Failed"
             return True, "ALLOW", reasons, scores
             
        # Predict A
        results_a = clf_a(img_pil)
        ai_score_a = 0.0
        details_a = []
        for r in results_a:
            label = r['label'].lower()
            details_a.append(f"{label}:{round(r['score'],3)}")
            if "fake" in label or "ai" in label or "artificial" in label:
                ai_score_a = r['score']
                
        # Predict B
        results_b = clf_b(img_pil)
        ai_score_b = 0.0
        details_b = []
        for r in results_b:
            label = r['label'].lower()
            details_b.append(f"{label}:{round(r['score'],3)}")
            if "fake" in label or "ai" in label or "artificial" in label:
                ai_score_b = r['score']
        
        # Ensemble Logic
        abs_diff = abs(ai_score_a - ai_score_b)
        avg_score = (ai_score_a + ai_score_b) / 2
        
        scores['ai_prob'] = float(avg_score)
        scores['human_prob'] = float(1.0 - avg_score)
        scores['ai_prob_a'] = float(ai_score_a)
        scores['ai_prob_b'] = float(ai_score_b)
        scores['ensemble_diff'] = float(abs_diff)
        
        # Helper logs
        # reasons.append(f"DEBUG_A[{model_a_name}]: {details_a}")
        # reasons.append(f"DEBUG_B[{model_b_name}]: {details_b}")
        
        # Disagreement Handling
        if abs_diff > 0.4:
            reasons.append(f"AI_UNCERTAIN (Diff: {round(abs_diff, 2)})")
            return True, "ALLOW", reasons, scores
            
        # Agreement -> Use average
        AI_THRESHOLD = 0.90
        if avg_score > AI_THRESHOLD:
            reasons.append(f"AI_GENERATED_CONTENT_ENSEMBLE ({round(avg_score*100)}%)")
            return False, "HARD_BLOCK", reasons, scores
            
        return True, "ALLOW", reasons, scores
        
    # --- SINGLE MODEL LOGIC (Existing) ---
    # 1. Load Model
    clf = get_classifier(model_name)
    if clf is None:
        scores['l2_error'] = f"Model {model_name} Load Failed"
        return True, "ALLOW", reasons, scores

    try:
        # 2. Predict
        results = clf(img_pil)
        
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
        AI_THRESHOLD = 0.90 
        
        if ai_score > AI_THRESHOLD:
            reasons.append(f"AI_GENERATED_CONTENT ({round(ai_score*100)}%)")
            return False, "HARD_BLOCK", reasons, scores
            
        return True, "ALLOW", reasons, scores

    except Exception as e:
        print(f"Level 2 Runtime Error: {e}")
        scores['l2_error'] = str(e)
        return True, "ALLOW", reasons, scores
