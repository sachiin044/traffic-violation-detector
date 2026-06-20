import numpy as np
from typing import Dict, List, Optional, Tuple

class TemporalRuleEngine:
    def __init__(self):
        # State machine for red light: BEFORE_LINE -> ON_LINE -> AFTER_LINE
        self.red_light_states: Dict[int, str] = {}
        
    def _get_bbox_center(self, bbox: Tuple[float, float, float, float]) -> Tuple[float, float]:
        x1, y1, x2, y2 = bbox
        return ((x1 + x2) / 2, (y1 + y2) / 2)
        
    def evaluate_wrong_side(
        self, 
        track_id: int, 
        trajectory: List[Tuple[float, float, float, float]], 
        allowed_vector: Tuple[float, float]
    ) -> bool:
        """
        Evaluate if a vehicle is driving on the wrong side.
        Uses the last 10 frames to compute a smoothed average motion vector.
        """
        if len(trajectory) < 10:
            return False
            
        recent = trajectory[-10:]
        
        # Calculate moving average vector
        start_center = self._get_bbox_center(recent[0])
        end_center = self._get_bbox_center(recent[-1])
        
        dx = end_center[0] - start_center[0]
        dy = end_center[1] - start_center[1]
        
        # Normalize motion vector
        magnitude = np.sqrt(dx**2 + dy**2)
        if magnitude < 5.0: # Minimum movement threshold to avoid noise
            return False
            
        motion_vector = (dx / magnitude, dy / magnitude)
        
        # Calculate dot product with allowed vector
        # If dot product is strongly negative, it's moving in the opposite direction
        dot_product = motion_vector[0] * allowed_vector[0] + motion_vector[1] * allowed_vector[1]
        
        return dot_product < -0.5  # Cosine similarity threshold for "opposite"

    def evaluate_red_light(
        self, 
        track_id: int, 
        vehicle_bbox: Tuple[float, float, float, float], 
        stop_line_coords: Tuple[float, float, float, float],
        is_red_light_active: bool
    ) -> bool:
        """
        State-machine based Red Light violation evaluation.
        Requires state transition: BEFORE_LINE -> AFTER_LINE while RED.
        """
        # Unpack
        vx1, vy1, vx2, vy2 = vehicle_bbox
        sx1, sy1, sx2, sy2 = stop_line_coords
        
        v_bottom = vy2
        line_y = (sy1 + sy2) / 2 # Simplify stop line to a horizontal line
        
        # Current position relative to line
        is_before = v_bottom < (line_y - 20)
        is_after = v_bottom > (line_y + 20)
        is_on_line = not is_before and not is_after
        
        current_state = self.red_light_states.get(track_id, "BEFORE_LINE")
        
        # State transitions
        if current_state == "BEFORE_LINE":
            if is_on_line:
                self.red_light_states[track_id] = "ON_LINE"
            elif is_after:
                # Fast crossing
                self.red_light_states[track_id] = "AFTER_LINE"
                return is_red_light_active
                
        elif current_state == "ON_LINE":
            if is_after:
                self.red_light_states[track_id] = "AFTER_LINE"
                return is_red_light_active
                
        return False
        
    def reset(self):
        """Reset state between videos."""
        self.red_light_states.clear()
