import os
from flask import Flask, render_template
from flask_cors import CORS
from dotenv import load_dotenv

# Load blueprints
from routes.chat import chat_bp
from routes.legal import legal_bp
from routes.memory import memory_bp

load_dotenv()

app = Flask(__name__)
CORS(app) # Enable CORS for all routes

# App configuration
app.secret_key = os.getenv("APP_PASSWORD", "supersecret")

# Register Blueprints
app.register_blueprint(chat_bp, url_prefix='/api')
app.register_blueprint(legal_bp, url_prefix='/api')
app.register_blueprint(memory_bp, url_prefix='/api')

@app.route("/")
def index():
    """Main entry point - Frontend logic handles login/dashboard visibility."""
    return render_template("index.html")

if __name__ == "__main__":
    # Ensure static and templates directories exist (though they should already)
    os.makedirs("static", exist_ok=True)
    os.makedirs("templates", exist_ok=True)
    
    print("Memory AI Backend Started!")
    print("Frontend available at: http://localhost:5000")
    app.run(debug=True, port=5000)
