"""
OpenAI vision reader for license plate text only.

This module is deliberately isolated from the rest of the violation pipeline.
It is called only by the license-plate step when OPENAI_API_KEY is present.
"""

from __future__ import annotations

import base64
import json
import logging
import os
import urllib.error
import urllib.request
from typing import Optional, Tuple

import cv2
import numpy as np

from config import OPENAI_PLATE_MODEL, OPENAI_PLATE_TIMEOUT_SECONDS

logger = logging.getLogger(__name__)


class OpenAIPlateReader:
    """Reads visible license plate text with an OpenAI vision model."""

    API_URL = "https://api.openai.com/v1/responses"

    def __init__(self) -> None:
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.model = OPENAI_PLATE_MODEL

    @property
    def is_available(self) -> bool:
        return bool(self.api_key)

    @staticmethod
    def _image_data_url(image: np.ndarray) -> Optional[str]:
        if image is None or image.size == 0:
            return None

        ok, encoded = cv2.imencode(".jpg", image, [int(cv2.IMWRITE_JPEG_QUALITY), 90])
        if not ok:
            return None

        b64 = base64.b64encode(encoded.tobytes()).decode("ascii")
        return f"data:image/jpeg;base64,{b64}"

    @staticmethod
    def _extract_output_text(response: dict) -> str:
        if isinstance(response.get("output_text"), str):
            return response["output_text"]

        chunks = []
        for item in response.get("output", []):
            for content in item.get("content", []):
                if content.get("type") in {"output_text", "text"}:
                    text = content.get("text")
                    if isinstance(text, str):
                        chunks.append(text)
        return "\n".join(chunks)

    @staticmethod
    def _parse_plate_json(text: str) -> Tuple[Optional[str], float]:
        if not text:
            return None, 0.0

        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1 or end <= start:
            return None, 0.0

        try:
            data = json.loads(text[start : end + 1])
        except json.JSONDecodeError:
            return None, 0.0

        plate = data.get("license_plate")
        if not isinstance(plate, str):
            return None, 0.0

        cleaned = "".join(ch for ch in plate.upper() if ch.isalnum())
        if len(cleaned) < 4:
            return None, 0.0

        confidence = data.get("confidence", 0.0)
        try:
            confidence = max(0.0, min(1.0, float(confidence)))
        except (TypeError, ValueError):
            confidence = 0.0

        return cleaned, confidence

    def read_plate(self, image: np.ndarray) -> Tuple[Optional[str], float]:
        """Return (plate_text, confidence), or (None, 0.0) on any failure."""
        if not self.is_available:
            return None, 0.0

        data_url = self._image_data_url(image)
        if not data_url:
            return None, 0.0

        payload = {
            "model": self.model,
            "input": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_text",
                            "text": (
                                "Read the visible vehicle license plate number in this image. "
                                "Return only compact JSON with keys: visible, license_plate, confidence. "
                                "If no license plate text is clearly visible, use "
                                '{"visible": false, "license_plate": null, "confidence": 0}. '
                                "Do not guess hidden or blurry characters."
                            ),
                        },
                        {
                            "type": "input_image",
                            "image_url": data_url,
                            "detail": "high",
                        },
                    ],
                }
            ],
            "max_output_tokens": 80,
        }

        request = urllib.request.Request(
            self.API_URL,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(
                request,
                timeout=OPENAI_PLATE_TIMEOUT_SECONDS,
            ) as response:
                body = response.read().decode("utf-8")
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            logger.warning(f"[OpenAI Plate OCR] Request failed: {exc}")
            return None, 0.0

        try:
            response_data = json.loads(body)
        except json.JSONDecodeError:
            logger.warning("[OpenAI Plate OCR] Non-JSON API response")
            return None, 0.0

        plate, confidence = self._parse_plate_json(self._extract_output_text(response_data))
        if plate:
            logger.info(f"[OpenAI Plate OCR] Read plate: {plate} (conf: {confidence:.2f})")
        return plate, confidence
