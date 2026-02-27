"""
===============================================================================
🚁 TRINETRA - MULTI-MODE DISASTER RESCUE SYSTEM (FIXED)
===============================================================================
✅ Shows correct human counts by distance
✅ Auto-capture working with serial numbers
✅ All 8 modes ready
===============================================================================
"""

import cv2
import numpy as np
from mss import mss
from ultralytics import YOLO
import time
import threading
from flask import Flask, Response, render_template_string, jsonify
import os
from pathlib import Path
from datetime import datetime
import torch

# ===============================
# CONFIGURATION
# ===============================
CONFIG = {
    "screen_region": {"top": 100, "left": 400, "width": 800, "height": 600},
    "web_host": "127.0.0.1",
    "web_port": 5000,
    "confidence": 0.35,
    "auto_capture": True,
    "capture_cooldown": 2,
}

# ===============================
# SIZE CATEGORIES FOR DISTANCE ESTIMATION - FIXED RANGES
# ===============================
SIZE_CATEGORIES = {
    "tiny": {"range": (5, 20), "color": (0, 0, 255), "distance": "200m", "label": "🔴 TINY"},
    "small": {"range": (20, 40), "color": (0, 165, 255), "distance": "150m", "label": "🟠 SMALL"},
    "medium": {"range": (40, 80), "color": (0, 255, 255), "distance": "100m", "label": "🟡 MEDIUM"},
    "large": {"range": (80, 150), "color": (0, 255, 0), "distance": "50m", "label": "🟢 LARGE"},
    "xlarge": {"range": (150, 2000), "color": (255, 0, 255), "distance": "<20m", "label": "🟣 CLOSE"}
}

# ===============================
# MODE CONFIGURATIONS
# ===============================
MODES = {
    "1": {
        "name": "🏠 BASIC",
        "description": "Human detection only",
        "model": "models/01_basic_human.pt",
        "classes": [0],
        "class_names": {0: "Human"},
        "color": (0, 255, 0),
        "hex_color": "#00ff00"
    },
    "2": {
        "name": "🚨 DISASTER",
        "description": "Human detection in disaster zones",
        "model": "models/02_disaster_real.pt",
        "classes": [0, 1, 2],
        "class_names": {0: "🔥 Fire", 1: "💨 Smoke", 2: "👤 Human"},
        "color": (0, 0, 255),
        "hex_color": "#ff0000"
    },
    "3": {
        "name": "🌲 FOREST",
        "description": "Wildlife detection",
        "model": "models/03_forest_animals.pt",
        "classes": [14, 15, 16, 17, 18, 19, 20, 21, 22, 23],
        "class_names": {
            14: "Bird", 15: "Cat", 16: "Dog", 17: "Horse", 18: "Sheep",
            19: "Cow", 20: "Elephant", 21: "Bear", 22: "Zebra", 23: "Giraffe"
        },
        "color": (0, 255, 255),
        "hex_color": "#00ffff"
    },
    "4": {
        "name": "🌊 MARINE",
        "description": "Marine vessel detection",
        "model": "models/04_marine.pt",
        "classes": [0, 8, 9],
        "class_names": {0: "Human", 8: "🚤 Boat", 9: "🚢 Ship"},
        "color": (0, 165, 255),
        "hex_color": "#00a5ff"
    },
    "5": {
        "name": "🚗 VEHICLE",
        "description": "Vehicle detection",
        "model": "models/05_vehicle.pt",
        "classes": [1, 2, 3, 5, 7],
        "class_names": {1: "🚲 Bicycle", 2: "🚗 Car", 3: "🏍️ Motorcycle", 5: "🚌 Bus", 7: "🚛 Truck"},
        "color": (255, 255, 0),
        "hex_color": "#ffff00"
    },
    "6": {
        "name": "⚔️ ARMY",
        "description": "Military personnel detection",
        "model": "models/06_army.pt",
        "classes": [0],
        "class_names": {0: "⚔️ Personnel"},
        "color": (128, 0, 128),
        "hex_color": "#800080"
    },
    "7": {
        "name": "🚢 SHIP",
        "description": "Ship detection",
        "model": "models/07_ship.pt",
        "classes": [8, 9],
        "class_names": {8: "🚤 Boat", 9: "🚢 Ship"},
        "color": (255, 0, 255),
        "hex_color": "#ff00ff"
    },
    "8": {
        "name": "⛏️ MINING",
        "description": "Mining safety monitoring",
        "model": "models/08_mining.pt",
        "classes": [0],
        "class_names": {0: "⛏️ Miner"},
        "color": (255, 165, 0),
        "hex_color": "#ffa500"
    }
}

