import os
import threading
import socket
from dotenv import load_dotenv
from pyngrok import ngrok
import uvicorn
import time

# 1. Load the .env file from the local Colab disk
load_dotenv()
NGROK_TOKEN = os.getenv("NGROK_AUTH_TOKEN")

# Helper function to check if port is in use
def is_port_in_use(port):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    result = sock.connect_ex(('0.0.0.0', port))
    sock.close()
    return result == 0

# Kill any existing process on port 8000
if is_port_in_use(8000):
    print("WARNING: Port 8000 is already in use. Attempting to free it...")
    os.system("lsof -ti:8000 | xargs kill -9 2>/dev/null || true")
    time.sleep(1)  # Wait for port to be released

if not NGROK_TOKEN:
    print("ERROR: NGROK_AUTH_TOKEN not found in .env file.")
else:
    # 2. Establish Tunnel
    ngrok.set_auth_token(NGROK_TOKEN)
    # Clear existing tunnels just in case of a previous crash
    ngrok.kill() 
    public_url = ngrok.connect(8000).public_url
    print("="*50)
    print(f"YOUR CLOUD API IS ONLINE AT: {public_url}")
    print("="*50)

    # 3. Boot Server in a Background Thread
    def run_server():
        # Uvicorn creates its own clean event loop in this new thread
        uvicorn.run("identity_service:app", host="0.0.0.0", port=8000)

    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()
    
    print("API is running in the background. Ready to receive frames.")