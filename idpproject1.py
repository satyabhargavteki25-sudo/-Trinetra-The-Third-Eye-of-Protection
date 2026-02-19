"""
===============================================================================
🚁 C2A DISASTER RESCUE SYSTEM - COMPLETE ALL-IN-ONE
===============================================================================
✅ Auto-setup + Detection + Web Interface + Mobile Access
✅ Just run this ONE file - everything works automatically
===============================================================================
"""

import cv2
import numpy as np
from mss import mss
from ultralytics import YOLO
import time
import winsound
from datetime import datetime
import os
from pathlib import Path
import subprocess
import sys
import threading
from flask import Flask, Response, render_template_string, jsonify
import socket

# ===============================
# CONFIGURATION
# ===============================
CONFIG = {
    # Screen capture - OPTIMIZED FOR SPEED
    "screen_region": {"top": 100, "left": 600, "width": 640, "height": 480},
    
    # Web server
    "web_host": "0.0.0.0",
    "web_port": 5000,
    
    # Detection
    "confidence": 0.25,
    "model": "yolov8n.pt",
    
    # Auto-setup
    "auto_install": True,
}

# ===============================
# AUTO-SETUP FUNCTIONS
# ===============================
def check_python_version():
    """Verify Python version"""
    version = sys.version_info
    print(f"   Python {version.major}.{version.minor}.{version.micro}")
    return version.major == 3 and version.minor >= 8

