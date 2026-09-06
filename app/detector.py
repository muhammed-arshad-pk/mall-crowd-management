"""
YOLO person detector.

Detects ONLY class 0 ("person") from a COCO-pretrained YOLO model - every
other COCO class (car, bag, chair, dog, phone, ...) is filtered out at the
model call itself via `classes=[0]`, not post-filtered, so they never cost
inference time either.

track() adds ByteTrack for stable per-person IDs across frames, required for
track-confirmation stability and frame-based entry/exit.
"""
import logging

from ultralytics import YOLO

import config

logger = logging.getLogger(__name__)

COCO_PERSON_CLASS_ID = 0


class PersonDetector:
    """Detects people in a single frame using a COCO-pretrained YOLO model,
    filtered to class 0 ("person") only."""

    def __init__(self, model_path=config.MODEL_PATH, device=None):
        self.model = YOLO(model_path)
        self.device = device if device is not None else config.resolve_device()

        if self.model.names.get(COCO_PERSON_CLASS_ID) != "person":
            raise RuntimeError(
                f"Expected class {COCO_PERSON_CLASS_ID} of this model to be 'person', got "
                f"{self.model.names.get(COCO_PERSON_CLASS_ID)!r}. This model is not a "
                f"standard COCO-pretrained YOLO model."
            )
        logger.info("Person model loaded on device=%s", self.device)

    def track(self, frame):
        """Runs tracked person detection on one frame via ByteTrack.

        Returns a list of dicts: {"id": int, "box": (x1, y1, x2, y2), "conf": float}.
        """
        results = self.model.track(
            frame,
            persist=True,
            classes=[COCO_PERSON_CLASS_ID],
            conf=config.CONFIDENCE_THRESHOLD,
            imgsz=config.IMAGE_SIZE,
            tracker=config.TRACKER_CONFIG,
            device=self.device,
            verbose=False,
        )

        boxes = results[0].boxes
        if boxes is None or boxes.id is None:
            return []

        detections = []
        for xyxy, track_id, conf in zip(
            boxes.xyxy.cpu().numpy(), boxes.id.cpu().numpy(), boxes.conf.cpu().numpy()
        ):
            detections.append({
                "id": int(track_id),
                "box": tuple(float(v) for v in xyxy),
                "conf": float(conf),
            })
        return detections
