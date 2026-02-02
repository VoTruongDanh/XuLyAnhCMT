from PIL import Image, ImageChops, ImageEnhance
import os
import io

def perform_ela(img_pil, quality=90, scale=10):
    """
    Generates an Error Level Analysis (ELA) image.
    
    Args:
        img_pil (PIL.Image): Original image.
        quality (int): JPEG quality for resaving (default 90).
        scale (int): Brightness scale factor for difference (default 10).
        
    Returns:
        PIL.Image: The ELA heatmap image.
        dict: Stats like max difference.
    """
    # 1. Save to buffer with specific compression
    buffer = io.BytesIO()
    # ELA works best on RGB
    img_pil = img_pil.convert("RGB")
    img_pil.save(buffer, "JPEG", quality=quality)
    buffer.seek(0)
    
    # 2. Open compressed image
    img_compressed = Image.open(buffer)
    
    # 3. Calculate difference
    diff = ImageChops.difference(img_pil, img_compressed)
    
    # 4. Find max diff (for score/stats)
    extrema = diff.getextrema()
    max_diff = max([ex[1] for ex in extrema])
    
    # 5. Enhance brightness to make it visible
    # We can use Point operation or ImageEnhance
    # Using point scaling is standard for ELA
    ela_img = ImageEnhance.Brightness(diff).enhance(scale)
    
    return ela_img, {"max_diff": max_diff}
