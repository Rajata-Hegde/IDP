"""
Flask API server for crowd monitoring
"""
from flask import Flask, jsonify, request
from flask_cors import CORS
import base64
import cv2
import io
import os
import platform
from functools import lru_cache
from main import initialize_monitoring
from pathlib import Path
from werkzeug.utils import secure_filename
from event_analysis import analyze_event_video

app = Flask(__name__)
CORS(app)

# Configuration
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'mp4', 'avi', 'mov', 'mkv', 'flv', 'wmv', 'webm'}
ALLOWED_IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp', 'bmp', 'gif'}
MAX_FILE_SIZE = 500 * 1024 * 1024  # 500MB

# Create upload folder if it doesn't exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_FILE_SIZE

# Initialize monitoring system
monitoring_system = None
last_alert_logged = False

def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def allowed_image_file(filename):
    """Check if image file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_IMAGE_EXTENSIONS


def get_system_location():
    """Return a human-readable local system location label."""
    configured_location = os.getenv('SYSTEM_LOCATION')
    if configured_location:
        return configured_location

    hostname = platform.node() or 'unknown-host'
    return f"{hostname} (local monitoring workstation)"


@lru_cache(maxsize=1)
def get_blip_captioner(model_name="Salesforce/blip-image-captioning-large"):
    """Load and cache the BLIP captioning model."""
    import torch
    from transformers import BlipForConditionalGeneration, BlipProcessor

    device = "cuda" if torch.cuda.is_available() else "cpu"
    processor = BlipProcessor.from_pretrained(model_name)
    model = BlipForConditionalGeneration.from_pretrained(model_name).to(device)
    model.eval()

    return processor, model, device


def build_caption(image, model_name="Salesforce/blip-image-captioning-large"):
    """Generate a BLIP caption for an image."""
    import torch

    processor, model, device = get_blip_captioner(model_name)

    inputs = processor(image, text="a photo of", return_tensors="pt").to(device)

    with torch.no_grad():
        output = model.generate(
            **inputs,
            max_new_tokens=30,
            min_length=10,
            num_beams=5,
            no_repeat_ngram_size=2,
            length_penalty=1.0,
            early_stopping=True,
        )

    caption = processor.decode(output[0], skip_special_tokens=True)
    caption = " ".join(caption.split())

    if caption:
        caption = caption[0].upper() + caption[1:]
        if caption[-1] not in ".!?":
            caption += "."

    return caption


def start_monitoring(video_source=0):
    """Start the monitoring system"""
    global monitoring_system
    
    # Stop existing monitoring if any
    if monitoring_system is not None:
        monitoring_system.stop()
        import time
        time.sleep(1)  # Wait for threads to clean up
    
    monitoring_system = initialize_monitoring(video_source=video_source)
    print(f"Monitoring system started with source: {video_source}", flush=True)


@app.route('/data', methods=['GET'])
def get_data():
    """Get current crowd monitoring data"""
    if monitoring_system is None:
        return jsonify({
            "error": "Monitoring system not initialized",
            "count": 0,
            "average": 0,
            "recent_average": 0,
            "spike": 0,
            "status": "ERROR",
            "alert_triggered": False,
            "history": [],
            "density_index": 0,
            "occupancy_ratio": 0,
            "concentration_ratio": 0,
            "recent_growth": 0,
            "sudden_crowd_formation": False,
            "overcrowded": False,
            "stampede_risk": False,
            "stampede_risk_score": 0,
            "unusual_gathering": False,
            "risk_level": "LOW",
            "baseline_ready": False
        }), 500
    
    try:
        status = monitoring_system.get_current_status()
        
        response = {
            "count": status.get("count", 0),
            "average": status.get("average", 0),
            "recent_average": status.get("recent_average", 0),
            "spike": status.get("spike", 0),
            "status": status.get("status", "NORMAL"),
            "alert_triggered": status.get("alert_triggered", False),
            "history": status.get("history", []),
            "density_index": status.get("density_index", 0),
            "occupancy_ratio": status.get("occupancy_ratio", 0),
            "concentration_ratio": status.get("concentration_ratio", 0),
            "recent_growth": status.get("recent_growth", 0),
            "sudden_crowd_formation": status.get("sudden_crowd_formation", False),
            "overcrowded": status.get("overcrowded", False),
            "stampede_risk": status.get("stampede_risk", False),
            "stampede_risk_score": status.get("stampede_risk_score", 0),
            "unusual_gathering": status.get("unusual_gathering", False),
            "risk_level": status.get("risk_level", "LOW"),
            "baseline_ready": status.get("baseline_ready", False)
        }
        
        return jsonify(response)
    except Exception as e:
        print(f"Error in /data endpoint: {e}", flush=True)
        return jsonify({
            "error": str(e),
            "count": 0,
            "average": 0,
            "recent_average": 0,
            "spike": 0,
            "status": "ERROR",
            "alert_triggered": False,
            "history": [],
            "density_index": 0,
            "occupancy_ratio": 0,
            "concentration_ratio": 0,
            "recent_growth": 0,
            "sudden_crowd_formation": False,
            "overcrowded": False,
            "stampede_risk": False,
            "stampede_risk_score": 0,
            "unusual_gathering": False,
            "risk_level": "LOW",
            "baseline_ready": False
        }), 500


@app.route('/frame', methods=['GET'])
def get_frame():
    """Get current video frame as base64 encoded JPEG"""
    if monitoring_system is None:
        return jsonify({"error": "Monitoring system not initialized"}), 500
    
    frame = monitoring_system.get_current_frame()
    
    if frame is None:
        return jsonify({"error": "No frame available"}), 204
    
    # Encode frame as JPEG
    ret, jpeg_data = cv2.imencode('.jpg', frame)
    if not ret:
        return jsonify({"error": "Failed to encode frame"}), 500
    
    # Convert to base64
    frame_base64 = base64.b64encode(jpeg_data).decode('utf-8')
    
    return jsonify({
        "frame": frame_base64,
        "content_type": "image/jpeg"
    })


@app.route('/events', methods=['GET'])
def get_events():
    """Get event log"""
    if monitoring_system is None:
        return jsonify({"error": "Monitoring system not initialized"}), 500
    
    events = monitoring_system.get_event_log()
    
    return jsonify({
        "events": events
    })


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "monitoring_active": monitoring_system is not None
    })


@app.route('/config', methods=['POST'])
def update_config():
    """Update system configuration"""
    data = request.json
    
    # Implement config updates as needed
    # For now, just acknowledge
    return jsonify({
        "message": "Configuration updated",
        "config": data
    })


@app.route('/upload-video', methods=['POST'])
def upload_video():
    """Upload and process a video file"""
    if 'file' not in request.files:
        return jsonify({"error": "No file provided"}), 400
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({"error": "No file selected"}), 400
    
    if not allowed_file(file.filename):
        return jsonify({
            "error": f"File type not allowed. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
        }), 400
    
    try:
        # Save the file
        filename = secure_filename(file.filename)
        # Add timestamp to avoid conflicts
        import time
        filename = f"{int(time.time())}_{filename}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        print(f"Video uploaded: {filepath}", flush=True)
        
        # Start monitoring with this video file
        start_monitoring(video_source=filepath)
        
        return jsonify({
            "message": "Video uploaded and processing started",
            "filename": filename,
            "filepath": filepath
        }), 200
        
    except Exception as e:
        print(f"Error uploading video: {e}", flush=True)
        return jsonify({
            "error": f"Failed to upload video: {str(e)}"
        }), 500


@app.route('/caption-image', methods=['POST'])
def caption_image():
    """Generate a caption for an uploaded image using BLIP."""
    if 'file' not in request.files:
        return jsonify({"error": "No image file provided"}), 400

    file = request.files['file']

    if file.filename == '':
        return jsonify({"error": "No image file selected"}), 400

    if not allowed_image_file(file.filename):
        return jsonify({
            "error": f"Image type not allowed. Allowed: {', '.join(sorted(ALLOWED_IMAGE_EXTENSIONS))}"
        }), 400

    model_name = request.form.get('model', 'Salesforce/blip-image-captioning-large')
    try:
        from PIL import Image

        image = Image.open(file.stream).convert('RGB')
        caption = build_caption(image, model_name=model_name)

        return jsonify({
            "message": "Caption generated successfully",
            "caption": caption,
            "model": model_name,
            "filename": secure_filename(file.filename),
        }), 200
    except Exception as e:
        print(f"Error generating image caption: {e}", flush=True)
        return jsonify({
            "error": f"Failed to generate caption: {str(e)}"
        }), 500


@app.route('/analyze-event-video', methods=['POST'])
def analyze_event_video_upload():
    """Analyze an uploaded video for violence and accident detection."""
    if 'file' not in request.files:
        return jsonify({"error": "No file provided"}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No file selected"}), 400

    if not allowed_file(file.filename):
        return jsonify({
            "error": f"File type not allowed. Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
        }), 400

    try:
        filename = secure_filename(file.filename)
        import time

        filename = f"{int(time.time())}_{filename}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        system_location = request.form.get('system_location') or get_system_location()
        analysis_result = analyze_event_video(filepath, system_location=system_location)

        return jsonify({
            **analysis_result,
            "filename": filename,
            "filepath": filepath,
        }), 200
    except Exception as e:
        print(f"Error analyzing video: {e}", flush=True)
        return jsonify({
            "error": f"Failed to analyze video: {str(e)}"
        }), 500


@app.route('/switch-source', methods=['POST'])
def switch_source():
    """Switch between camera (0) and uploaded video"""
    data = request.json or {}
    source = data.get('source', 0)
    
    try:
        # Convert string "0" to int if needed
        if source == "0" or source == 0:
            source = 0
        
        print(f"Switching to source: {source}", flush=True)
        start_monitoring(video_source=source)
        
        return jsonify({
            "message": f"Switched to source: {source}",
            "current_source": source
        }), 200
        
    except Exception as e:
        print(f"Error switching source: {e}", flush=True)
        return jsonify({
            "error": f"Failed to switch source: {str(e)}"
        }), 500


@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Endpoint not found"}), 404


@app.errorhandler(500)
def internal_error(error):
    return jsonify({"error": "Internal server error"}), 500


if __name__ == '__main__':
    # Check if model exists
    model_path = Path("models/yolov8n.pt")
    if not model_path.exists():
        print(f"Model not found at {model_path}", flush=True)
        print("Please download YOLOv8n model first:", flush=True)
        print("  from ultralytics import YOLO", flush=True)
        print("  YOLO('yolov8n.pt')  # This will download the model", flush=True)
        exit(1)
    
    # Start monitoring system (0 for webcam, or use a video file path)
    # CHANGE THIS to your video file if camera doesn't work:
    # video_source = "path/to/your/video.mp4"
    video_source = 0  # Use 0 for webcam
    
    print(f"Initializing monitoring system with source: {video_source}...", flush=True)
    try:
        start_monitoring(video_source=video_source)
        print("Monitoring system initialized successfully", flush=True)
    except Exception as e:
        print(f"Warning: Could not initialize monitoring system: {e}", flush=True)
        print("The API will still start, but /frame and /data endpoints may not work", flush=True)
    
    # Run Flask app
    print("Starting Flask API server on http://localhost:5000", flush=True)
    print("Press Ctrl+C to stop", flush=True)
    app.run(debug=False, port=5000, use_reloader=False, threaded=True)
