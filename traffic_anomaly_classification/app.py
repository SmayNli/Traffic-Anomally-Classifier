import os
import base64
import requests
import numpy as np
import cv2
import random
import uvicorn
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Optional
from contextlib import asynccontextmanager

from video_generator import generate_all_samples

# Configuration state (in-memory database/cache)
CONFIG = {
    "simulation_mode": True,
    "api_key": os.environ.get("NVIDIA_API_KEY", ""),
    "api_endpoint": "https://integrate.api.nvidia.com/v1/embeddings",
    "thresholds": {
        "accident": 0.40,
        "fight": 0.40,
        "obstacle": 0.40,
        "violation": 0.40
    }
}

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create static/samples directory and generate synthetic videos on startup
    static_dir = os.path.join(os.path.dirname(__file__), "static")
    samples_dir = os.path.join(static_dir, "samples")
    os.makedirs(samples_dir, exist_ok=True)
    
    # Check if samples already exist, if not, generate them
    samples = ["normal.mp4", "accident.mp4", "fight.mp4", "obstacle.mp4", "violation.mp4"]
    exists = all(os.path.exists(os.path.join(samples_dir, s)) for s in samples)
    if not exists:
        try:
            generate_all_samples(samples_dir)
        except Exception as e:
            print(f"Hata: Sentetik videolar olusturulamadi: {e}")
            
    yield

app = FastAPI(title="Trafik Anomalisi Analiz API", lifespan=lifespan)

# Add CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ConfigUpdate(BaseModel):
    simulation_mode: bool
    api_key: Optional[str] = ""
    api_endpoint: Optional[str] = ""
    thresholds: Optional[Dict[str, float]] = None

class JSErrorLog(BaseModel):
    message: str
    source: Optional[str] = None
    lineno: Optional[int] = None
    colno: Optional[int] = None
    error: Optional[str] = None

@app.post("/api/log-error")
def log_js_error(err: JSErrorLog):
    print(f"\n[FRONTEND ERROR] {err.message} at {err.source}:{err.lineno}:{err.colno}")
    if err.error:
        print(f"Stack Trace:\n{err.error}\n")
    return {"status": "ok"}

def extract_8_frames(video_path):
    cap = cv2.VideoCapture(video_path)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    if total_frames <= 0:
        return []
    
    # Uniformly sample 8 frames across the video duration
    indices = np.linspace(0, total_frames - 1, 8, dtype=int)
    
    frames_b64 = []
    current_index = 0
    
    while len(frames_b64) < 8:
        ret, frame = cap.read()
        if not ret:
            break
            
        if current_index in indices:
            # Resize frame to 336x336 to keep the payload size small and standard
            resized = cv2.resize(frame, (336, 336))
            _, buffer = cv2.imencode('.jpg', resized)
            b64_str = base64.b64encode(buffer).decode('utf-8')
            frames_b64.append(b64_str)
            
        current_index += 1
        
    cap.release()
    
    # Pad if we couldn't get exactly 8 frames
    while len(frames_b64) < 8 and len(frames_b64) > 0:
        frames_b64.append(frames_b64[-1])
        
    return frames_b64

def get_cosmos_embedding(payload: dict, headers: dict) -> List[float]:
    """Helper function to make requests to the Cosmos Embed API"""
    try:
        response = requests.post(CONFIG["api_endpoint"], json=payload, headers=headers, timeout=30)
        if response.status_code != 200:
            raise HTTPException(
                status_code=response.status_code, 
                detail=f"Nvidia API Hatası: {response.text}"
            )
        data = response.json()
        # Parse standard embeddings structure
        return data["data"][0]["embedding"]
    except requests.exceptions.RequestException as e:
        raise HTTPException(
            status_code=500,
            detail=f"Nvidia API'sine bağlanırken bağlantı hatası oluştu: {str(e)}"
        )

def cosine_similarity(v1, v2):
    v1 = np.array(v1)
    v2 = np.array(v2)
    return float(np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2)))

