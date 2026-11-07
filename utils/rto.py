"""
Look up the Regional Transport Office (RTO) a vehicle is registered with,
from the state + district code at the start of an Indian number plate:

    UP93AB1234  ->  UP 93  ->  Jhansi, Uttar Pradesh

This is where the vehicle is REGISTERED, not where an offence happened.
Data: config/rto_codes.json (built from the RTO mapping list in
ClimateDot-Code/rto-locations-india on GitHub, updated Oct 2026).
"""

import json
import logging
import re
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

_DATA_PATH = Path(__file__).resolve().parent.parent / "config" / "rto_codes.json"


@lru_cache(maxsize=1)
def _load():
    try:
        with open(_DATA_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("codes", {}), data.get("_aliases", {})
    except Exception as e:
        logger.error(f"[RTO] Could not load {_DATA_PATH}: {e}")
        return {}, {}


def rto_code_from_plate(plate: Optional[str]) -> Optional[str]:
    """'UP93AB1234' -> 'UP93', 'DL1CAF1234' -> 'DL01'. None for BH-series or unreadable plates."""
    p = re.sub(r"[^A-Z0-9]", "", str(plate or "").upper())
    if re.match(r"^\d{2}BH\d", p):
        return None  # Bharat series plates have no home RTO
    m = re.match(r"^([A-Z]{2})(\d{1,2})(?=[A-Z])", p) or re.match(r"^([A-Z]{2})(\d{2})", p)
    if not m:
        return None
    return f"{m.group(1)}{int(m.group(2)):02d}"


def lookup_rto(plate: Optional[str]) -> Optional[Dict[str, Any]]:
    """Registration office for a plate, or None if the code isn't in the list."""
    code = rto_code_from_plate(plate)
    if not code:
        return None
    codes, aliases = _load()
    entry = codes.get(code)
    if entry is None and code[:2] in aliases:          # e.g. TS09 -> TG09, OR02 -> OD02
        entry = codes.get(aliases[code[:2]] + code[2:])
    if entry is None:
        return None
    area = entry.get("office") or entry.get("district")
    return {
        "code": code,
        "display_code": f"{code[:2]} {code[2:]}",
        "office": entry.get("office"),
        "district": entry.get("district"),
        "state": entry.get("state"),
        "latitude": entry.get("lat"),
        "longitude": entry.get("lon"),
        "place": f"{area}, {entry.get('state')}" if entry.get("state") else area,
    }
