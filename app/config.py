class Config:
    # --- LEVEL 0 THRESHOLDS ---
    MIN_SHORT_SIDE_PX = 300 # Lowered from 400 to support 360p images
    
    # Blur detection (Variance of Laplacian)
    # < this value => HARD_BLOCK
    BLUR_THRESHOLD = 50.0 # Lowered to 50 to allow softer focus images

    # Solid Color detection (Standard Deviation of pixels)
    # < this value => HARD_BLOCK
    SOLID_COLOR_THRESHOLD = 10.0
    
    # Filename Blocking (Case insensitive partial match)
    # Block if filename contains these strings
    FILENAME_BLOCK_PATTERNS = [
        "screenshot", "screen shot", "chụp màn hình", 
        "zalo_", "facebook_", "messenger_", 
        "untitled", "capture", "screencapture"
    ]

    # Brightness (Mean pixel intensity 0-255)
    DARK_THRESHOLD = 30.0   # Lowered to allow night shots
    BRIGHT_THRESHOLD = 230.0 # Raised to allow beach/sunny shots
    
    # File size
    MIN_FILE_SIZE_KB = 10 # Lowered to 10KB

    # --- LEVEL 3 THRESHOLDS ---
    # Text heavy
    TEXT_SCORE_THRESHOLD = 0.35 # Relaxed from 0.25 back to 0.35
    
    # Document like
    DOC_SCORE_THRESHOLD = 0.6 # Relaxed from 0.5 to 0.6

    # [NEW] Digital/Synthetic (Screenshots, Games, Cartoons)
    # Natural photos usually have noise so pixels are rarely EXACTLY same neighbor.
    # Digital images have many flat areas.
    SYNTHETIC_SCORE_THRESHOLD = 0.7 # Raised to 0.7 to avoid blocking photos with clear sky/walls


    # Paths
    UPLOAD_DIR = "uploads"

    # [NEW] Filename Patterns to Block
    # Common prefixes for screenshots or downloaded files
    BAD_FILENAME_PATTERNS = [
        "screenshot", "screen_shot", "man_hinh", "màn_hình",
        "zalo", "messenger", "image", "download", "untitled",
        "capture", "snap"
    ]

settings = Config()
