import cv2
import numpy as np
try:
    import pytesseract
except ImportError:
    pytesseract = None

from app.config import settings
from app.pipeline.common import detect_faces, check_camera_exif, calculate_entropy

def run_level1_checks(img_cv, img_pil, filename="", file_format="", config_override=None):
    """
    Run Level 1 checks: Text-heavy, Document-like, Synthetic, and [NEW] Web/Download indicators.
    Returns: (is_passed, decision, reasons, scores)
    """
    scores = {}
    reasons = []
    if config_override is None:
        config_override = {}
        
    # Extract overrides
    base_synthetic_thresh = config_override.get('synthetic_thresh', settings.SYNTHETIC_SCORE_THRESHOLD)
    base_entropy_thresh = config_override.get('entropy_thresh', 7.0) # Default for Physical Realism check

    # --- POSITIVE SIGNALS (TRUST INDICATORS) ---
    n_faces = detect_faces(img_cv)
    has_exif = check_camera_exif(img_pil)
    entropy = calculate_entropy(img_cv)
    
    scores['n_faces'] = n_faces
    scores['has_exif'] = has_exif
    scores['entropy'] = float(entropy)
    
    is_trusted_photo = False
    if n_faces > 0:
        is_trusted_photo = True # Face detected = likely real
    if has_exif:
        is_trusted_photo = True # Camera metadata = likely real

    # --- 0. Filename & Metadata Checks (New) ---
    is_suspicious_meta = False
    meta_reasons = []

    # Check Filename
    filename_lower = filename.lower()
    for pattern in settings.BAD_FILENAME_PATTERNS:
        if pattern in filename_lower:
            meta_reasons.append("SUSPICIOUS_FILENAME")
            is_suspicious_meta = True
            break
            
    # Check Aspect Ratio (Square)
    h, w = img_cv.shape[:2]
    ratio = w / h
    is_square = 0.99 < ratio < 1.01
    scores['is_square'] = is_square
    
    if is_square:
        meta_reasons.append("WEB_DOWNLOADED_OR_ART") # Soft indicator
        # Don't mark is_suspicious_meta just for square, unless combined with other things?
        # Actually square is very common for art. Let's count it as weak suspicion.
    
    # Check Format (PNG)
    is_png = "png" in file_format.lower()
    if is_png:
        scores['is_sus_png'] = True

    # --- PHYSICAL REALISM CHECK (New Fallback) ---
    # Sometimes Face Detection fails (back turned, hats) and Exif is missing.
    # We check physical properties: High Entropy (Chaos) + Low Flatness (Noise/Texture).
    
    # Calculate flatness early for this check
    gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
    diff_x = np.abs(gray[:, 1:].astype(int) - gray[:, :-1].astype(int))
    diff_y = np.abs(gray[1:, :].astype(int) - gray[:-1, :].astype(int))
    flat_pixels_x = np.count_nonzero(diff_x < 2)
    flat_pixels_y = np.count_nonzero(diff_y < 2)
    total_pixels_x = diff_x.size
    total_pixels_y = diff_y.size
    flatness_score = (flat_pixels_x + flat_pixels_y) / (total_pixels_x + total_pixels_y)
    scores['synthetic_flatness'] = float(flatness_score)

    # Criteria for "Likely Real Photo" purely from pixel stats
    # Real photos: Entropy > 7.0, Flatness < 0.3 (lots of noise/texture)
    # The Boat photo had Entropy 7.66, Flatness 0.28.
    # Landscape photo (Woman with camera): Entropy 7.27, Flatness 0.54.
    is_physically_real = False
    
    # Relaxed Physical Realism for Landscapes (entropy is key)
    # Use base_entropy_thresh (User configured) as the anchor.
    # If user sets 7.0, we use 7.0. If they set 8.0, we use 8.0.
    
    if entropy > (base_entropy_thresh + 0.15): # e.g. > 7.15
        # If huge entropy, we allow more flatness (e.g. sky)
        if flatness_score < 0.6: 
            is_physically_real = True
    elif entropy > base_entropy_thresh and flatness_score < 0.3:
        # Standard check
        is_physically_real = True
        
    # --- DYNAMIC THRESHOLD & TRUST LOGIC ---
    synthetic_thresh = base_synthetic_thresh # Start with user config

    if is_trusted_photo or is_physically_real:
        scores['trust_mode'] = "HIGH"
        # HIGH TRUST: Faces, Exif, OR Strong Realism stats.
        
        # EXCEPTION: MEME/COLLAGE/DIGITAL ART DETECTION
        is_meme_suspect = False
        
        # Case 1: Very High Flatness (> 0.6) + PNG
        # Digital Art / Anime often has large perfect flat areas. 
        # Real photos (even sky) rarely exceed 0.6 due to noise, unless overexposed.
        if is_png and flatness_score > 0.6:
            is_meme_suspect = True
            
        # Case 2: Moderate Flatness (0.5 - 0.6) + PNG
        # Check Entropy to distinguish Real Landscape (High Entropy) vs Meme (Low Entropy)
        elif is_png and flatness_score > 0.5:
            if not is_physically_real and entropy < base_entropy_thresh:
                is_meme_suspect = True

        if is_meme_suspect:
            # Downgrade trust for Memes/Digital Art
            # If it's Very High Flatness (> 0.6), we need a threshold below 0.6 to catch it.
            # Set to 0.55.
            synthetic_thresh = 0.55 
        else:
            synthetic_thresh = 0.85
            # IGNORE metadata suspicions (bad filename is ok for real photos)
            meta_reasons = [] 
            
        # Strict Entropy Check for "Trusted" Renders
        if (is_png or is_square) and entropy < 6.35:
             reasons.append("SYNTHETIC_DIGITAL_ART_OR_GAME")
             
    elif is_suspicious_meta or is_png or is_square:
        # Check if Entropy "saves" it from being Low Trust
        # If Entropy is decent (> 7.0), don't go into Strict Mode (0.35).
        # Art/Game usually < 7.0.
        if entropy > 7.0:
            scores['trust_mode'] = "NEUTRAL (SAVED)"
            synthetic_thresh = 0.6 # Moderate threshold
        else:
            scores['trust_mode'] = "LOW"
            # LOW TRUST / SUSPICIOUS
            synthetic_thresh = 0.35
            
    else:
        scores['trust_mode'] = "NEUTRAL"
        # NEUTRAL: Use default 0.7
        pass

    # --- 2.1 Low Detail / Collage Check (Independent) ---
    # Move edge density calcluation up here
    gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY) # Already done above? Yes line 67.
    edges = cv2.Canny(gray, 100, 200)
    edge_density = np.count_nonzero(edges) / (edges.shape[0] * edges.shape[1])
    scores['edge_density'] = float(edge_density)

    if is_png and not has_exif:
        # Threshold 0.1 was too high for some landscapes (0.11).
        # Reduced to 0.05 to only catch extremely empty images.
        # [UPDATE] If Entropy is High (> 7.0), it means rich colors (real photo/bokeh).
        # We only block if BOTH Edges are low AND Entropy is low (flat colors).
        if edge_density < 0.05 and entropy < 7.0:
            reasons.append("LOW_DETAIL_OR_EDITED")

    # --- 1. Text Detection ---
    text_score = 0.0
    ocr_available = False
    
    # gray calc already done
    # edges calc already done above
    
    if pytesseract:
        try:
            data = pytesseract.image_to_data(img_pil, output_type=pytesseract.Output.DICT)
            n_words = len([x for x in data['text'] if x.strip() != ''])
            scores['ocr_word_count'] = n_words
            text_score = min(1.0, n_words / 100.0) 
            ocr_available = True
        except Exception:
            pass # Fallback

    if not ocr_available:
        scores['ocr_status'] = "NOT_INSTALLED"
        text_score = min(1.0, edge_density * 1.5) 

    scores['text_score'] = float(text_score)

    if text_score > settings.TEXT_SCORE_THRESHOLD:
        tolerance = settings.TEXT_SCORE_THRESHOLD * 1.5 if is_trusted_photo else settings.TEXT_SCORE_THRESHOLD
        if text_score > tolerance:
            reasons.append("TEXT_HEAVY_SCREENSHOT_LIKE")
    
    # --- 2. Synthetic/Digital Detection ---
    # Flatness calculated early above
    scores['synthetic_threshold_used'] = float(synthetic_thresh)

    if flatness_score > synthetic_thresh:
        # Check entropy compatibility
        # If strict threshold (0.35) used, we should also check entropy to avoid blocking semi-flat real photos
        if synthetic_thresh < 0.5:
             # Strict mode
             if entropy < 7.5: # Wolf was 7.4. Bridge was 7.8. 
                 reasons.append("SYNTHETIC_DIGITAL_ART_OR_GAME")
        else:
             # Normal/Lenient mode
             if entropy < 6.2:
                 reasons.append("SYNTHETIC_DIGITAL_ART_OR_GAME")

    # Add metadata reasons if any (and if not cleared by trust)
    reasons.extend(meta_reasons)

    # --- 3. Document-like Detection ---
    ret, thresh = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY)
    white_pixel_ratio = np.count_nonzero(thresh) / (gray.shape[0] * gray.shape[1])
    scores['white_ratio'] = float(white_pixel_ratio)
    
    doc_score = (white_pixel_ratio * 0.7) + (text_score * 0.3)
    scores['doc_score'] = float(doc_score)
    
    if doc_score > settings.DOC_SCORE_THRESHOLD:
        reasons.append("DOCUMENT_LIKE")

    # Final Decision Aggregation
    if "DOCUMENT_LIKE" in reasons:
        decision = "HARD_BLOCK"
        return False, decision, reasons, scores
        
    soft_block_reasons = [
        "TEXT_HEAVY_SCREENSHOT_LIKE", 
        "SYNTHETIC_DIGITAL_ART_OR_GAME",
        "SUSPICIOUS_FILENAME",
        "WEB_DOWNLOADED_OR_ART",
        "LOW_DETAIL_OR_EDITED"
    ]
    
    if any(r in reasons for r in soft_block_reasons):
        decision = "SOFT_BLOCK"
        return False, decision, reasons, scores

    return True, "ALLOW", reasons, scores
