# Vehicle Detection Training Summary

**Auto-generated on 2026-06-20 03:48:37**

## Results
| Metric | Value |
|--------|-------|
| mAP50 | 0.8807 |
| mAP50-95 | 0.7191 |

## Model
| File | Path |
|------|------|
| ONNX | D:/train/outputs/vehicle/weights/best.onnx |
| Size | 10.1 MB |

## Training
| Detail | Value |
|--------|-------|
| Duration | 2h 35m 58s |
| Image Size | 640 |
| Dataset | indian-driving-dataset |

## Saved Artifacts
- results.csv
- results.png
- confusion_matrix.png
- confusion_matrix_normalized.png
- best.onnx

## Commands
- Predict: yolo predict task=detect model=D:/train/outputs/vehicle/weights/best.onnx imgsz=640
- Validate: yolo val task=detect model=D:/train/outputs/vehicle/weights/best.onnx imgsz=640
