"""
SQLite database connection and operations.
This completely replaces the MongoDB Atlas connection for local robustness.
It perfectly mimics the previous MongoDB interface so the rest of the app doesn't break.
"""

import os
import json
import sqlite3
import logging
import uuid
from typing import List, Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

DB_PATH = os.path.join(os.path.dirname(__file__), "violations.db")


class MongoDB:
    """
    SQLite wrapper that mimics the MongoDB evidence storage and analytics.
    Keeps the name 'MongoDB' so imports don't break across the project!
    """

    def __init__(self, uri: str = "sqlite"):
        self.db_path = DB_PATH
        self.conn = None

    def connect(self) -> None:
        """Establish connection to local SQLite database and create tables."""
        try:
            # check_same_thread=False is needed for FastAPI concurrent requests
            self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self.conn.row_factory = sqlite3.Row  # To return dict-like rows
            
            cursor = self.conn.cursor()
            
            # Evidence Table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS evidence (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                evidence_id TEXT UNIQUE,
                timestamp TEXT,
                plate_number TEXT,
                vehicle_type TEXT,
                confidence REAL,
                thumbnail_path TEXT,
                original_image_path TEXT,
                latitude REAL,
                longitude REAL,
                location TEXT,
                camera_id TEXT,
                violations TEXT  -- JSON array
            )
            ''')
            
            # Video Tasks Table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS video_tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id TEXT UNIQUE,
                filename TEXT,
                status TEXT,
                progress INTEGER,
                violations_found INTEGER,
                violation_details TEXT,
                error TEXT,
                processed_video_path TEXT,
                timestamp TEXT
            )
            ''')
            
            # Camera Configs Table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS camera_configs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                camera_id TEXT UNIQUE,
                config_json TEXT
            )
            ''')
            
            # Challans Table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS challans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                challan_id TEXT UNIQUE,
                evidence_id TEXT,
                status TEXT,
                fine_amount REAL,
                plate_number TEXT,
                timestamp TEXT,
                created_at TEXT,
                violation_type TEXT,
                vehicle_type TEXT,
                confidence REAL
            )
            ''')
            
            # Create indexes for fast searching
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_evidence_ts ON evidence(timestamp)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_evidence_plate ON evidence(plate_number)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_challan_status ON challans(status)')
            
            self.conn.commit()
            logger.info(f"[SQLite] Connected successfully to local database at {self.db_path}")
        except Exception as e:
            logger.error(f"[SQLite] Connection failed: {e}")
            raise

    def _dict_factory(self, row) -> Dict[str, Any]:
        """Convert a sqlite3.Row to a dictionary, unpacking JSON strings."""
        d = dict(row)
        if 'violations' in d and isinstance(d['violations'], str):
            try:
                d['violations'] = json.loads(d['violations'])
            except:
                d['violations'] = []
        if 'config_json' in d and isinstance(d['config_json'], str):
            try:
                d.update(json.loads(d['config_json']))
                del d['config_json']
            except:
                pass
        return d

    def insert_evidence(self, evidence_data: Dict[str, Any]) -> str:
        """Insert a single evidence package record."""
        cursor = self.conn.cursor()
        
        # Serialize list to JSON
        violations_json = json.dumps(evidence_data.get('violations', []))
        
        cursor.execute('''
        INSERT INTO evidence (
            evidence_id, timestamp, plate_number, vehicle_type, confidence, 
            thumbnail_path, original_image_path, latitude, longitude, 
            location, camera_id, violations
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            evidence_data.get('evidence_id'),
            evidence_data.get('timestamp'),
            evidence_data.get('plate_number'),
            evidence_data.get('vehicle_type'),
            evidence_data.get('confidence'),
            evidence_data.get('thumbnail_path'),
            evidence_data.get('original_image_path') or evidence_data.get('image_path'),
            evidence_data.get('latitude'),
            evidence_data.get('longitude'),
            evidence_data.get('location'),
            evidence_data.get('camera_id'),
            violations_json
        ))
        self.conn.commit()
        return str(cursor.lastrowid)

    def get_evidence(self, evidence_id: str) -> Optional[Dict[str, Any]]:
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM evidence WHERE evidence_id = ?', (evidence_id,))
        row = cursor.fetchone()
        return self._dict_factory(row) if row else None

    def search_evidence(
        self,
        limit: int = 100,
        skip: int = 0,
        plate_number: Optional[str] = None,
        violation_type: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        min_confidence: Optional[float] = None,
    ) -> Dict[str, Any]:
        cursor = self.conn.cursor()
        
        query = 'SELECT * FROM evidence WHERE 1=1'
        count_query = 'SELECT COUNT(*) FROM evidence WHERE 1=1'
        params = []
        
        if plate_number:
            query += ' AND plate_number LIKE ?'
            count_query += ' AND plate_number LIKE ?'
            params.append(f'%{plate_number}%')
            
        if violation_type:
            query += ' AND violations LIKE ?'
            count_query += ' AND violations LIKE ?'
            params.append(f'%"{violation_type}"%')
            
        if date_from:
            query += ' AND timestamp >= ?'
            count_query += ' AND timestamp >= ?'
            params.append(date_from)
            
        if date_to:
            query += ' AND timestamp <= ?'
            count_query += ' AND timestamp <= ?'
            params.append(date_to)
            
        if min_confidence is not None:
            query += ' AND confidence >= ?'
            count_query += ' AND confidence >= ?'
            params.append(min_confidence)
            
        # Get total count
        cursor.execute(count_query, params)
        total = cursor.fetchone()[0]
        
        # Get paginated records
        query += ' ORDER BY timestamp DESC LIMIT ? OFFSET ?'
        params.extend([limit, skip])
        
        cursor.execute(query, params)
        records = [self._dict_factory(row) for row in cursor.fetchall()]
        
        return {"total": total, "records": records}

    def get_dashboard_summary(self) -> Dict[str, int]:
        cursor = self.conn.cursor()
        
        cursor.execute('SELECT COUNT(*) FROM evidence')
        total_violations = cursor.fetchone()[0]
        
        cursor.execute('SELECT violations FROM evidence')
        rows = cursor.fetchall()
        
        summary = {
            "total": total_violations,
            "helmet": 0,
            "seatbelt": 0,
            "triple_riding": 0,
            "red_light": 0,
            "illegal_parking": 0
        }
        
        key_mapping = {
            "Helmet Non Compliance": "helmet",
            "Seatbelt Non Compliance": "seatbelt",
            "Triple Riding": "triple_riding",
            "Red Light Violation": "red_light",
            "Illegal Parking": "illegal_parking"
        }
        
        for row in rows:
            v_str = row['violations']
            if not v_str: continue
            try:
                v_list = json.loads(v_str)
                for v in v_list:
                    if v in key_mapping:
                        summary[key_mapping[v]] += 1
            except:
                pass
                
        return summary

    def get_top_plates(self, limit: int = 5) -> List[Dict[str, Any]]:
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT plate_number, COUNT(*) as offenses 
            FROM evidence 
            WHERE plate_number IS NOT NULL AND plate_number != ''
            GROUP BY plate_number 
            ORDER BY offenses DESC 
            LIMIT ?
        ''', (limit,))
        
        return [{"plate_number": row['plate_number'], "offenses": row['offenses']} for row in cursor.fetchall()]

    # ── Phase 5: Video Tasks & Camera Configs ────────────────────────────────

    def get_camera_config(self, camera_id: str) -> Optional[Dict[str, Any]]:
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM camera_configs WHERE camera_id = ?', (camera_id,))
        row = cursor.fetchone()
        return self._dict_factory(row) if row else None

    def create_video_task(self, task_id: str, filename: str) -> None:
        cursor = self.conn.cursor()
        cursor.execute('''
        INSERT INTO video_tasks (task_id, filename, status, progress, violations_found)
        VALUES (?, ?, ?, ?, ?)
        ''', (task_id, filename, "processing", 0, 0))
        self.conn.commit()

    def update_video_task(self, task_id: str, update_data: Dict[str, Any]) -> None:
        if not update_data: return
        cursor = self.conn.cursor()
        
        set_clauses = []
        params = []
        for k, v in update_data.items():
            set_clauses.append(f"{k} = ?")
            params.append(v)
            
        params.append(task_id)
        
        query = f"UPDATE video_tasks SET {', '.join(set_clauses)} WHERE task_id = ?"
        cursor.execute(query, params)
        self.conn.commit()

    def get_video_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM video_tasks WHERE task_id = ?', (task_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

    # ── Phase 5: Advanced Analytics ──────────────────────────────────────────

    def get_hotspots(self) -> List[Dict[str, Any]]:
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT camera_id, location, latitude, longitude, COUNT(*) as total_violations
            FROM evidence
            WHERE camera_id IS NOT NULL
            GROUP BY camera_id, location, latitude, longitude
            ORDER BY total_violations DESC
            LIMIT 20
        ''')
        return [dict(row) for row in cursor.fetchall()]

    def get_daily_trends(self) -> List[Dict[str, Any]]:
        cursor = self.conn.cursor()
        cursor.execute('SELECT timestamp, violations FROM evidence')
        rows = cursor.fetchall()
        
        trends_map = {}
        key_mapping = {
            "Helmet Non Compliance": "helmet",
            "Seatbelt Non Compliance": "seatbelt",
            "Triple Riding": "triple_riding",
            "Red Light Violation": "red_light",
            "Illegal Parking": "illegal_parking",
            "Wrong Side Driving": "wrong_side"
        }
        
        for row in rows:
            ts = row['timestamp']
            if not ts: continue
            date = ts[:10]  # YYYY-MM-DD
            
            if date not in trends_map:
                trends_map[date] = {"date": date}
                
            v_str = row['violations']
            if not v_str: continue
            try:
                v_list = json.loads(v_str)
                for v in v_list:
                    mapped_key = key_mapping.get(v, "other")
                    trends_map[date][mapped_key] = trends_map[date].get(mapped_key, 0) + 1
            except:
                pass
                
        trend_list = list(trends_map.values())
        trend_list.sort(key=lambda x: x["date"])
        return trend_list

    # ── Phase 6: Enforcement & Challans ──────────────────────────────────────

    def insert_challan(self, challan_data: Dict[str, Any]) -> str:
        cursor = self.conn.cursor()
        cursor.execute('''
        INSERT INTO challans (
            challan_id, evidence_id, status, fine_amount, plate_number, 
            timestamp, created_at, violation_type, vehicle_type, confidence
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            challan_data.get('challan_id'),
            challan_data.get('evidence_id'),
            challan_data.get('status'),
            challan_data.get('fine_amount'),
            challan_data.get('plate_number'),
            challan_data.get('timestamp'),
            challan_data.get('created_at'),
            challan_data.get('violation_type'),
            challan_data.get('vehicle_type'),
            challan_data.get('confidence')
        ))
        self.conn.commit()
        return str(cursor.lastrowid)

    def get_challan(self, challan_id: str) -> Optional[Dict[str, Any]]:
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM challans WHERE challan_id = ?', (challan_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

    def update_challan_status(self, challan_id: str, new_status: str) -> bool:
        cursor = self.conn.cursor()
        cursor.execute('UPDATE challans SET status = ? WHERE challan_id = ?', (new_status, challan_id))
        self.conn.commit()
        return cursor.rowcount > 0

    def search_challans(self, limit: int = 50, skip: int = 0, status: Optional[str] = None, plate_number: Optional[str] = None) -> Dict[str, Any]:
        cursor = self.conn.cursor()
        
        query = 'SELECT * FROM challans WHERE 1=1'
        count_query = 'SELECT COUNT(*) FROM challans WHERE 1=1'
        params = []
        
        if status:
            query += ' AND status = ?'
            count_query += ' AND status = ?'
            params.append(status)
            
        if plate_number:
            query += ' AND plate_number LIKE ?'
            count_query += ' AND plate_number LIKE ?'
            params.append(f'%{plate_number}%')
            
        cursor.execute(count_query, params)
        total = cursor.fetchone()[0]
        
        query += ' ORDER BY created_at DESC LIMIT ? OFFSET ?'
        params.extend([limit, skip])
        
        cursor.execute(query, params)
        records = [dict(row) for row in cursor.fetchall()]
        
        return {"total": total, "records": records}

    def get_enforcement_demo_stats(self) -> Dict[str, int]:
        cursor = self.conn.cursor()
        
        stats = {
            "total_challans": 0,
            "pending": 0,
            "review_required": 0,
            "generated": 0,
            "issued": 0,
            "paid": 0,
            "disputed": 0,
            "estimated_fines": 0,
            "total_violations": 0
        }
        
        cursor.execute('SELECT COUNT(*) FROM evidence')
        stats["total_violations"] = cursor.fetchone()[0]
        
        cursor.execute('SELECT status, COUNT(*), SUM(fine_amount) FROM challans GROUP BY status')
        for row in cursor.fetchall():
            status = row[0]
            count = row[1]
            total_fine = row[2] or 0
            
            stats["total_challans"] += count
            if status:
                status_lower = status.lower()
                stats[status_lower] = count
                if status != 'DISPUTED':
                    stats["estimated_fines"] += total_fine
                    
        return stats

    def close(self) -> None:
        if self.conn:
            self.conn.close()
            logger.info("[SQLite] Connection closed")
