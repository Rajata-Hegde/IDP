"""
Main processing loop - capture video and run detection + analysis
"""
import cv2
import threading
from detector import PersonDetector
from analysis import CrowdAnalyzer
from pathlib import Path


class CrowdMonitoringSystem:
    def __init__(self, model_path="models/yolov8n.pt", video_source=0):
        """
        Initialize the monitoring system
        
        Args:
            model_path: Path to YOLO model
            video_source: Video source (0 for webcam, or video file path)
        """
        self.detector = PersonDetector(model_path)
        self.analyzer = CrowdAnalyzer()
        self.video_source = video_source
        self.running = False
        self.current_frame = None
        self.is_processing = False
        
    def process_video_stream(self):
        """
        Main processing loop - capture frames and run detection
        """
        cap = cv2.VideoCapture(self.video_source)
        
        if not cap.isOpened():
            print(f"Error: Cannot open video source {self.video_source}", flush=True)
            return
        
        print("Video stream opened. Starting detection...", flush=True)
        frame_count = 0
        
        while self.running:
            ret, frame = cap.read()
            if not ret:
                print("End of video or error reading frame", flush=True)
                break
            
            try:
                frame_count += 1
                # Resize frame for faster processing
                frame = cv2.resize(frame, (640, 480))
                
                # Run detection
                detection = self.detector.detect(frame)
                
                if detection.get("success", True):
                    person_count = detection["count"]
                    self.analyzer.add_detection(
                        count=person_count,
                        boxes=detection.get("boxes", []),
                        frame_shape=frame.shape,
                    )
                    
                    # Log every 30 frames (roughly every second at 30fps)
                    if frame_count % 30 == 0:
                        print(f"Frame {frame_count}: Detected {person_count} people", flush=True)
                    
                    # Draw boxes on frame
                    frame_with_boxes = self.detector.draw_boxes(frame, detection)
                    
                    # Add metrics text to frame
                    status = self.analyzer.get_status()
                    self._draw_metrics(frame_with_boxes, status)
                    
                    self.current_frame = frame_with_boxes
                else:
                    self.current_frame = frame
                
                self.is_processing = False
                
            except Exception as e:
                print(f"Error processing frame: {e}", flush=True)
        
        cap.release()
        cv2.destroyAllWindows()
        print("Video stream closed", flush=True)
    
    def _draw_metrics(self, frame, status):
        """Draw metrics on frame"""
        h, w = frame.shape[:2]
        
        # Count (main metric)
        cv2.putText(frame, f"People: {status['count']}", (10, 40),
                   cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 255, 0), 3)
        
        # Average
        cv2.putText(frame, f"Avg: {status['average']}", (10, 80),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 0), 2)

        # Density
        density_color = (0, 0, 255) if status.get('overcrowded') else (255, 165, 0)
        cv2.putText(frame, f"Density: {status.get('density_index', 0)}", (10, 120),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.8, density_color, 2)

        # Spike (sudden increase)
        spike_color = (0, 0, 255) if status['spike'] > 2 else (255, 165, 0)
        cv2.putText(frame, f"Spike: {status['spike']}", (10, 160),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.8, spike_color, 2)

        # Risk level
        risk_color = (0, 0, 255) if status.get('stampede_risk') else (255, 255, 255)
        cv2.putText(frame, f"Risk: {status.get('risk_level', 'LOW')}", (10, 200),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.8, risk_color, 2)

        # Status - make it very visible
        status_color = (0, 0, 255) if status['status'] == "ALERT" else (0, 255, 0)
        status_thickness = 3 if status['status'] == "ALERT" else 2
        cv2.putText(frame, f"Status: {status['status']}", (10, 240),
                   cv2.FONT_HERSHEY_SIMPLEX, 1, status_color, status_thickness)
        
        # Draw a filled rectangle background for better visibility
        if status['status'] == "ALERT":
            cv2.rectangle(frame, (5, 15), (w-5, 255), (0, 0, 255), -1)
            cv2.rectangle(frame, (5, 15), (w-5, 255), (255, 255, 255), 2)
    
    def start(self):
        """Start the monitoring system"""
        self.running = True
        self.thread = threading.Thread(target=self.process_video_stream, daemon=True)
        self.thread.start()
        print("Crowd monitoring system started")
    
    def stop(self):
        """Stop the monitoring system"""
        self.running = False
        if hasattr(self, 'thread'):
            self.thread.join(timeout=5)
        print("Crowd monitoring system stopped")
    
    def get_current_status(self):
        """Get current analysis status"""
        return self.analyzer.get_status()
    
    def get_current_frame(self):
        """Get current frame"""
        return self.current_frame
    
    def get_event_log(self):
        """Get event log"""
        return self.analyzer.get_event_log()


# Global instance
monitoring_system = None


def initialize_monitoring(model_path="models/yolov8n.pt", video_source=0):
    """Initialize the global monitoring system"""
    global monitoring_system
    monitoring_system = CrowdMonitoringSystem(model_path, video_source)
    monitoring_system.start()
    return monitoring_system


if __name__ == "__main__":
    system = initialize_monitoring()
    
    try:
        import time
        while True:
            time.sleep(1)
            status = system.get_current_status()
            print(f"Count: {status['count']}, Avg: {status['average']}, Status: {status['status']}")
    except KeyboardInterrupt:
        print("Shutting down...")
        system.stop()
