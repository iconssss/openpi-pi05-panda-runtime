from __future__ import annotations
import json
from pathlib import Path
from openpi_robot_runtime.stage22 import audit,generate
out=Path('artifacts/stage22');out.mkdir(parents=True,exist_ok=True); rows=generate(); report={'seed':20260822,'rows':len(rows),'audit':audit(rows),'mock_state_only_pair_discrimination':0.0,'gates_pass':all(v['constant_cosine_abs']<=.1 and v['max_within_group_state_delta']<=1e-12 and v['nearest_neighbor_condition_accuracy_upper_bound']<=1/6+.05 for v in audit(rows).values())};(out/'audit.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
