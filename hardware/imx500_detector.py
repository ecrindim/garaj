"""Raspberry Pi AI Camera (IMX500) üzerindeki modelle nesne tespiti.

Çıkarım kameranın kendi çipinde yapılır; Pi sadece sonuçları okur.
"""
from __future__ import annotations

import logging
from typing import Callable, Optional

from picamera2 import Picamera2
from picamera2.devices import IMX500
from picamera2.devices.imx500 import NetworkIntrinsics

from config import CameraConfig
from domain.detection import Detection, LabelClassifier, ObjectCategory
from domain.geometry import BoundingBox

logger = logging.getLogger(__name__)

FrameCallback = Callable[[object], None]


class Imx500Detector:
    def __init__(
        self,
        config: CameraConfig,
        classifier: LabelClassifier,
        frame_callback: Optional[FrameCallback] = None,
    ) -> None:
        self._config = config
        self._classifier = classifier
        self._imx500 = IMX500(config.model_path)
        self._intrinsics = self._load_intrinsics()
        self._labels = self._load_labels()
        self._picam2 = Picamera2(self._imx500.camera_num)
        self._start_camera(frame_callback)
        self._frame_width, self._frame_height = self._picam2.camera_configuration()["main"]["size"]
        self._last_detections: list[Detection] = []

    def read_detections(self) -> list[Detection]:
        metadata = self._picam2.capture_metadata()
        outputs = self._imx500.get_outputs(metadata, add_batch=True)
        if outputs is None:
            return self._last_detections

        boxes, scores, classes = outputs[0][0], outputs[1][0], outputs[2][0]
        boxes = self._normalize_box_format(boxes)

        detections = []
        for box, score, class_id in zip(boxes, scores, classes):
            if score < self._config.confidence_threshold:
                continue
            detection = self._build_detection(box, float(score), int(class_id), metadata)
            if detection is not None:
                detections.append(detection)

        self._last_detections = detections
        return detections

    def close(self) -> None:
        self._picam2.stop()
        self._picam2.close()

    # --- kurulum ---------------------------------------------------------

    def _load_intrinsics(self) -> NetworkIntrinsics:
        intrinsics = self._imx500.network_intrinsics
        if not intrinsics:
            intrinsics = NetworkIntrinsics()
            intrinsics.task = "object detection"
        elif intrinsics.task != "object detection":
            raise ValueError("Seçilen model bir nesne tespit modeli değil.")

        if self._config.ignore_dash_labels is not None:
            intrinsics.ignore_dash_labels = self._config.ignore_dash_labels
        if intrinsics.labels is None and self._config.labels_path:
            with open(self._config.labels_path, encoding="utf-8") as file:
                intrinsics.labels = file.read().splitlines()
        intrinsics.update_with_defaults()
        return intrinsics

    def _load_labels(self) -> list[str]:
        labels = list(self._intrinsics.labels or [])
        if not labels:
            raise ValueError("Model etiketleri bulunamadı, config.labels_path ayarlayın.")
        if self._intrinsics.ignore_dash_labels:
            labels = [label for label in labels if label and label != "-"]
        return labels

    def _start_camera(self, frame_callback: Optional[FrameCallback]) -> None:
        camera_config = self._picam2.create_preview_configuration(
            main={"format": "XRGB8888"},  # OpenCV ile aynı BGR sırası
            controls={"FrameRate": self._intrinsics.inference_rate},
            buffer_count=12,
        )
        self._imx500.show_network_fw_progress_bar()
        if frame_callback is not None:
            self._picam2.pre_callback = frame_callback
        self._picam2.start(camera_config, show_preview=self._config.show_preview)
        if self._intrinsics.preserve_aspect_ratio:
            self._imx500.set_auto_aspect_ratio()
        logger.info("AI Camera başlatıldı, model: %s", self._config.model_path)

    # --- dönüşümler ------------------------------------------------------

    def _normalize_box_format(self, boxes):
        if self._intrinsics.bbox_normalization:
            _, input_height = self._imx500.get_input_size()
            boxes = boxes / input_height
        if self._intrinsics.bbox_order == "xy":
            boxes = boxes[:, [1, 0, 3, 2]]
        return boxes

    def _build_detection(self, box, score: float, class_id: int, metadata) -> Optional[Detection]:
        x, y, width, height = self._imx500.convert_inference_coords(
            tuple(float(v) for v in box), metadata, self._picam2
        )
        if width <= 0 or height <= 0:
            return None

        label = self._labels[class_id] if 0 <= class_id < len(self._labels) else "unknown"
        category = self._classifier.categorize(label)
        if category is ObjectCategory.OTHER:
            return None  # Araç ve canlı dışındaki nesneler yok sayılır

        normalized_box = BoundingBox.from_xywh(
            x / self._frame_width,
            y / self._frame_height,
            width / self._frame_width,
            height / self._frame_height,
        )
        return Detection(label, category, score, normalized_box)
