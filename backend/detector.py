"""
YOLO-based person detector module
"""
import cv2
import torch

# Monkey-patch torch.load to disable weights_only for YOLO model loading
_original_torch_load = torch.load


def _patched_torch_load(f, *args, **kwargs):
    kwargs['weights_only'] = False
    return _original_torch_load(f, *args, **kwargs)


torch.load = _patched_torch_load


class PersonDetector:
    def __init__(self, model_path="models/yolov8n.pt"):
        """
        Initialize the YOLO detector

        Args:
            model_path: Path to the YOLOv8 model file
        """
        self.model_path = model_path
        self.model = None  # Lazy loaded
        self.person_class_id = 0  # Person is class 0 in COCO dataset
        self.conf_threshold = 0.25

    def _load_model(self):
        """Lazy load the YOLO model on first use"""
        if self.model is None:
            print(f"Loading YOLO model from {self.model_path}...", flush=True)
            from ultralytics import YOLO

            self.model = YOLO(self.model_path)
            print("YOLO model loaded successfully", flush=True)

    def detect(self, frame):
        """
        Detect people in a frame

        Args:
            frame: Input video frame (numpy array)

        Returns:
            Dictionary with:
            - count: Number of people detected
            - boxes: List of bounding boxes [x1, y1, x2, y2]
            - confidences: List of detection confidence scores
        """
        self._load_model()  # Lazy load on first use

        try:
            results = self.model(frame, verbose=False, conf=self.conf_threshold, classes=[self.person_class_id])
            result = results[0]

            people_boxes = []
            confidences = []

            # YOLO is already restricted to the person class, but keep the
            # class check as a safeguard for custom model swaps.
            if result.boxes is not None and len(result.boxes) > 0:
                for box in result.boxes:
                    class_id = int(box.cls[0])
                    conf = float(box.conf[0])

                    # Only count if confidence > 0.25 and it's a person
                    if class_id == self.person_class_id and conf >= self.conf_threshold:
                        people_boxes.append(box.xyxy[0].tolist())
                        confidences.append(conf)

            return {
                "count": len(people_boxes),
                "boxes": people_boxes,
                "confidences": confidences,
                "success": True,
            }
        except Exception as e:
            print(f"Detection error: {e}", flush=True)
            return {
                "count": 0,
                "boxes": [],
                "confidences": [],
                "success": False,
            }

    def draw_boxes(self, frame, detection_result):
        """
        Draw bounding boxes on the frame

        Args:
            frame: Input video frame
            detection_result: Detection result from detect()

        Returns:
            Frame with drawn boxes
        """
        frame_copy = frame.copy()

        for box, conf in zip(detection_result["boxes"], detection_result["confidences"]):
            x1, y1, x2, y2 = box
            x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)

            # Draw box
            cv2.rectangle(frame_copy, (x1, y1), (x2, y2), (0, 255, 0), 2)

            # Draw confidence
            label = f"Person: {conf:.2f}"
            cv2.putText(
                frame_copy,
                label,
                (x1, y1 - 10),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (0, 255, 0),
                2,
            )

        return frame_copy