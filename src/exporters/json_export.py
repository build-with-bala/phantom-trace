"""JSON report export."""

import json
from datetime import datetime
from pathlib import Path
from src.models import PersonProfile


def export_json(profile: PersonProfile, output_path: str):
    report = {
        "phantom_trace": {"version": "1.0.0", "timestamp": datetime.now().isoformat()},
        "target": profile.to_dict() if hasattr(profile, "to_dict") else {"query": profile.query},
    }
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(report, f, indent=2, default=str)
