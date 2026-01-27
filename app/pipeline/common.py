import cv2
import numpy as np
from PIL import Image
import io

def load_image_from_bytes(file_bytes: bytes):
    """
    Load image from bytes into OpenCV format (BGR) and PIL format.
    Returns: (image_cv, image_pil, width, height)
    """
    try:
        # Convert to numpy array
        nparr = np.frombuffer(file_bytes, np.uint8)
        # Decode image using OpenCV
        img_cv = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if img_cv is None:
            return None, None, 0, 0
            
        # Create PIL Image properly to keep EXIF
        # We read from bytes again for PIL
        img_pil = Image.open(io.BytesIO(file_bytes))
        # Ensure it's loaded to prevent issues later
        img_pil.load() 
        
        h, w = img_cv.shape[:2]
        return img_cv, img_pil, w, h
    except Exception as e:
        print(f"Error loading image: {e}")
        return None, None, 0, 0

def resize_for_processing(img_cv, max_dim=1024):
    """
    Resize image if it's too large for faster processing.
    """
    h, w = img_cv.shape[:2]
    if max(h, w) > max_dim:
        scale = max_dim / max(h, w)
        new_w = int(w * scale)
        new_h = int(h * scale)
        return cv2.resize(img_cv, (new_w, new_h), interpolation=cv2.INTER_AREA)
    return img_cv

# --- NEW UTILITIES ---

def detect_faces(img_cv):
    """
    Detect faces using OpenCV Haar Cascade.
    Returns number of faces found.
    """
    try:
        # Load pre-trained face detector from OpenCV data
        cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        face_cascade = cv2.CascadeClassifier(cascade_path)
        
        gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(
            gray, 
            scaleFactor=1.1, 
            minNeighbors=5, 
            minSize=(30, 30)
        )
        return len(faces)
    except Exception as e:
        # print(f"Face detection error: {e}") 
        return 0

def check_camera_exif(img_pil):
    """
    Check if image has Camera Exif data (Make, Model).
    Returns True if camera data found.
    """
    try:
        exif = img_pil._getexif()
        if not exif:
            return False
        
        # Look for Make (271) or Model (272) tags
        # 306 is DateTime
        has_make = 271 in exif
        has_model = 272 in exif
        return has_make or has_model
    except Exception:
        return False

def calculate_entropy(img_cv):
    """
    Calculate Shannon Entropy of image.
    High entropy > 7.0: Real photo (complex texture).
    Low entropy < 5.0: Synthetic/Cartoon/Flat.
    """
    try:
        gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
        hist = cv2.calcHist([gray], [0], None, [256], [0, 256])
        hist = hist.ravel() / hist.sum()
        logs = np.log2(hist + 0.00001)
        entropy = -1 * (hist * logs).sum()
        return float(entropy)
    except Exception:
        return 0.0
