import logging
from flask import Flask, render_template
import threading
import config

# Initialize Flask app
app = Flask(__name__)
app.secret_key = config.SESSION_SECRET

# Initialize logger
logger = logging.getLogger(__name__)

@app.route('/')
def index():
    """Render the index page for the keep-alive server."""
    return render_template('index.html')

def run_flask():
    """Run the Flask server."""
    try:
        app.run(host='0.0.0.0', port=config.PORT)
    except Exception as e:
        logger.error(f"Error running Flask server: {e}")

def start_server():
    """Start the Flask server in a separate thread."""
    server_thread = threading.Thread(target=run_flask)
    server_thread.daemon = True
    server_thread.start()
    logger.info(f"Keep-alive server started on port {config.PORT}")

if __name__ == "__main__":
    start_server()
