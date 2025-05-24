import webview
from app import app
import threading
import time
from waitress import serve

def get_local_ip():
    """Fetch the local IP address dynamically"""
    return socket.gethostbyname(socket.gethostname())

def run_flask():
    """Start the Flask server with a dynamically assigned IP"""
    local_ip = get_local_ip()
    serve(app, host=local_ip, port=4040)

def main():
    """Main function to start Flask server and WebView"""
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()

    time.sleep(3)  # Allow enough time for the server to start

    local_ip = get_local_ip()
    webview.create_window("Design Record Manager", f"http://{local_ip}:4040", width=1200, height=800)
    webview.start()

if __name__ == '__main__':
    main()
