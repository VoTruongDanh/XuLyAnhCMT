import os
import time
import uuid
import logging
from typing import List
import numpy as np

from fastapi import FastAPI, File, UploadFile, HTTPException, Form
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.pipeline.common import load_image_from_bytes, resize_for_processing
from app.pipeline.level0 import run_level0_checks
from app.pipeline.level1 import run_level1_checks
from app.pipeline.level2 import run_level2_checks
from app.pipeline.level3 import run_level3_checks

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def sanitize_start_recursive(obj):
    if isinstance(obj, dict):
        return {k: sanitize_start_recursive(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [sanitize_start_recursive(i) for i in obj]
    if isinstance(obj, (np.intc, np.intp, np.int8,
        np.int16, np.int32, np.int64, np.uint8,
        np.uint16, np.uint32, np.uint64)):
        return int(obj)
    if isinstance(obj, (np.float16, np.float32, np.float64)):
        return float(obj)
    if isinstance(obj, (np.ndarray,)): 
        return sanitize_start_recursive(obj.tolist())
    if isinstance(obj, (np.bool_)):
        return bool(obj)
    return obj

app = FastAPI(title="Irrelevant Image Checker")

# CORS (allow all for demo)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ensure upload directory exists
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)

# Mount UI for static serving (if needed, but user asked for 'ui/' folder separate or served)
# We will serve the 'ui' folder at /ui
if os.path.exists("ui"):
    app.mount("/ui", StaticFiles(directory="ui", html=True), name="ui")

@app.get("/healthz")
def health_check():
    return {"ok": True}

@app.post("/api/check-image")
async def check_image(
    file: UploadFile = File(...),
    custom_synthetic_thresh: float = Form(None),
    custom_entropy_thresh: float = Form(None),
    custom_ai_model: str = Form(None)
):
    start_time = time.time()
    
    # Pack overrides
    config_override = {}
    if custom_synthetic_thresh is not None:
        config_override['synthetic_thresh'] = custom_synthetic_thresh
    if custom_entropy_thresh is not None:
        config_override['entropy_thresh'] = custom_entropy_thresh
    if custom_ai_model is not None and custom_ai_model.strip() != "":
        config_override['ai_model'] = custom_ai_model.strip()
    
    # 1. Read file
    try:
        contents = await file.read()
        filesize = len(contents)
    except Exception as e:
        return JSONResponse(status_code=400, content={"error": "Failed to read file"})

    # 2. Save file (Requirement: uploads/timestamp+uuid)
    file_ext = file.filename.split(".")[-1] if "." in file.filename else "jpg"
    filename = f"{int(time.time())}_{uuid.uuid4()}.{file_ext}"
    filepath = os.path.join(settings.UPLOAD_DIR, filename)
    
    with open(filepath, "wb") as f:
        f.write(contents)
    
    # 3. Load Image
    img_cv, img_pil, width, height = load_image_from_bytes(contents)
    
    meta = {
        "width": width,
        "height": height,
        "format": file.content_type,
        "filesize": filesize
    }
    
    # Invalid image
    if img_cv is None:
        return {
            "allowed": False,
            "decision": "HARD_BLOCK",
            "reasons": ["INVALID_IMAGE_FORMAT"],
            "scores": {},
            "meta": meta
        }

    # Optimization: Resize for heavy processing if needed (not strictly used for quality check, 
    # but good for performance on heavy heuristics if we had Level 2)
    # img_small = resize_for_processing(img_cv)

    # --- PIPELINE START ---
    
    try:
        # 1. Level 0 Checks (Basic)
        l0_passed, l0_decision, l0_reasons, l0_scores = run_level0_checks(img_cv, width, height, filesize, filename=file.filename)
        
        all_scores = {**l0_scores}
        all_reasons = l0_reasons[:]
        final_decision = l0_decision
        
        if final_decision == "HARD_BLOCK":
            return sanitize_start_recursive({
                "allowed": False,
                "decision": "HARD_BLOCK",
                "reasons": all_reasons,
                "scores": all_scores,
                "meta": meta
            })

        # 2. Level 1 Checks (Style/Illustration Detection)
        l1_passed, l1_decision, l1_reasons, l1_scores = run_level1_checks(
            img_cv, img_pil, filename=file.filename,
            config_override=config_override
        )
        all_scores.update(l1_scores)
        all_reasons.extend(l1_reasons)
        
        if l1_decision == "HARD_BLOCK":
             return sanitize_start_recursive({
                "allowed": False,
                "decision": "HARD_BLOCK",
                "reasons": all_reasons,
                "scores": all_scores,
                "meta": meta
            })

        # 3. Level 2 Checks (AI Detection)
        l2_passed, l2_decision, l2_reasons, l2_scores = run_level2_checks(
            img_cv, img_pil, filename=file.filename,
            config_override=config_override
        )
        all_scores.update(l2_scores)
        all_reasons.extend(l2_reasons)
        
        if l2_decision == "HARD_BLOCK":
             return sanitize_start_recursive({
                "allowed": False,
                "decision": "HARD_BLOCK",
                "reasons": all_reasons,
                "scores": all_scores,
                "meta": meta
            })

        # 4. Level 3 Checks (Metadata/Heuristics/Trust)
        l3_passed, l3_decision, l3_reasons, l3_scores = run_level3_checks(
            img_cv, 
            img_pil, 
            filename=file.filename or "", 
            file_format=file.content_type or "",
            config_override=config_override
        )
        
        all_scores.update(l3_scores)
        all_reasons.extend(l3_reasons)
        
        # Logic aggregation
        if l3_decision == "HARD_BLOCK":
            final_decision = "HARD_BLOCK"
        elif l3_decision == "SOFT_BLOCK" and final_decision == "ALLOW":
            final_decision = "SOFT_BLOCK"
        
        is_allowed = (final_decision == "ALLOW")
        
        # Compute elapsed time
        elapsed_ms = (time.time() - start_time) * 1000
        meta['elapsed_ms'] = round(elapsed_ms, 2)
        
        return sanitize_start_recursive({
            "allowed": is_allowed,
            "decision": final_decision,
            "reasons": all_reasons,
            "scores": all_scores,
            "meta": meta
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"error": str(e), "trace": traceback.format_exc()})

@app.get("/")
def root():
    # Redirect to UI if accessed directly
    if os.path.exists("ui/index.html"):
        return FileResponse("ui/index.html")
    return {"message": "Image Checker API. Go to /ui to test."}
