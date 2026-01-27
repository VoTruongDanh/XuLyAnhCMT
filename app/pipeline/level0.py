import cv2
import numpy as np
from app.config import settings

def run_level0_checks(img_cv, width, height, file_size_bytes, filename=""):
    """
    Run Level 0 checks: Validity, Size, Blur, Brightness, Filename.
    Returns: (is_passed, decision, reasons, scores)
    """
    scores = {}
    reasons = []
    
    # 0. Check Decode/Validity (Already handled in caller, but safety check)
    if img_cv is None:
        return False, "HARD_BLOCK", ["IMAGE_DECODE_FAILED"], scores

    # 0.1 Check Filename
    if filename:
        lower_name = filename.lower()
        for pattern in settings.FILENAME_BLOCK_PATTERNS:
            if pattern in lower_name:
                reasons.append(f"FILENAME_BLOCKED_{pattern.upper()}")
                # Allow soft block or hard block? Usually if it says Screenshot it IS a screenshot.
                # Let's start with SOFT_BLOCK mostly, or HARD if strict.
                # User complaint implies they want to block it. 
                # Let's SOFT_BLOCK to be safe, or HARD_BLOCK?
                # "có thể block" -> implies action. Let's return HARD_BLOCK for obvious ones.
                return False, "HARD_BLOCK", reasons, scores

    # 1. Check Resolution
    min_side = min(width, height)
    scores['min_side'] = min_side
    if min_side < settings.MIN_SHORT_SIDE_PX:
        reasons.append("RESOLUTION_TOO_LOW")
        return False, "HARD_BLOCK", reasons, scores

    # 2. Check File Size
    file_size_kb = file_size_bytes / 1024
    scores['file_size_kb'] = file_size_kb
    if file_size_kb < settings.MIN_FILE_SIZE_KB:
        reasons.append("FILE_SIZE_TOO_SMALL")
        # Can be SOFT or HARD based on strictness, user req says SOFT_BLOCK
        return False, "SOFT_BLOCK", reasons, scores

    # 3. Check Solid Color / Low Information
    gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
    std_dev = np.std(gray)
    scores['pixel_std_dev'] = float(std_dev)
    
    if std_dev < settings.SOLID_COLOR_THRESHOLD:
        reasons.append("SOLID_COLOR_IMAGE")
        return False, "HARD_BLOCK", reasons, scores

    # 4. Check Blur (Laplacian Variance)
    blur_score = cv2.Laplacian(gray, cv2.CV_64F).var()
    scores['blur_score'] = float(blur_score)
    
    if blur_score < settings.BLUR_THRESHOLD:
        reasons.append("IMAGE_TOO_BLURRY")
        return False, "HARD_BLOCK", reasons, scores

    # 5. Check Brightness
    # Mean pixel intensity
    brightness = np.mean(gray)
    scores['brightness_mean'] = float(brightness)
    
    if brightness < settings.DARK_THRESHOLD:
        reasons.append("IMAGE_TOO_DARK")
        return False, "SOFT_BLOCK", reasons, scores
        
    if brightness > settings.BRIGHT_THRESHOLD:
        reasons.append("IMAGE_TOO_BRIGHT")
        return False, "SOFT_BLOCK", reasons, scores

    return True, "ALLOW", reasons, scores
