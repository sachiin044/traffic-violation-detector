"""
Seed script to populate mock camera configurations into MongoDB.
Run this once to setup the `camera_configs` collection.
"""

import sys
from pathlib import Path

# Ensure root path is in sys.path
root_dir = Path(__file__).resolve().parent.parent
sys.path.append(str(root_dir))

from database.mongo import MongoDB
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

MOCK_CAMERAS = [
    {
        "camera_id": "CAM_001",
        "location": "Main Junction North",
        "latitude": 20.2961,
        "longitude": 85.8245,
        "allowed_direction": "north_to_south", # Example vector mapping would be needed
        "allowed_vector": (0, 1), # x=0, y=1 (moving down the frame)
        "stop_line_coords": [100, 400, 800, 420], # [x1, y1, x2, y2]
    },
    {
        "camera_id": "CAM_002",
        "location": "Highway A Exit",
        "latitude": 20.3012,
        "longitude": 85.8123,
        "allowed_direction": "west_to_east",
        "allowed_vector": (1, 0), # x=1, y=0 (moving right across frame)
        "stop_line_coords": None, # No stop line here
    }
]

def seed_cameras():
    db = MongoDB()
    db.connect()
    
    collection = db.db["camera_configs"]
    
    # Clear existing
    collection.delete_many({})
    
    # Insert new
    collection.insert_many(MOCK_CAMERAS)
    logger.info(f"Successfully seeded {len(MOCK_CAMERAS)} camera configurations.")
    
    db.close()

if __name__ == "__main__":
    seed_cameras()
