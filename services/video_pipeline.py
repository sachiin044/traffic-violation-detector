import cv2
import time
import logging
from typing import List, Dict, Any, Tuple
from pathlib import Path
from datetime import datetime, timezone
import uuid
import subprocess
import os

from database.mongo import MongoDB
from services.evidence import EvidenceManager
from services.pipeline import InferencePipeline
from engine.temporal_rules import TemporalRuleEngine
from engine.challan import ChallanManager
from utils.preprocess import preprocess_image, crop_region
from utils.schemas import Detection, VehicleResult, Violation, BBox
from config import INFERENCE_OUTPUTS_DIR, TWO_WHEELER_TYPES, FOUR_WHEELER_TYPES, CROP_PAD_FRACTION

logger = logging.getLogger(__name__)

class VideoInferencePipeline:
    def __init__(self, inference_pipeline: InferencePipeline):
        self.pipe = inference_pipeline
        self.db = inference_pipeline.db
        self.evidence_manager = inference_pipeline.evidence_manager
        self.temporal_engine = TemporalRuleEngine()
        self.challan_manager = ChallanManager(self.db)
        
    def process_video_task(self, task_id: str, video_path: str, camera_id: str = "CAM_001"):
        """Run video inference as a background task.
        
        Creates its own DB connection for thread-safety since SQLite connections
        cannot be safely shared across threads.
        """
        # Create a thread-local DB connection
        from database.mongo import MongoDB
        thread_db = MongoDB()
        thread_db.connect()
        
        try:
            logger.info(f"Starting video task: {task_id}")
            self.temporal_engine.reset()
            
            # Fetch Camera Config
            config = thread_db.get_camera_config(camera_id)
            if not config:
                logger.warning(f"No config for {camera_id}, using defaults")
                allowed_vector = (0, 1)
                stop_line = None
            else:
                allowed_vector = config.get("allowed_vector", (0, 1))
                stop_line = config.get("stop_line_coords")
                
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                raise ValueError(f"Could not open video {video_path}")
                
            fps = cap.get(cv2.CAP_PROP_FPS)
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            
            out_filename = f"{task_id}_out.mp4"
            out_path = INFERENCE_OUTPUTS_DIR / out_filename
            
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            writer = cv2.VideoWriter(str(out_path), fourcc, fps, (width, height))
            
            frame_idx = 0
            violations_found = 0
            
            # Track history: track_id -> list of bboxes
            track_history: Dict[int, List[Tuple[float, float, float, float]]] = {}
            # Tracks that have already been penalized to avoid duplicate evidence packages
            penalized_tracks = set()
            violation_details_list = []

            while cap.isOpened():
                ret, frame = cap.read()
                if not ret:
                    break
                    
                frame_idx += 1
                
                # 1. Track vehicles
                tracked_vehicles = self.pipe.vehicle_detector.track(frame, persist=True)
                
                # 2. Scene detections (Red light signal)
                signal_detections = self.pipe.traffic_signal_detector.detect(frame)
                is_red_light = any(d.class_name == "Red Light" and d.confidence > 0.5 for d in signal_detections)
                
                vehicle_results = []
                
                # 3. Analyze each tracked vehicle
                for v_det in tracked_vehicles:
                    tid = v_det.track_id
                    if tid is None:
                        continue
                        
                    bbox_tuple = (v_det.bbox.x1, v_det.bbox.y1, v_det.bbox.x2, v_det.bbox.y2)
                    
                    if tid not in track_history:
                        track_history[tid] = []
                    track_history[tid].append(bbox_tuple)
                    
                    # Limit history memory
                    if len(track_history[tid]) > 30:
                        track_history[tid].pop(0)
                        
                    violations: List[Violation] = []
                    
                    # Temporal Evaluation: Wrong Side Driving
                    if tid not in penalized_tracks:
                        is_wrong_side = self.temporal_engine.evaluate_wrong_side(
                            track_id=tid, 
                            trajectory=track_history[tid], 
                            allowed_vector=allowed_vector
                        )
                        if is_wrong_side:
                            violations.append(Violation(type="Wrong Side Driving", confidence=0.9))
                            
                    # Temporal Evaluation: Red Light (If we have a stop line)
                    if stop_line and tid not in penalized_tracks:
                        is_rl_viol = self.temporal_engine.evaluate_red_light(
                            track_id=tid,
                            vehicle_bbox=bbox_tuple,
                            stop_line_coords=stop_line,
                            is_red_light_active=is_red_light
                        )
                        if is_rl_viol:
                            violations.append(Violation(type="Red Light Violation", confidence=0.95))

                    # For spatial violations (Helmet, Triple, Seatbelt), we only check occasionally to save compute
                    if frame_idx % 5 == 0 and tid not in penalized_tracks:
                        crop, (cx1, cy1, cx2, cy2) = crop_region(
                            frame, int(v_det.bbox.x1), int(v_det.bbox.y1), int(v_det.bbox.x2), int(v_det.bbox.y2), pad_fraction=0.1
                        )
                        if v_det.class_name in TWO_WHEELER_TYPES:
                            h_dets = self.pipe.helmet_detector.detect(crop)
                            t_dets = self.pipe.triple_riding_detector.detect(crop)
                            violations.extend(self.pipe.rules.check_helmet(h_dets))
                            violations.extend(self.pipe.rules.check_triple_riding(t_dets))
                        elif v_det.class_name in FOUR_WHEELER_TYPES:
                            s_dets = self.pipe.seatbelt_detector.detect(crop)
                            violations.extend(self.pipe.rules.check_seatbelt(s_dets))
                            
                    # Generate Evidence Package if any violations found
                    if violations and tid not in penalized_tracks:
                        penalized_tracks.add(tid)
                        violations_found += len(violations)
                        
                        # Get Plate OCR
                        crop, (cx1, cy1, cx2, cy2) = crop_region(
                            frame, int(v_det.bbox.x1), int(v_det.bbox.y1), int(v_det.bbox.x2), int(v_det.bbox.y2), pad_fraction=0.1
                        )
                        plate_dets = self.pipe.plate_detector.detect(crop)
                        best_plate = self.pipe.plate_detector.get_best_plate(plate_dets)
                        plate_text, plate_conf = None, None
                        if best_plate:
                            plate_bbox_full = BBox(
                                x1=best_plate.bbox.x1 + cx1, y1=best_plate.bbox.y1 + cy1,
                                x2=best_plate.bbox.x2 + cx1, y2=best_plate.bbox.y2 + cy1,
                            )
                            plate_text, plate_conf = self.pipe.plate_reader.crop_and_read(
                                frame, int(plate_bbox_full.x1), int(plate_bbox_full.y1),
                                int(plate_bbox_full.x2), int(plate_bbox_full.y2)
                            )
                            
                        # Package
                        v_res = VehicleResult(
                            vehicle_id=tid, vehicle_type=v_det.class_name, bbox=v_det.bbox,
                            license_plate=plate_text, plate_confidence=plate_conf,
                            violations=violations, track_id=tid
                        )
                        
                        evidence_id = self.evidence_manager.generate_evidence_id()
                        # Use annotate_image implicitly via creating package, wait, I need to annotate image
                        from utils.annotate import annotate_image
                        annotated = annotate_image(frame.copy(), [v_res], [], evidence_id, datetime.now(timezone.utc).isoformat())
                        
                        report = self.evidence_manager.create_evidence_package(
                            original_image=frame, annotated_image=annotated,
                            vehicle_results=[v_res], scene_violations=[], processing_time_ms=50
                        )
                        report["camera_id"] = camera_id
                        report["track_id"] = tid
                        # Approximate Lat/Lon from Camera
                        report["latitude"] = config.get("latitude") if config else None
                        report["longitude"] = config.get("longitude") if config else None
                        report["location"] = config.get("location") if config else None
                        
                        thread_db.insert_evidence(report)
                        
                        violation_details_list.append({
                            "track_id": tid,
                            "vehicle_type": v_det.class_name,
                            "license_plate": plate_text,
                            "evidence_id": evidence_id,
                            "violations": [v.type for v in violations]
                        })
                        
                        # Phase 6: Auto-Challan Evaluation
                        thread_challan_mgr = ChallanManager(thread_db)
                        thread_challan_mgr.evaluate_evidence(report)
                        
                # Visualization for video out
                for v in tracked_vehicles:
                    if v.track_id in penalized_tracks:
                        # Draw red box for violator
                        x1, y1, x2, y2 = map(int, [v.bbox.x1, v.bbox.y1, v.bbox.x2, v.bbox.y2])
                        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 0, 255), 2)
                        cv2.putText(frame, f"ID:{v.track_id} VIOLATOR", (x1, y1-10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
                    elif v.track_id:
                        # Draw green box for normal tracking
                        x1, y1, x2, y2 = map(int, [v.bbox.x1, v.bbox.y1, v.bbox.x2, v.bbox.y2])
                        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 1)
                        cv2.putText(frame, f"ID:{v.track_id}", (x1, y1-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
                
                if stop_line:
                    cv2.line(frame, (int(stop_line[0]), int(stop_line[1])), (int(stop_line[2]), int(stop_line[3])), (255, 0, 255), 2)
                
                writer.write(frame)
                
                # Update task progress occasionally
                if frame_idx % 10 == 0:
                    progress = int((frame_idx / total_frames) * 100) if total_frames > 0 else 0
                    thread_db.update_video_task(task_id, {"progress": progress, "violations_found": violations_found})
                    
            cap.release()
            writer.release()
            
            # Convert video to H.264 for web compatibility
            try:
                import imageio_ffmpeg
                ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
                h264_path = str(out_path).replace(".mp4", "_h264.mp4")
                
                logger.info(f"Converting video {out_path} to H.264...")
                subprocess.run([
                    ffmpeg_exe, 
                    "-y", 
                    "-i", str(out_path),
                    "-vcodec", "libx264",
                    "-f", "mp4",
                    h264_path
                ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                
                # Replace the original file with the H.264 version
                if os.path.exists(h264_path):
                    os.replace(h264_path, str(out_path))
                    logger.info(f"Successfully converted video {out_path} to H.264.")
            except Exception as e:
                logger.warning(f"Could not convert video to H.264 (will serve as is): {e}")
            
            # Final Update
            import json
            thread_db.update_video_task(task_id, {
                "status": "completed",
                "progress": 100,
                "violations_found": violations_found,
                "violation_details": json.dumps(violation_details_list),
                "processed_video_path": f"/outputs/{out_filename}",
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
            logger.info(f"Completed video task: {task_id}")
            
        except Exception as e:
            logger.error(f"Error processing video task {task_id}: {str(e)}", exc_info=True)
            try:
                thread_db.update_video_task(task_id, {"status": "error", "error": str(e)})
            except Exception:
                logger.error(f"Failed to update error status for task {task_id}")
        finally:
            thread_db.close()

