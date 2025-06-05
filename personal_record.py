import json
import os
from typing import Tuple

def update_personal_record(player: str, speed_kmh: float, file_path: str = "personal_records.json") -> Tuple[float, bool]:
    """Update personal record for a player.

    Args:
        player: Player name.
        speed_kmh: Recorded speed in km/h.
        file_path: Path to the record file.

    Returns:
        Tuple of the best recorded speed after the update and a boolean
        indicating whether a new record was set.
    """
    if os.path.exists(file_path):
        with open(file_path, "r") as f:
            records = json.load(f)
    else:
        records = {}

    current_best = records.get(player, 0.0)
    new_record = speed_kmh > current_best
    if new_record:
        records[player] = speed_kmh
        with open(file_path, "w") as f:
            json.dump(records, f, indent=2)
        current_best = speed_kmh

    return current_best, new_record
