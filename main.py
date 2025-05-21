import webview
from app import app
import threading
import time
from waitress import serve

def run_flask():
    serve(app, host='0.0.0.0', port=4040)  # Serve on port 4040

if __name__ == '__main__':
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()

    time.sleep(1)  # Wait for server to start

    webview.create_window("Design Record Manager", "http://192.168.0.89:4040", width=1200, height=800)
    webview.start()
