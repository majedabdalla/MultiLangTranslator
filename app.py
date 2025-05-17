import os
import logging
from flask import Flask, render_template

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "multichatbot_secret_key")

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Routes
@app.route('/')
def index():
    """Render the index page for the keep-alive server."""
    return render_template('index.html')

# For gunicorn
app = app

if __name__ == "__main__":
    # Start the Flask server directly (for development)
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))