@app.get("/")
def read_root():
    return FileResponse("static/index.html")

@app.get("/api/config")
def get_config():
    # Hide the API key partially for security
    api_key_display = ""
    if CONFIG["api_key"]:
        api_key_display = CONFIG["api_key"][:6] + "..." + CONFIG["api_key"][-4:] if len(CONFIG["api_key"]) > 10 else "***"
        
    return {
        "simulation_mode": CONFIG["simulation_mode"],
        "api_endpoint": CONFIG["api_endpoint"],
        "has_api_key": bool(CONFIG["api_key"]),
        "api_key_masked": api_key_display,
        "thresholds": CONFIG["thresholds"]
    }

@app.post("/api/config")
def update_config(data: ConfigUpdate):
    CONFIG["simulation_mode"] = data.simulation_mode
    if data.api_key is not None:
        # Keep old key if user sent empty string for masked field
        if data.api_key.strip() != "" and not data.api_key.startswith("******"):
            CONFIG["api_key"] = data.api_key.strip()
    if data.api_endpoint:
        CONFIG["api_endpoint"] = data.api_endpoint.strip()
    if data.thresholds:
        CONFIG["thresholds"].update(data.thresholds)
    return {"status": "success", "message": "Konfigürasyon güncellendi"}

@app.post("/api/generate-samples")
def regenerate_samples():
    static_dir = os.path.join(os.path.dirname(__file__), "static")
    samples_dir = os.path.join(static_dir, "samples")
    try:
        generate_all_samples(samples_dir)
        return {"status": "success", "message": "Sentetik videolar başarıyla yeniden üretildi"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Sentetik videolar üretilemedi: {str(e)}")

@app.post("/api/analyze")
async def analyze_video(
    video_file: Optional[UploadFile] = File(None),
    sample_name: Optional[str] = Form(None),
    labels: str = Form(...)  # Comma separated list of labels
):
    label_list = [l.strip() for l in labels.split(",") if l.strip()]
    if not label_list:
        raise HTTPException(status_code=400, detail="Etiket listesi boş olamaz.")
        
    # Save the file temporarily
    temp_path = "temp_video.mp4"
    is_sample = False
    
    if sample_name:
        static_dir = os.path.join(os.path.dirname(__file__), "static")
        temp_path = os.path.join(static_dir, "samples", sample_name)
        if not os.path.exists(temp_path):
            raise HTTPException(status_code=404, detail=f"Örnek video bulunamadı: {sample_name}")
        is_sample = True
    elif video_file:
        try:
            with open(temp_path, "wb") as buffer:
                buffer.write(await video_file.read())
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Yüklenen dosya kaydedilemedi: {str(e)}")
    else:
        raise HTTPException(status_code=400, detail="Bir video dosyası yükleyin veya örnek video seçin.")

    # 1. SIMULATION MODE
    if CONFIG["simulation_mode"]:
        # Simulate similarity scores based on file type or content
        scores = {}
        
        # Determine the scenario type
        scenario = "normal"
        filename = (sample_name or video_file.filename).lower()
        
        if "accident" in filename or "kaza" in filename or "crash" in filename or "carpism" in filename:
            scenario = "accident"
        elif "fight" in filename or "kavga" in filename or "altercation" in filename or "mudahale" in filename:
            scenario = "fight"
        elif "obstacle" in filename or "engel" in filename or "duran" in filename or "bariyer" in filename:
            scenario = "obstacle"
        elif "violation" in filename or "ihlal" in filename or "kirmizi" in filename or "isik" in filename or "serit" in filename or "lane" in filename or "hatali" in filename:
            scenario = "violation"
            
        # Base values for simulation to create a realistic demonstration
        for label in label_list:
            lbl_lower = label.lower()
            base_val = 0.15 # Default low similarity
            
            if scenario == "accident":
                if "kaza" in lbl_lower or "accident" in lbl_lower or "çarpışma" in lbl_lower:
                    base_val = 0.83
                elif "engel" in lbl_lower or "obstacle" in lbl_lower:
                    base_val = 0.45 # Accidents block roads
            elif scenario == "fight":
                if "kavga" in lbl_lower or "fight" in lbl_lower or "fiziksel" in lbl_lower:
                    base_val = 0.81
            elif scenario == "obstacle":
                if "engel" in lbl_lower or "obstacle" in lbl_lower or "duran" in lbl_lower:
                    base_val = 0.78
                elif "normal" in lbl_lower:
                    base_val = 0.35
            elif scenario == "violation":
                if "ihlal" in lbl_lower or "violation" in lbl_lower or "kural" in lbl_lower or "kırmızı" in lbl_lower or "şerit" in lbl_lower or "lane" in lbl_lower or "hatalı" in lbl_lower:
                    base_val = 0.82
            else: # Normal
                if "normal" in lbl_lower or "akış" in lbl_lower:
                    base_val = 0.85
                    
            scores[label] = base_val + random.uniform(-0.03, 0.03)
            
        # Clean up temporary uploaded file
        if not is_sample and os.path.exists(temp_path):
            os.remove(temp_path)
            
        return {
            "mode": "simulation",
            "scores": scores,
            "detected": max(scores, key=scores.get),
            "max_score": max(scores.values())
        }
        
    # 2. LIVE API MODE (NVIDIA Cosmos Embed1)
    else:
        if not CONFIG["api_key"] and "integrate.api.nvidia.com" in CONFIG["api_endpoint"]:
            if not is_sample and os.path.exists(temp_path):
                os.remove(temp_path)
            raise HTTPException(status_code=400, detail="Bulut API'si için geçerli bir NVIDIA API anahtarı gereklidir.")
            
        # Extract 8 frames from the video
        try:
            frames_b64 = extract_8_frames(temp_path)
            if not frames_b64:
                raise ValueError("Videodan kareler çıkartılamadı.")
        except Exception as e:
            if not is_sample and os.path.exists(temp_path):
                os.remove(temp_path)
            raise HTTPException(status_code=500, detail=f"Video işleme hatası: {str(e)}")
            
        # Format the frames in the special input format:
        # data:video_frames/jpg;base64,{frame0,frame1,...,frame7}
        frames_joined = ",".join(frames_b64)
        video_input_str = f"data:video_frames/jpg;base64,{{{frames_joined}}}"
        
        # Prepare headers
        headers = {
            "Content-Type": "application/json"
        }
        if CONFIG["api_key"]:
            headers["Authorization"] = f"Bearer {CONFIG['api_key']}"
            
        try:
            # Step A: Get video embedding
            video_payload = {
                "input": [video_input_str],
                "model": "nvidia/cosmos-embed1",
                "request_type": "query",
                "encoding_format": "float"
            }
            video_embedding = get_cosmos_embedding(video_payload, headers)
            
            # Step B: Get text embeddings for all labels
            text_embeddings = []
            for label in label_list:
                text_payload = {
                    "input": [label],
                    "model": "nvidia/cosmos-embed1",
                    "request_type": "query",
                    "encoding_format": "float"
                }
                text_emb = get_cosmos_embedding(text_payload, headers)
                text_embeddings.append(text_emb)
                
            # Step C: Compute Cosine Similarity
            scores = {}
            for label, text_emb in zip(label_list, text_embeddings):
                sim = cosine_similarity(video_embedding, text_emb)
                scores[label] = sim
                
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Nvidia Cosmos API Hatası: {str(e)}")
        finally:
            # Clean up temporary uploaded file
            if not is_sample and os.path.exists(temp_path):
                os.remove(temp_path)
                
        return {
            "mode": "live",
            "scores": scores,
            "detected": max(scores, key=scores.get),
            "max_score": max(scores.values())
        }

# Mount static folder
static_dir = os.path.join(os.path.dirname(__file__), "static")
os.makedirs(static_dir, exist_ok=True)
app.mount("/static", StaticFiles(directory=static_dir), name="static")

if __name__ == "__main__":
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)
