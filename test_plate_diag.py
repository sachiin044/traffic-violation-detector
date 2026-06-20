"""
Quick test to verify the direct OCR scan works on a vehicle crop.
"""
import cv2
import numpy as np
import logging

logging.basicConfig(level=logging.INFO, format="%(name)s | %(message)s")

from ocr.plate_reader import PlateReader

reader = PlateReader()
reader.load()

# Create a synthetic test with plate-like text
# Use bus.jpg as a test image
img = cv2.imread("bus.jpg")
if img is not None:
    print("Testing direct_ocr_scan on bus.jpg (likely no Indian plate)...")
    text, conf, bbox = reader.direct_ocr_scan(img)
    print(f"  Result: text={text}, conf={conf:.2f}, bbox={bbox}")
    print()

# Test on a blank image with text drawn on it (simulate a plate)
print("Testing direct_ocr_scan on synthetic plate image...")
synth = np.ones((200, 400, 3), dtype=np.uint8) * 255
cv2.putText(synth, "TN20DD8016", (50, 120), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 0, 0), 3)
text, conf, bbox = reader.direct_ocr_scan(synth)
print(f"  Result: text={text}, conf={conf:.2f}, bbox={bbox}")

print("\nDone!")