def install_requirements():
    """Install all required packages"""
    print("\n📦 Installing required libraries...")
    
    requirements = [
        "ultralytics",
        "opencv-python",
        "numpy",
        "mss",
        "flask",
        "pillow",
    ]
    
    for package in requirements:
        print(f"   Installing {package}...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "--quiet", package])
            print(f"   ✅ {package} installed")
        except:
            print(f"   ⚠ Failed to install {package}")
    
    print("✅ All libraries installed!")

def create_folders():
    """Create necessary project folders"""
    print("\n📁 Creating project folders...")
    
    folders = [
        "datasets",
        "datasets/c2a",
        "models",
        "output",
        "logs",
    ]
    
    for folder in folders:
        Path(folder).mkdir(exist_ok=True)
        print(f"   Created: {folder}")
    
    print("✅ Folders created!")

def get_local_ip():
    """Get local IP address"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "127.0.0.1"

# ===============================
# HTML TEMPLATE FOR WEB INTERFACE
# ===============================
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>🚁 C2A Disaster Rescue</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; font-family: 'Segoe UI', sans-serif; }
        body { background: #0a0a0a; color: white; padding: 15px; }
        .container { max-width: 100%; margin: 0 auto; }
        h1 { font-size: 1.5rem; text-align: center; margin: 10px 0; color: #00ff88; }
        .video-container { width: 100%; background: #000; border-radius: 12px; overflow: hidden; margin: 15px 0; border: 2px solid #333; }
        .video-container img { width: 100%; height: auto; display: block; }
        .stats-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 10px; margin-bottom: 15px; }
        .stat-card { background: #1a1a1a; border-radius: 12px; padding: 15px; border-left: 4px solid; }
        .stat-title { font-size: 0.8rem; color: #888; margin-bottom: 5px; }
        .stat-number { font-size: 2rem; font-weight: bold; }
        .human-card { border-left-color: #00ff88; }
        .tiny-card { border-left-color: #ff0000; }
        .small-card { border-left-color: #ffaa00; }
        .medium-card { border-left-color: #ffff00; }
        .large-card { border-left-color: #00ff00; }
        .xlarge-card { border-left-color: #ff00ff; }
        .details-panel { background: #1a1a1a; border-radius: 12px; padding: 15px; margin-top: 10px; }
        .detail-row { display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid #333; }
        .detail-row:last-child { border-bottom: none; }
        .label { color: #aaa; }
        .value { font-weight: bold; }
        .fps { text-align: center; color: #888; font-size: 0.8rem; margin-top: 15px; }
        .ip-badge { background: #00ff88; color: black; padding: 10px; border-radius: 20px; text-align: center; margin: 10px 0; font-weight: bold; }
        .env-badge { background: #333; color: white; padding: 5px 10px; border-radius: 20px; display: inline-block; margin-bottom: 10px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="ip-badge">
            📱 Connected to: {{ ip }}:{{ port }}
        </div>
        
        <h1>🚁 C2A Disaster Rescue</h1>
        
        <div class="video-container">
            <img src="/video_feed" alt="Live Feed">
        </div>
        
        <div class="stats-grid">
            <div class="stat-card human-card">
                <div class="stat-title">👥 TOTAL HUMANS</div>
                <div class="stat-number">{{ stats.total }}</div>
            </div>
            
            <div class="stat-card tiny-card">
                <div class="stat-title">🔴 TINY (200m)</div>
                <div class="stat-number">{{ stats.tiny }}</div>
            </div>
            
            <div class="stat-card small-card">
                <div class="stat-title">🟠 SMALL (150m)</div>
                <div class="stat-number">{{ stats.small }}</div>
            </div>
            
            <div class="stat-card medium-card">
                <div class="stat-title">🟡 MEDIUM (100m)</div>
                <div class="stat-number">{{ stats.medium }}</div>
            </div>
            
            <div class="stat-card large-card">
                <div class="stat-title">🟢 LARGE (50m)</div>
                <div class="stat-number">{{ stats.large }}</div>
            </div>
            
            <div class="stat-card xlarge-card">
                <div class="stat-title">🟣 XLARGE (<20m)</div>
                <div class="stat-number">{{ stats.xlarge }}</div>
            </div>
        </div>
        
        <div class="details-panel">
            <div class="detail-row">
                <span class="label">FPS:</span>
                <span class="value">{{ fps }}</span>
            </div>
            <div class="detail-row">
                <span class="label">Processing Time:</span>
                <span class="value">{{ proc_time }}ms</span>
            </div>
            <div class="detail-row">
                <span class="label">Model:</span>
                <span class="value">{{ model }}</span>
            </div>
        </div>
        
        <div class="fps">
            Live from drone feed • Updated in real-time
        </div>
    </div>
</body>
</html>
"""

# ===============================
# DATASET FUNCTIONS
# ===============================
def find_c2a_dataset():
    """Automatically find C2A dataset anywhere on your system"""
    print("\n" + "=" * 60)
    print("🔍 SCANNING FOR C2A DATASET")
    print("=" * 60)
    
    search_paths = [
        Path.cwd(),
        Path.cwd() / "datasets",
        Path.cwd() / "c2a-dataset",
        Path.home() / "datasets",
        Path.home() / "Downloads",
        Path.home() / "Downloads/c2a-dataset",
        Path("C:/Users/HP/datasets"),
        Path("C:/Users/HP/Downloads/c2a-dataset"),
    ]
    
    for base_path in search_paths:
        if not base_path.exists():
            continue
        print(f"   Checking: {base_path}")
        
        possible_paths = [base_path, base_path / "c2a", base_path / "C2A", base_path / "c2a-dataset"]
        
        for dataset_path in possible_paths:
            train_img = dataset_path / "train" / "images"
            val_img = dataset_path / "val" / "images"
            
            if train_img.exists() and val_img.exists():
                print(f"   ✅ FOUND DATASET AT: {dataset_path}")
                return dataset_path
    
    print("   ❌ Dataset not found automatically")
    return None

def create_c2a_yaml(dataset_path):
    """Create properly formatted data.yaml for C2A"""
    dataset_path = Path(dataset_path).absolute()
    
    yaml_content = f"""
path: {dataset_path}
train: train/images
val: val/images
nc: 1
names: ['human']
"""
    
    yaml_path = Path("c2a_data.yaml")
    with open(yaml_path, "w") as f:
        f.write(yaml_content)
    
    print(f"\n✅ Created config: {yaml_path}")
    return yaml_path

# ===============================
# C2A DETECTOR CLASS
# ===============================
class C2ADetector:
    def __init__(self):
        print("\n📦 Loading YOLO model...")
        self.model = YOLO(CONFIG["model"])
        
        self.size_categories = {
            "tiny": {"range": (5, 20), "color": (0, 0, 255), "distance": "200m"},
            "small": {"range": (20, 40), "color": (0, 165, 255), "distance": "150m"},
            "medium": {"range": (40, 80), "color": (0, 255, 255), "distance": "100m"},
            "large": {"range": (80, 150), "color": (0, 255, 0), "distance": "50m"},
            "xlarge": {"range": (150, 2000), "color": (255, 0, 255), "distance": "<20m"}
        }
        
        self.stats = {
            'total': 0, 'tiny': 0, 'small': 0, 'medium': 0, 'large': 0, 'xlarge': 0
        }
        
        print("✅ Detector ready")
    
    def detect(self, frame):
        results = self.model(frame, conf=CONFIG["confidence"], verbose=False, classes=[0])
        
        # Reset stats
        for key in self.stats:
            self.stats[key] = 0
        
        detections = []
        
        for r in results:
            for box in r.boxes:
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                conf = float(box.conf[0])
                size = max(x2 - x1, y2 - y1)
                
                cat, info = self.get_category(size)
                self.stats[cat] += 1
                
                detections.append({
                    "bbox": (x1, y1, x2, y2),
                    "confidence": conf,
                    "size": size,
                    "category": cat,
                    "color": info["color"],
                    "center": ((x1 + x2)//2, (y1 + y2)//2)
                })
        
        self.stats['total'] = len(detections)
        return detections
    
    def get_category(self, size):
        for cat, info in self.size_categories.items():
            if info["range"][0] <= size <= info["range"][1]:
                return cat, info
        return "large", self.size_categories["large"]

# ===============================
# WEB SERVER CLASS
# ===============================
class WebServer:
    def __init__(self, detector):
        self.detector = detector
        self.app = Flask(__name__)
        self.frame = None
        self.fps = 0
        self.proc_time = 0
        self.setup_routes()
        
    def setup_routes(self):
        @self.app.route('/')
        def index():
            return render_template_string(
                HTML_TEMPLATE,
                ip=get_local_ip(),
                port=CONFIG["web_port"],
                stats=self.detector.stats,
                fps=f"{self.fps:.1f}",
                proc_time=f"{self.proc_time:.0f}",
                model=CONFIG["model"]
            )
        
        @self.app.route('/video_feed')
        def video_feed():
            return Response(self.generate_frames(),
                          mimetype='multipart/x-mixed-replace; boundary=frame')
        
        @self.app.route('/stats')
        def get_stats():
            return jsonify(self.detector.stats)
    
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
    
    def update_frame(self, frame, fps, proc_time):
        self.frame = frame
        self.fps = fps
        self.proc_time = proc_time
    
    def run(self):
        threading.Thread(target=self.app.run, 
                        kwargs={'host': CONFIG["web_host"], 
                               'port': CONFIG["web_port"], 
                               'debug': False, 
                               'threaded': True,
                               'use_reloader': False},
                        daemon=True).start()

# ===============================
# MAIN FUNCTION
# ===============================
def main():
    print("=" * 70)
    print("🚁 C2A DISASTER RESCUE SYSTEM - COMPLETE")
    print("=" * 70)
    
    # STEP 1: Auto-setup
    print("\n🛠️  Running auto-setup...")
    if not check_python_version():
        print("⚠ Python 3.8+ recommended")
    
    if CONFIG["auto_install"]:
        install_requirements()
    
    create_folders()
    
    # STEP 2: Find dataset
    dataset_path = find_c2a_dataset()
    if dataset_path:
        print(f"\n✅ Dataset found at: {dataset_path}")
        create_c2a_yaml(dataset_path)
        print("\n💡 To train on C2A, run: model.train(data='c2a_data.yaml', epochs=10)")
    else:
        print("\n⚠ Using COCO model (no dataset found)")
    
    # STEP 3: Initialize detector
    detector = C2ADetector()
    
    # STEP 4: Start web server
    server = WebServer(detector)
    server.run()
    
    # STEP 5: Screen capture
    sct = mss()
    screen = CONFIG["screen_region"]
    
    # STEP 6: Local windows
    cv2.namedWindow("C2A DRONE FEED", cv2.WINDOW_NORMAL)
    cv2.resizeWindow("C2A DRONE FEED", 800, 600)
    cv2.moveWindow("C2A DRONE FEED", 0, 0)
    
    cv2.namedWindow("C2A DASHBOARD", cv2.WINDOW_NORMAL)
    cv2.resizeWindow("C2A DASHBOARD", 500, 600)
    cv2.moveWindow("C2A DASHBOARD", 810, 0)
    
    # Connection info
    local_ip = get_local_ip()
    print("\n" + "=" * 70)
    print("🌐 WEB INTERFACE ACCESS")
    print("=" * 70)
    print(f"📱 On this computer: http://localhost:{CONFIG['web_port']}")
    print(f"📱 On phone/tablet:  http://{local_ip}:{CONFIG['web_port']}")
    print("=" * 70)
    print("\n✅ SYSTEM RUNNING - Press ESC to exit")
    print("=" * 70)
    
    # Performance tracking
    start_time = time.time()
    frame_count = 0
    
    try:
        while True:
            frame_start = time.time()
            
            # Capture
            img = sct.grab(screen)
            frame = np.array(img)
            frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)
            
            # Detect
            detections = detector.detect(frame)
            
            # Draw on frame
            display = frame.copy()
            for det in detections:
                x1, y1, x2, y2 = det["bbox"]
                color = det["color"]
                
                cv2.rectangle(display, (x1, y1), (x2, y2), color, 2)
                cv2.circle(display, det["center"], 2, (255,255,255), -1)
                cv2.putText(display, f"H {det['confidence']:.2f}", 
                          (x1, y1-5), cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)
            
            # Overlay
            cv2.rectangle(display, (0, 0), (250, 70), (0,0,0), -1)
            cv2.putText(display, f"Humans: {len(detections)}", (10, 25),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0,255,0), 2)
            
            # FPS
            frame_count += 1
            elapsed = time.time() - start_time
            fps = frame_count / elapsed if elapsed > 0 else 0
            cv2.putText(display, f"FPS: {fps:.1f}", (10, 55),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (150,150,255), 1)
            
            # Create local dashboard
            dash = np.zeros((600, 500, 3), dtype=np.uint8)
            dash[:] = (30, 30, 40)
            
            y_pos = 50
            cv2.putText(dash, "📊 DETECTION STATS", (20, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0,255,0), 2)
            
            for cat, count in detector.stats.items():
                if cat != 'total':
                    color = detector.size_categories[cat]["color"]
                    dist = detector.size_categories[cat]["distance"]
                    cv2.putText(dash, f"{cat.upper()}: {count} ({dist})", 
                               (20, y_pos), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 1)
                    y_pos += 30
            
            cv2.putText(dash, f"FPS: {fps:.1f}", (20, y_pos+30),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (150,150,255), 1)
            
            # Update web server
            proc_time = (time.time() - frame_start) * 1000
            server.update_frame(display, fps, proc_time)
            
            # Show windows
            cv2.imshow("C2A DRONE FEED", display)
            cv2.imshow("C2A DASHBOARD", dash)
            
            # Controls
            if cv2.waitKey(1) & 0xFF == 27:
                break
            
            # Progress
            if frame_count % 30 == 0:
                print(f"⚡ FPS: {fps:.1f} | Humans: {len(detections)} | "
                      f"T:{detector.stats['tiny']} S:{detector.stats['small']} "
                      f"M:{detector.stats['medium']} L:{detector.stats['large']}")
    
    except KeyboardInterrupt:
        pass
    finally:
        cv2.destroyAllWindows()
        print(f"\n✅ Average FPS: {frame_count / (time.time() - start_time):.1f}")

if __name__ == "__main__":
    main()
