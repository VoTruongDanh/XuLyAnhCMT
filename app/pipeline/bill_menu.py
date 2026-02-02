import torch
from transformers import CLIPProcessor, CLIPModel
from PIL import Image
import io

from transformers import pipeline

# Global cache
MODEL_NAME = "openai/clip-vit-base-patch32" 
FAKE_MODEL_NAME = "prithivMLmods/Deep-Fake-Detector-v2-Model"

model = None
processor = None
fake_pipeline = None

def get_bill_menu_model():
    global model, processor
    if model is None:
        print(f"Loading Bill/Menu CLIP ({MODEL_NAME})...")
        model = CLIPModel.from_pretrained(MODEL_NAME)
        processor = CLIPProcessor.from_pretrained(MODEL_NAME)
        print("Bill/Menu CLIP Loaded.")
    return model, processor

def get_fake_detector():
    global fake_pipeline
    if fake_pipeline is None:
        print(f"Loading Fake Detector ({FAKE_MODEL_NAME})...")
        try:
            fake_pipeline = pipeline("image-classification", model=FAKE_MODEL_NAME)
            print("Fake Detector Loaded.")
        except Exception as e:
            print(f"Error loading Fake Detector: {e}")
            return None
    return fake_pipeline

def check_bill_menu(img_pil):
    """
    Returns: (label, scores_dict)
    Labels: 'BILL', 'MENU', 'OTHER', 'FAKE_EDITED'
    """
    model, processor = get_bill_menu_model()
    fake_pipe = get_fake_detector()
    
    # 1. Zero-shot prompts
    labels = [
        "a receipt or invoice", 
        "a restaurant menu", 
        "a legal contract or dense text document", 
        "a normal photo"
    ]
    
    inputs = processor(text=labels, images=img_pil, return_tensors="pt", padding=True)
    
    with torch.no_grad():
        outputs = model(**inputs)
        
    # Softmax
    logits_per_image = outputs.logits_per_image
    probs = logits_per_image.softmax(dim=1).squeeze().tolist()
    
    # Map to result
    result_map = {
        0: "BILL/INVOICE",
        1: "MENU",
        2: "OTHER", # Contract -> Other
        3: "OTHER"  # Photo -> Other
    }
    
    scores = {
        "receipt_invoice": probs[0],
        "restaurant_menu": probs[1],
        "contract_document": probs[2],
        "normal_photo": probs[3],
        "fake_probability": 0.0 # Default
    }
    
    # Get max
    max_idx = probs.index(max(probs))
    prediction = result_map[max_idx]
    
    # 2. If Bill/Menu, check for Photoshop/Fake
    if prediction in ["BILL/INVOICE", "MENU"] and fake_pipe:
        print("Checking for manipulation...")
        try:
            fake_results = fake_pipe(img_pil)
            # Result is list of dicts: [{'label': 'Fake', 'score': 0.9}, {'label': 'Real', 'score': 0.1}]
            fake_score = 0.0
            for res in fake_results:
                lbl = res['label'].lower()
                scr = res['score']
                print(f"DEBUG: Label='{lbl}' Score={scr}")
                
                # Check for various "Fake" labels
                if "fake" in lbl or "ai" in lbl or "edit" in lbl or "artificial" in lbl:
                    fake_score = scr
                # If Realism is low, implies Fake? Better to stick to positive fake identification first.
                # If the label is "Realism" and score is low, that helps but usually there's a counterpart.
            
            # Fallback if no specific "fake" label found but we have "realism"
            if fake_score == 0.0:
                 for res in fake_results:
                     if "real" in res['label'].lower():
                         # if Real is 0.4, Fake is 0.6
                         fake_score = 1.0 - res['score']

            scores['fake_probability'] = fake_score
            print(f"Final Fake Score: {fake_score}")
            
            if fake_score > 0.6: # Threshold for Photoshop/Fake
                prediction = "FAKE_EDITED"
                
        except Exception as e:
            print(f"Fake check failed: {e}")

    return prediction, scores
