"""
Event analysis pipeline for accident and violence video detection.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime
from functools import lru_cache
from pathlib import Path
from typing import List, Sequence

import cv2
import numpy as np
import torch
import torch.nn as nn
import torchvision.transforms as transforms
from PIL import Image
from torchvision.models import MobileNet_V2_Weights, mobilenet_v2

FRAME_SAMPLE_FPS = 8
SEQUENCE_LENGTH = 20
STEP_SIZE = 5
ACCIDENT_THRESHOLD = 0.5
VIOLENCE_THRESHOLD = 0.6
MIN_POSITIVE_VOTES = 2

DEFAULT_SYSTEM_LOCATION = "Local monitoring workstation"


class LSTMModel(nn.Module):
    def __init__(self):
        super().__init__()
        self.lstm = nn.LSTM(1280, 256, batch_first=True)
        self.fc = nn.Linear(256, 2)

    def forward(self, x):
        out, _ = self.lstm(x)
        out = out[:, -1, :]
        return self.fc(out)


@dataclass
class SequencePrediction:
    sequence_index: int
    start_frame: int
    end_frame: int
    start_seconds: float
    end_seconds: float
    midpoint_seconds: float
    confidence: float
    detected: bool


@lru_cache(maxsize=1)
def get_feature_extractor():
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = mobilenet_v2(weights=MobileNet_V2_Weights.DEFAULT)
    model.classifier = nn.Identity()
    model = model.to(device)
    model.eval()

    transform = transforms.Compose(
        [
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
        ]
    )

    return model, transform, device


@lru_cache(maxsize=1)
def get_event_models():
    _, _, device = get_feature_extractor()

    model_root = Path(__file__).resolve().parent / "models"
    violence_path = model_root / "violence_model.pth"
    accident_path = model_root / "accident_model_run1.pth"

    violence_model = LSTMModel().to(device)
    accident_model = LSTMModel().to(device)

    violence_model.load_state_dict(torch.load(violence_path, map_location=device))
    accident_model.load_state_dict(torch.load(accident_path, map_location=device))

    violence_model.eval()
    accident_model.eval()

    return {
        "device": device,
        "violence_model": violence_model,
        "accident_model": accident_model,
    }


def _sample_frames(video_path: str, target_fps: int = FRAME_SAMPLE_FPS):
    capture = cv2.VideoCapture(video_path)
    if not capture.isOpened():
        raise ValueError(f"Cannot open video source: {video_path}")

    source_fps = capture.get(cv2.CAP_PROP_FPS) or 0
    frame_count = int(capture.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    if source_fps <= 0:
        source_fps = target_fps

    frame_interval = max(int(round(source_fps / target_fps)), 1)
    sampled_frames = []
    sampled_frame_indices = []
    raw_frames_read = 0

    while True:
        success, frame = capture.read()
        if not success:
            break

        if raw_frames_read % frame_interval == 0:
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            sampled_frames.append(Image.fromarray(rgb_frame))
            sampled_frame_indices.append(raw_frames_read)

        raw_frames_read += 1

    capture.release()

    if not sampled_frames:
        raise ValueError("No frames could be extracted from the uploaded video")

    duration_seconds = 0.0
    if source_fps > 0 and frame_count > 0:
        duration_seconds = frame_count / source_fps
    elif sampled_frame_indices:
        duration_seconds = sampled_frame_indices[-1] / float(target_fps)

    return sampled_frames, sampled_frame_indices, source_fps, duration_seconds, frame_count


def _extract_features(frames: Sequence[Image.Image]):
    feature_extractor, transform, device = get_feature_extractor()
    feature_batches = []

    batch_size = 16
    for start_index in range(0, len(frames), batch_size):
        batch_frames = frames[start_index : start_index + batch_size]
        tensors = [transform(frame) for frame in batch_frames]
        batch_tensor = torch.stack(tensors).to(device)

        with torch.no_grad():
            batch_features = feature_extractor(batch_tensor)

        feature_batches.append(batch_features.detach().cpu())

    return torch.cat(feature_batches, dim=0).numpy()


def _build_sequences(features: np.ndarray, sampled_frame_indices: Sequence[int], source_fps: float):
    sequence_features = []
    sequence_metadata = []

    frame_count = len(features)
    if frame_count < SEQUENCE_LENGTH:
        pad_count = SEQUENCE_LENGTH - frame_count
        padding = np.repeat(features[-1][None, :], pad_count, axis=0)
        features = np.concatenate([features, padding], axis=0)
        sampled_frame_indices = list(sampled_frame_indices) + [sampled_frame_indices[-1]] * pad_count
        frame_count = len(features)

    for sequence_index, start_index in enumerate(range(0, frame_count - SEQUENCE_LENGTH + 1, STEP_SIZE)):
        end_index = start_index + SEQUENCE_LENGTH
        sequence_features.append(features[start_index:end_index])

        start_frame = sampled_frame_indices[start_index]
        end_frame = sampled_frame_indices[end_index - 1]
        start_seconds = start_frame / float(source_fps)
        end_seconds = end_frame / float(source_fps)
        midpoint_seconds = (start_seconds + end_seconds) / 2.0

        sequence_metadata.append(
            {
                "sequence_index": sequence_index,
                "start_frame": start_frame,
                "end_frame": end_frame,
                "start_seconds": start_seconds,
                "end_seconds": end_seconds,
                "midpoint_seconds": midpoint_seconds,
            }
        )

    return sequence_features, sequence_metadata


def _score_model(model: nn.Module, sequences: Sequence[np.ndarray], metadata: Sequence[dict], threshold: float):
    if not sequences:
        return []

    device = next(model.parameters()).device
    predictions: List[SequencePrediction] = []

    for sequence_index, sequence in enumerate(sequences):
        input_tensor = torch.tensor([sequence], dtype=torch.float32, device=device)
        with torch.no_grad():
            output = model(input_tensor)
            probabilities = torch.softmax(output, dim=1)

        confidence = float(probabilities[0][1].item())
        sequence_info = metadata[sequence_index]
        predictions.append(
            SequencePrediction(
                sequence_index=sequence_index,
                start_frame=sequence_info["start_frame"],
                end_frame=sequence_info["end_frame"],
                start_seconds=sequence_info["start_seconds"],
                end_seconds=sequence_info["end_seconds"],
                midpoint_seconds=sequence_info["midpoint_seconds"],
                confidence=confidence,
                detected=confidence >= threshold,
            )
        )

    return predictions


def _format_timestamp(seconds: float) -> str:
    seconds = max(0.0, float(seconds))
    total_seconds = int(round(seconds))
    hours, remainder = divmod(total_seconds, 3600)
    minutes, secs = divmod(remainder, 60)
    if hours:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


def _summarize_model_predictions(predictions: Sequence[SequencePrediction], threshold: float, fallback_label: str):
    if not predictions:
        return {
            "detected": False,
            "confidence": 0.0,
            "timestamp": None,
            "timestamp_seconds": None,
            "votes": 0,
            "best_sequence": None,
            "label": fallback_label,
        }

    positive_predictions = [prediction for prediction in predictions if prediction.detected]
    best_prediction = max(predictions, key=lambda prediction: prediction.confidence)
    best_positive_prediction = max(positive_predictions, key=lambda prediction: prediction.confidence) if positive_predictions else None

    selected_prediction = best_positive_prediction or best_prediction
    votes = len(positive_predictions)

    return {
        "detected": votes >= MIN_POSITIVE_VOTES if fallback_label == "accident" else votes > 0,
        "confidence": round(selected_prediction.confidence, 4),
        "timestamp": _format_timestamp(selected_prediction.midpoint_seconds),
        "timestamp_seconds": round(selected_prediction.midpoint_seconds, 2),
        "votes": votes,
        "best_sequence": {
            "sequence_index": selected_prediction.sequence_index,
            "start_frame": selected_prediction.start_frame,
            "end_frame": selected_prediction.end_frame,
            "start_seconds": round(selected_prediction.start_seconds, 2),
            "end_seconds": round(selected_prediction.end_seconds, 2),
        },
        "label": fallback_label,
    }


def analyze_event_video(video_path: str, system_location: str | None = None):
    models = get_event_models()
    violence_model = models["violence_model"]
    accident_model = models["accident_model"]

    frames, sampled_frame_indices, source_fps, duration_seconds, total_frame_count = _sample_frames(video_path)
    features = _extract_features(frames)
    sequences, sequence_metadata = _build_sequences(features, sampled_frame_indices, source_fps)

    if not sequences:
        raise ValueError("Not enough frames were available to build analysis sequences")

    with ThreadPoolExecutor(max_workers=2) as executor:
        violence_future = executor.submit(_score_model, violence_model, sequences, sequence_metadata, VIOLENCE_THRESHOLD)
        accident_future = executor.submit(_score_model, accident_model, sequences, sequence_metadata, ACCIDENT_THRESHOLD)
        violence_predictions = violence_future.result()
        accident_predictions = accident_future.result()

    violence_summary = _summarize_model_predictions(violence_predictions, VIOLENCE_THRESHOLD, "violence")
    accident_summary = _summarize_model_predictions(accident_predictions, ACCIDENT_THRESHOLD, "accident")

    overall_candidates = [
        ("violence", violence_summary),
        ("accident", accident_summary),
    ]
    positive_candidates = [candidate for candidate in overall_candidates if candidate[1]["detected"]]

    if positive_candidates:
        incident_type, incident_summary = max(positive_candidates, key=lambda candidate: candidate[1]["confidence"])
        overall_incident = incident_type.capitalize()
        overall_confidence = incident_summary["confidence"]
        overall_timestamp = incident_summary["timestamp"]
    else:
        overall_incident = "No Incident"
        overall_confidence = max(violence_summary["confidence"], accident_summary["confidence"])
        overall_timestamp = violence_summary["timestamp"] or accident_summary["timestamp"]

    resolved_location = system_location or DEFAULT_SYSTEM_LOCATION
    analysis_timestamp = datetime.now().isoformat(timespec="seconds")

    return {
        "message": "Event analysis completed successfully",
        "analysis_timestamp": analysis_timestamp,
        "video": {
            "path": video_path,
            "source": "uploaded video",
            "camera_captured": False,
            "system_location": resolved_location,
            "video_capture_note": "Analyzed from uploaded footage using a local monitoring workstation.",
            "source_fps": round(source_fps, 2),
            "frame_count": total_frame_count,
            "duration_seconds": round(duration_seconds, 2),
            "sampled_frames": len(frames),
            "sequence_length": SEQUENCE_LENGTH,
            "step_size": STEP_SIZE,
        },
        "incident_type": overall_incident,
        "confidence_score": round(overall_confidence, 4),
        "timestamp": overall_timestamp,
        "location": resolved_location,
        "models": {
            "violence": {
                **violence_summary,
                "threshold": VIOLENCE_THRESHOLD,
            },
            "accident": {
                **accident_summary,
                "threshold": ACCIDENT_THRESHOLD,
            },
        },
        "summary": {
            "violence_detected": violence_summary["detected"],
            "accident_detected": accident_summary["detected"],
            "feature_extraction": "Shared MobileNetV2 features reused for both models.",
            "parallel_inference": True,
        },
    }