# ===============================
# HTML TEMPLATE - FIXED STATS DISPLAY
# ===============================
DETECTION_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>{{ mode_name }} - TRINETRA</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; font-family: 'Segoe UI', sans-serif; }
        body { background: #0a0a0a; color: white; padding: 15px; }
        .container { max-width: 100%; margin: 0 auto; }
        .header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px; flex-wrap: wrap; }
        .mode-badge { background: {{ mode_color }}; color: black; padding: 8px 20px; border-radius: 25px; font-weight: bold; }
        .stats-badge { background: #333; padding: 8px 20px; border-radius: 25px; }
        .video-container { width: 100%; background: #000; border-radius: 12px; overflow: hidden; 
                          margin: 15px 0; border: 3px solid {{ mode_color }}; }
        .video-container img { width: 100%; height: auto; display: block; }
        .dashboard { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 10px; margin: 20px 0; }
        .stat-card { background: #1a1a1a; border-radius: 10px; padding: 15px; border-left: 4px solid; }
        .stat-card.tiny { border-left-color: #ff0000; }
        .stat-card.small { border-left-color: #ffa500; }
        .stat-card.medium { border-left-color: #ffff00; }
        .stat-card.large { border-left-color: #00ff00; }
        .stat-card.xlarge { border-left-color: #ff00ff; }
        .stat-number { font-size: 2rem; font-weight: bold; }
        .stat-label { color: #888; font-size: 0.8rem; }
        .controls { display: flex; gap: 10px; margin: 15px 0; flex-wrap: wrap; }
        .btn { padding: 10px 20px; border: none; border-radius: 5px; cursor: pointer; 
               font-weight: bold; text-decoration: none; display: inline-block; }
        .btn-primary { background: {{ mode_color }}; color: black; }
        .btn-secondary { background: #333; color: white; }
        .recent-panel { background: #1a1a1a; border-radius: 10px; padding: 15px; margin-top: 20px; max-height: 300px; overflow-y: auto; }
        .detection-item { display: flex; justify-content: space-between; padding: 8px; border-bottom: 1px solid #333; }
        .serial { color: {{ mode_color }}; font-weight: bold; }
        .footer { margin-top: 20px; color: #666; font-size: 0.8rem; text-align: center; }
        .refresh-btn { background: #444; color: white; border: none; padding: 5px 10px; border-radius: 5px; cursor: pointer; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <span class="mode-badge">{{ mode_name }}</span>
            <span class="stats-badge">⚡ {{ fps }} FPS | 🎯 {{ stats.total }} total</span>
        </div>
        
        <div class="video-container">
            <img src="/video_feed" alt="Live Feed" id="videoFeed">
        </div>
        
        <div class="controls">
            <a href="/" class="btn btn-secondary">🔙 Change Mode</a>
            <button class="btn btn-primary" onclick="captureNow()">📸 Capture Now</button>
            <button class="btn btn-secondary" onclick="refreshStats()">🔄 Refresh</button>
        </div>
        
        <div class="dashboard">
            <div class="stat-card tiny">
                <div class="stat-label">🔴 TINY (200m)</div>
                <div class="stat-number" id="tinyCount">{{ stats.tiny }}</div>
            </div>
            <div class="stat-card small">
                <div class="stat-label">🟠 SMALL (150m)</div>
                <div class="stat-number" id="smallCount">{{ stats.small }}</div>
            </div>
            <div class="stat-card medium">
                <div class="stat-label">🟡 MEDIUM (100m)</div>
                <div class="stat-number" id="mediumCount">{{ stats.medium }}</div>
            </div>
            <div class="stat-card large">
                <div class="stat-label">🟢 LARGE (50m)</div>
                <div class="stat-number" id="largeCount">{{ stats.large }}</div>
            </div>
            <div class="stat-card xlarge">
                <div class="stat-label">🟣 CLOSE (<20m)</div>
                <div class="stat-number" id="xlargeCount">{{ stats.xlarge }}</div>
            </div>
        </div>
        
        <div class="recent-panel">
            <h3>📋 Recent Detections</h3>
            <div id="recent-list">
                {% for det in recent_detections %}
                <div class="detection-item">
                    <span><span class="serial">#{{ det.serial }}</span> {{ det.label }}</span>
                    <span>{{ det.time }}</span>
                </div>
                {% endfor %}
            </div>
        </div>
        
        <div class="footer">
            Serial Counter: <strong id="serial">{{ serial }}</strong> | Auto-capture: {{ "ON" if auto_capture else "OFF" }}
        </div>
    </div>
    
    <script>
        function captureNow() {
            fetch('/capture')
                .then(response => response.json())
                .then(data => {
                    alert('📸 Captured: ' + data.filename);
                    refreshStats();
                });
        }
        
        function refreshStats() {
            fetch('/stats')
                .then(response => response.json())
                .then(data => {
                    document.getElementById('tinyCount').innerText = data.tiny || 0;
                    document.getElementById('smallCount').innerText = data.small || 0;
                    document.getElementById('mediumCount').innerText = data.medium || 0;
                    document.getElementById('largeCount').innerText = data.large || 0;
                    document.getElementById('xlargeCount').innerText = data.xlarge || 0;
                    document.getElementById('serial').innerText = 'S' + String(data.serial).padStart(4, '0');
                });
        }
        
        // Auto-refresh every 2 seconds
        setInterval(refreshStats, 2000);
        
        // Also refresh when page loads
        window.onload = refreshStats;
    </script>
</body>
</html>
"""

MODE_SELECTION_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>🚁 TRINETRA - Rescue System</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; font-family: 'Segoe UI', sans-serif; }
        body { background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%); min-height: 100vh; padding: 20px; }
        .container { max-width: 1200px; margin: 0 auto; }
        h1 { color: white; text-align: center; font-size: 2.5rem; margin-bottom: 10px; }
        .subtitle { color: #00ff88; text-align: center; margin-bottom: 30px; }
        .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px; }
        .mode-card { background: white; border-radius: 15px; padding: 20px; cursor: pointer; 
                    transition: transform 0.3s, box-shadow 0.3s; box-shadow: 0 10px 20px rgba(0,0,0,0.2); }
        .mode-card:hover { transform: translateY(-5px); box-shadow: 0 15px 30px rgba(0,255,136,0.3); }
        .mode-name { font-size: 1.3rem; font-weight: bold; margin: 10px 0; }
        .mode-desc { color: #666; font-size: 0.9rem; }
        .model-status { font-size: 0.8rem; color: #00ff88; margin-top: 10px; }
        .local-info { background: rgba(255,255,255,0.1); padding: 15px; border-radius: 10px; 
                     margin-top: 30px; text-align: center; color: white; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🚁 TRINETRA</h1>
        <div class="subtitle">AI-Powered Disaster Rescue System</div>
        
        <div class="grid">
            {% for num, mode in modes.items() %}
            <div class="mode-card" onclick="selectMode('{{ num }}')" style="border-left: 5px solid {{ mode.hex_color }};">
                <div class="mode-name">{{ mode.name }}</div>
                <div class="mode-desc">{{ mode.description }}</div>
                <div class="model-status">{{ "✅ Model Ready" if mode.model_exists else "❌ Not Trained" }}</div>
            </div>
            {% endfor %}
        </div>
        
        <div class="local-info">
            <p>📱 Open on this computer: <strong>http://localhost:5000</strong></p>
        </div>
    </div>
    
    <script>
        function selectMode(mode) {
            window.location.href = '/start/' + mode;
        }
    </script>
</body>
</html>
"""

# ===============================
# CAPTURE MANAGER
# ===============================
class CaptureManager:
    def __init__(self):
        self.serial_counter = 1
        self.recent_detections = []
        os.makedirs("captured_images", exist_ok=True)
    
    def capture(self, frame, detections, mode_name, stats):
        """Capture image with serial number"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        serial = f"S{self.serial_counter:04d}"
        filename = f"captured_images/{serial}_{timestamp}.jpg"
        
        # Annotate frame
        annotated = frame.copy()
        h, w = annotated.shape[:2]
        
        # Add header
        cv2.rectangle(annotated, (0, 0), (w, 120), (0, 0, 0), -1)
        cv2.putText(annotated, f"TRINETRA - {mode_name}", (10, 30),
                   cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
        cv2.putText(annotated, f"Serial: {serial}", (10, 60),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
        cv2.putText(annotated, f"Stats: T{stats['tiny']} S{stats['small']} M{stats['medium']} L{stats['large']} C{stats['xlarge']}", 
                   (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
        
        # Draw detections
        for det in detections[:10]:
            x1, y1, x2, y2 = det["bbox"]
            color = det.get("color", (0, 255, 0))
            cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 3)
            
            label = f"{det['label']}"
            cv2.putText(annotated, label, (x1, y1-10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
        
        cv2.imwrite(filename, annotated)
        
        # Add to recent detections
        self.recent_detections.insert(0, {
            'serial': serial,
            'label': f"{len(detections)} detections",
            'time': datetime.now().strftime("%H:%M:%S")
        })
        if len(self.recent_detections) > 10:
            self.recent_detections.pop()
        
        self.serial_counter += 1
        return filename, serial

# ===============================
# DETECTOR CLASS
# ===============================
class ModeDetector:
    def __init__(self, mode_num):
        self.mode_num = mode_num
        self.mode = MODES[mode_num]
        self.recent_detections = []
        self.stats = {'total': 0, 'tiny': 0, 'small': 0, 'medium': 0, 'large': 0, 'xlarge': 0}
        
        # Load model
        model_path = Path(self.mode["model"])
        if model_path.exists():
            self.model = YOLO(str(model_path))
            size = model_path.stat().st_size / (1024*1024)
            print(f"✅ Loaded {self.mode['name']} model ({size:.1f} MB)")
        else:
            print(f"❌ Model not found: {model_path}")
            self.model = None
    
    def get_size_category(self, size):
        """Categorize by pixel size for distance estimation"""
        for cat, info in SIZE_CATEGORIES.items():
            if info["range"][0] <= size <= info["range"][1]:
                return cat, info
        return "large", SIZE_CATEGORIES["large"]
    
    def detect(self, frame):
        if not self.model:
            return []
        
        results = self.model(frame, conf=CONFIG["confidence"], verbose=False)
        
        detections = []
        
        # Reset stats
        for key in self.stats:
            self.stats[key] = 0
        
        for r in results:
            for box in r.boxes:
                cls_id = int(box.cls[0])
                conf = float(box.conf[0])
                
                # Mode-specific filtering
                if cls_id in self.mode["classes"]:
                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                    size = max(x2 - x1, y2 - y1)
                    
                    # Get category and update stats
                    cat, info = self.get_size_category(size)
                    self.stats[cat] += 1
                    
                    # Get class name
                    class_name = self.mode["class_names"].get(cls_id, f"Class {cls_id}")
                    
                    # Special formatting for disaster mode
                    if self.mode_num == "2":
                        if cls_id == 0:
                            label = f"🔥 Fire"
                        elif cls_id == 1:
                            label = f"💨 Smoke"
                        else:
                            label = f"👤 Human"
                    else:
                        label = f"{class_name}"
                    
                    detections.append({
                        "bbox": (x1, y1, x2, y2),
                        "label": label,
                        "conf": conf,
                        "size": size,
                        "category": cat,
                        "color": info["color"],
                        "class_id": cls_id
                    })
        
        self.stats['total'] = len(detections)
        return detections

# ===============================
# FLASK SERVER
# ===============================
class RescueServer:
    def __init__(self):
        self.app = Flask(__name__)
        self.detector = None
        self.frame = None
        self.fps = 0
        self.capture_manager = CaptureManager()
        self.last_capture = 0
        self.setup_routes()
    
    def setup_routes(self):
        @self.app.route('/')
        def index():
            # Check which models exist
            for mode in MODES.values():
                mode["model_exists"] = Path(mode["model"]).exists()
            
            return render_template_string(
                MODE_SELECTION_HTML,
                modes=MODES
            )
        
        @self.app.route('/start/<mode>')
        def start_mode(mode):
            if mode in MODES:
                self.detector = ModeDetector(mode)
                return render_template_string(
                    DETECTION_HTML,
                    mode_name=MODES[mode]['name'],
                    mode_color=MODES[mode]['hex_color'],
                    stats=self.detector.stats if self.detector else {'total':0, 'tiny':0, 'small':0, 'medium':0, 'large':0, 'xlarge':0},
                    recent_detections=self.capture_manager.recent_detections,
                    fps="0.0",
                    serial=f"S{self.capture_manager.serial_counter:04d}",
                    auto_capture=CONFIG["auto_capture"]
                )
            return "Invalid mode", 404
        
        @self.app.route('/video_feed')
        def video_feed():
            return Response(self.generate_frames(),
                          mimetype='multipart/x-mixed-replace; boundary=frame')
        
        @self.app.route('/stats')
        def get_stats():
            if self.detector:
                stats = self.detector.stats.copy()
                stats['serial'] = self.capture_manager.serial_counter
                return jsonify(stats)
            return jsonify({'total':0, 'tiny':0, 'small':0, 'medium':0, 'large':0, 'xlarge':0, 'serial':1})
        
        @self.app.route('/capture')
        def capture():
            if self.frame is not None and self.detector:
                filename, serial = self.capture_manager.capture(
                    self.frame, 
                    self.detector.recent_detections[-10:] if self.detector.recent_detections else [],
                    self.detector.mode['name'],
                    self.detector.stats
                )
                return jsonify({"success": True, "filename": filename, "serial": serial})
            return jsonify({"success": False})
    
    def generate_frames(self):
        while True:
            if self.frame is not None:
                try:
                    _, buffer = cv2.imencode('.jpg', self.frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
                    yield (b'--frame\r\n'
                          b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
                except:
                    pass
            time.sleep(0.03)
    
    def update_frame(self, frame, fps):
        self.frame = frame
        self.fps = fps
        
        # Auto-capture if enabled and humans detected
        if (CONFIG["auto_capture"] and self.detector and 
            self.detector.stats['total'] > 0 and 
            time.time() - self.last_capture > CONFIG["capture_cooldown"]):
            
            filename, serial = self.capture_manager.capture(
                frame,
                self.detector.recent_detections[-10:] if self.detector.recent_detections else [],
                self.detector.mode['name'],
                self.detector.stats
            )
            self.last_capture = time.time()
            print(f"📸 Auto-captured {serial} with {self.detector.stats['total']} detections")
    
    def run(self):
        threading.Thread(target=self.app.run, 
                        kwargs={'host': CONFIG["web_host"], 
                               'port': CONFIG["web_port"], 
                               'debug': False, 
                               'threaded': True},
                        daemon=True).start()

# ===============================
# MAIN
# ===============================
def main():
    print("=" * 80)
    print("🚁 TRINETRA - MULTI-MODE RESCUE SYSTEM (FIXED)")
    print("=" * 80)
    
    # Check models
    print("\n📦 Checking trained models:")
    for mode_num, mode in MODES.items():
        model_path = Path(mode["model"])
        if model_path.exists():
            size = model_path.stat().st_size / (1024*1024)
            print(f"   ✅ {mode['name']}: {mode['model']} ({size:.1f} MB)")
        else:
            print(f"   ❌ {mode['name']}: NOT FOUND - {mode['model']}")
    
    # Start server
    server = RescueServer()
    server.run()
    
    # Screen capture
    sct = mss()
    screen = CONFIG["screen_region"]
    
    print("\n" + "=" * 80)
    print("📱 OPEN IN BROWSER: http://localhost:5000")
    print("=" * 80)
    print("\n✅ Server running. Press Ctrl+C to stop\n")
    
    try:
        while True:
            if server.detector and server.detector.model:
                frame_start = time.time()
                
                # Capture screen
                img = sct.grab(screen)
                frame = np.array(img)
                frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)
                
                # Detect
                detections = server.detector.detect(frame)
                server.detector.recent_detections = detections
                
                # Draw on frame
                display = frame.copy()
                for det in detections:
                    x1, y1, x2, y2 = det["bbox"]
                    color = det["color"]
                    
                    cv2.rectangle(display, (x1, y1), (x2, y2), color, 2)
                    cv2.putText(display, det['label'], (x1, y1-5),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
                
                # Add overlay with stats
                h, w = display.shape[:2]
                overlay = display.copy()
                cv2.rectangle(overlay, (10, 10), (350, 130), (0, 0, 0), -1)
                cv2.addWeighted(overlay, 0.7, display, 0.3, 0, display)
                
                # Add stats
                y_offset = 35
                cv2.putText(display, f"TRINETRA - {server.detector.mode['name']}", 
                           (20, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
                cv2.putText(display, f"Total: {server.detector.stats['total']}", 
                           (20, y_offset+25), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
                cv2.putText(display, f"T:{server.detector.stats['tiny']} S:{server.detector.stats['small']} M:{server.detector.stats['medium']} L:{server.detector.stats['large']} C:{server.detector.stats['xlarge']}", 
                           (20, y_offset+50), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
                
                # FPS
                fps = 1.0 / (time.time() - frame_start)
                server.update_frame(display, fps)
                
                # Show status
                if len(detections) > 0:
                    print(f"\r⚡ {server.detector.mode['name']} | "
                          f"Detected: {len(detections)} | "
                          f"T:{server.detector.stats['tiny']} S:{server.detector.stats['small']} "
                          f"M:{server.detector.stats['medium']} L:{server.detector.stats['large']} "
                          f"C:{server.detector.stats['xlarge']}", end='')
            
            time.sleep(0.01)
    
    except KeyboardInterrupt:
        print("\n\n🛑 Shutting down...")
        cv2.destroyAllWindows()

if __name__ == "__main__":
    main()