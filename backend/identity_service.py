from fastapi import FastAPI, File, UploadFile, Form
import cv2
import dlib
import numpy as np
from keras_facenet import FaceNet
from scipy.spatial import distance
import json
import os
import traceback # Added for detailed error reporting

app = FastAPI()
DB_FILE = "user_database.json"
LANDMARK_PATH = "shape_predictor_68_face_landmarks.dat"

print("Loading AI Models on T4 GPU...")
try:
    embedder = FaceNet()
    if not os.path.exists(LANDMARK_PATH):
        raise FileNotFoundError(f"Missing file: {LANDMARK_PATH}")
    detector = dlib.get_frontal_face_detector()
    predictor = dlib.shape_predictor(LANDMARK_PATH)
    print("Models Loaded Successfully.")
except Exception as e:
    print(f"CRITICAL ERROR loading models: {e}")

# --- Database Logic ---
def load_db():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r") as f:
            return json.load(f)
    return {}

def save_db(db_data):
    with open(DB_FILE, "w") as f:
        json.dump(db_data, f)

# --- Core AI Logic ---
def calculate_ear(eye):
    A = distance.euclidean(eye[1], eye[5])
    B = distance.euclidean(eye[2], eye[4])
    C = distance.euclidean(eye[0], eye[3])
    return (A + B) / (2.0 * C)

def extract_features(frame):
    try:
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = detector(gray)
        is_live = False
        
        if len(faces) == 0:
            print("DEBUG: No face detected in frame.")
            return False, None
            
        face = faces[0]
        landmarks = predictor(gray, face)
        left_eye = np.array([(landmarks.part(i).x, landmarks.part(i).y) for i in range(36, 42)])
        right_eye = np.array([(landmarks.part(i).x, landmarks.part(i).y) for i in range(42, 48)])
        
        ear_value = (calculate_ear(left_eye) + calculate_ear(right_eye)) / 2.0
        if ear_value < 0.25:
            is_live = True

        face_resized = cv2.resize(frame, (160, 160))
        # Ensure correct input shape for FaceNet
        embedding = embedder.embeddings([face_resized])[0]
        return is_live, embedding.tolist()
        
    except Exception as e:
        print(f"DEBUG: Error in extract_features: {e}")
        print(traceback.format_exc()) # Prints the full error trace to Colab logs
        return False, None

# --- MFA Endpoints ---
@app.post("/enroll/")
async def enroll_user(username: str = Form(...), password: str = Form(...), file: UploadFile = File(...)):
    contents = await file.read()
    nparr = np.frombuffer(contents, np.uint8)
    frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    
    is_live, embedding = extract_features(frame)
    if embedding is None:
        return {"status": "failed", "reason": "Could not extract facial features."}
    
    db = load_db()
    db[username] = {"password": password, "embedding": embedding}
    save_db(db)
    return {"status": "success", "message": f"User '{username}' successfully enrolled."}

@app.post("/login/")
async def login_user(username: str = Form(...), password: str = Form(...), file: UploadFile = File(...)):
    db = load_db()
    if username not in db: return {"status": "failed", "reason": "User not found."}
    if db[username]["password"] != password: return {"status": "failed", "reason": "Invalid password."}
        
    contents = await file.read()
    nparr = np.frombuffer(contents, np.uint8)
    frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    
    is_live, live_embedding = extract_features(frame)
    if live_embedding is None:
        return {"status": "failed", "reason": "Could not extract facial features."}
    
    stored_embedding = np.array(db[username]["embedding"])
    cos_dist = distance.cosine(stored_embedding, np.array(live_embedding))
    
    if cos_dist > 0.40:
        return {"status": "failed", "reason": "Face mismatch.", "distance": cos_dist}
    if not is_live:
        return {"status": "failed", "reason": "Liveness check failed.", "distance": cos_dist}
        
    return {"status": "success", "auth_granted": True, "distance": cos_dist}
