import cv2
import requests
import numpy as np
import os
from dotenv import load_dotenv

# 1. Environment Setup
load_dotenv()
base_url = os.getenv("NGROK_URL")

if not base_url:
    print("CRITICAL ERROR: 'NGROK_URL' not found in .env file.")
    exit(1)

ENROLL_URL = base_url + "/enroll/"
LOGIN_URL = base_url + "/login/"

# Security Bypass for Free Ngrok Tier
HEADERS = {"ngrok-skip-browser-warning": "true"}

def capture_frame(prompt_text):
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Error: Could not open webcam.")
        return None

    print(f"\n{prompt_text}")
    print("Press 'Space' to capture, or 'q' to cancel.")

    captured_frame = None
    while True:
        ret, frame = cap.read()
        if not ret:
            break

        cv2.imshow("MFA Terminal", frame)
        key = cv2.waitKey(1)
        
        if key % 256 == 32:  # SPACE bar
            captured_frame = frame
            print("Frame captured.")
            break
        elif key % 256 == 113:  # 'q' key
            print("Capture cancelled.")
            break

    cap.release()
    cv2.destroyAllWindows()
    return captured_frame

def enroll_user():
    print("\n=== SYSTEM ENROLLMENT ===")
    username = input("Enter a new username: ").strip()
    password = input("Enter a secure password: ").strip()
    
    if not username or not password:
        print("Error: Credentials cannot be empty.")
        return

    frame = capture_frame("Look directly at the camera to establish your baseline identity.")
    if frame is None:
        return

    print("Transmitting baseline data to cloud...")
    _, encoded_image = cv2.imencode('.jpg', frame)
    
    payload = {'username': username, 'password': password}
    files = {'file': ('frame.jpg', encoded_image.tobytes(), 'image/jpeg')}
    
    try:
        response = requests.post(ENROLL_URL, data=payload, files=files, headers=HEADERS)
        
        if response.status_code == 200:
            print("\n--- SERVER RESPONSE ---")
            print(response.json())
            print("-----------------------\n")
        else:
            print(f"\n[!] SERVER ERROR (HTTP {response.status_code})")
            print(f"Raw Output: {response.text}\n")
    except Exception as e:
        print(f"Connection Error: {e}")

def login_user():
    print("\n=== SYSTEM LOGIN ===")
    username = input("Username: ").strip()
    password = input("Password: ").strip()
    
    frame = capture_frame("Look at the camera and BLINK to verify liveness.")
    if frame is None:
        return

    print("Authenticating via cloud inference...")
    _, encoded_image = cv2.imencode('.jpg', frame)
    
    payload = {'username': username, 'password': password}
    files = {'file': ('frame.jpg', encoded_image.tobytes(), 'image/jpeg')}
    
    try:
        response = requests.post(LOGIN_URL, data=payload, files=files, headers=HEADERS)
        
        if response.status_code == 200:
            result = response.json()
            print("\n" + "="*40)
            print("--- AUTHENTICATION RESULT ---")
            if result.get("auth_granted"):
                print(f"ACCESS GRANTED. {result.get('message')}")
                print(f"Mathematical Distance: {result.get('distance'):.4f}")
            else:
                print("ACCESS DENIED.")
                print(f"Reason: {result.get('reason')}")
                if "distance" in result:
                    print(f"Mathematical Distance: {result.get('distance'):.4f}")
            print("="*40 + "\n")
        else:
            print(f"\n[!] SERVER ERROR (HTTP {response.status_code})")
            print(f"Raw Output: {response.text}\n")
    except Exception as e:
        print(f"Connection Error: {e}")

def main_menu():
    while True:
        print("\n" + "="*30)
        print(" DISTRIBUTED MFA TERMINAL ")
        print("="*30)
        print("1. Enroll New Identity")
        print("2. Login (Verify Identity)")
        print("3. Exit System")
        print("="*30)
        
        choice = input("Select an operation (1/2/3): ").strip()
        
        if choice == '1':
            enroll_user()
        elif choice == '2':
            login_user()
        elif choice == '3':
            print("Shutting down terminal. Goodbye.")
            break
        else:
            print("Invalid selection. Please enter 1, 2, or 3.")

if __name__ == "__main__":
    main_menu()
