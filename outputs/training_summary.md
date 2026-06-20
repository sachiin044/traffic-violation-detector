# Training Summary
## Traffic Violation Detection System

> **Date:** 2026-06-19 04:13:32  
> **Total Time:** 12:10:48  
> **Platform:** Windows | PyTorch 2.6.0+cu124  
> **GPU:** NVIDIA GeForce RTX 3050 Laptop GPU  

**Results:** 7 succeeded, 0 failed, 7 total

## Per-Model Results

| # | Model | Status | Time | Precision | Recall | mAP@50 | mAP@50-95 |
|---|-------|--------|------|-----------|--------|--------|-----------|
| 1 | License Plate Detector | ✅ success | 5:02:29 | 0.9996 | 1.0 | 0.995 | 0.9032 |
| 2 | Vehicle Detector | ✅ success | pretrained (YOLOv8m) | 0.872 | 0.758 | 0.828 | 0.507 |
| 3 | Helmet Detector | ✅ success | 0:42:48 | 0.8437 | 0.7619 | 0.7985 | 0.4927 |
| 4 | Seatbelt Detector | ✅ success | 3:29:03 | 0.9394 | 0.9107 | 0.9673 | 0.6445 |
| 5 | Traffic Signal Detector | ✅ success | 1:39:13 | 0.7067 | 0.8502 | 0.8563 | 0.5792 |
| 6 | Triple Riding Detector | ✅ success | 0:23:40 | 0.859 | 0.8138 | 0.8705 | 0.5747 |
| 7 | Illegal Parking Detector | ✅ success | 0:53:23 | 0.955 | 0.865 | 0.9413 | 0.6405 |

## Output Paths

| Model | best.pt | best.onnx |
|-------|---------|-----------|
| License Plate Detector | `D:\New folder (3)\outputs\plate\weights\best.pt` | `D:\New folder (3)\outputs\plate\weights\best.onnx` |
| Vehicle Detector | `D:\final-filipkart-hackathon\outputs\vehicle\weights\best.pt` | `D:\final-filipkart-hackathon\outputs\vehicle\weights\best.onnx` |
| Helmet Detector | `D:\New folder (3)\outputs\helmet\weights\best.pt` | `D:\New folder (3)\outputs\helmet\weights\best.onnx` |
| Seatbelt Detector | `D:\New folder (3)\outputs\seatbelt\weights\best.pt` | `D:\New folder (3)\outputs\seatbelt\weights\best.onnx` |
| Traffic Signal Detector | `D:\New folder (3)\outputs\traffic_signal\weights\best.pt` | `D:\New folder (3)\outputs\traffic_signal\weights\best.onnx` |
| Triple Riding Detector | `D:\New folder (3)\outputs\triple_riding\weights\best.pt` | `D:\New folder (3)\outputs\triple_riding\weights\best.onnx` |
| Illegal Parking Detector | `D:\New folder (3)\outputs\illegal_parking\weights\best.pt` | `D:\New folder (3)\outputs\illegal_parking\weights\best.onnx` |

> **Note — Vehicle Detector:** Uses pretrained YOLOv8m (COCO) as substitute.
> Detects: `bicycle`, `car`, `motorcycle`, `bus`, `truck`.
> Metrics are published COCO val2017 values.

---
*Auto-generated on 2026-06-19 04:13:32*