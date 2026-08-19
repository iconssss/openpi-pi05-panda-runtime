"""Train bounded residual adapters from frozen-pi05 diagnostic data."""
from __future__ import annotations
import json
from pathlib import Path
import torch

DATA = Path('/root/shared-nvme/openpi-robot-runtime/results/stage18_adapter_data/pilot_1024_seed_20260820.json')
OUT = Path('/root/shared-nvme/openpi-robot-runtime/results/stage18_adapter_training')

class Adapter(torch.nn.Module):
    def __init__(self) -> None:
        super().__init__()
        self.net = torch.nn.Sequential(torch.nn.Linear(14, 64), torch.nn.ReLU(), torch.nn.Linear(64, 64), torch.nn.ReLU(), torch.nn.Linear(64, 7), torch.nn.Tanh())
    def forward(self, value: torch.Tensor) -> torch.Tensor:
        return self.net(value)

def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    rows = [row for row in json.loads(DATA.read_text())['rows'] if row['safe_hold'] is None]
    features = torch.tensor([row['joint_position'] + row['raw_pi05_arm_action'] for row in rows], dtype=torch.float32)
    target = torch.tensor([[o-a for o, a in zip(row['dls_oracle_velocity'], row['raw_pi05_arm_action'], strict=True)] for row in rows], dtype=torch.float32).clamp(-1, 1)
    generator = torch.Generator().manual_seed(20260820)
    permutation = torch.randperm(len(rows), generator=generator)
    cut = int(0.8 * len(rows)); train_i, val_i = permutation[:cut], permutation[cut:]
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    summary = {'scope': 'three-seed frozen-pi05 residual-adapter training on diagnostic-distribution data only', 'samples': len(rows), 'train_samples': len(train_i), 'validation_samples': len(val_i), 'device': str(device), 'seeds': []}
    for seed in (11, 22, 33):
        torch.manual_seed(seed); model = Adapter().to(device); opt = torch.optim.AdamW(model.parameters(), lr=1e-3, weight_decay=1e-4)
        x, y = features.to(device), target.to(device)
        for _ in range(800):
            pred = model(x[train_i]); loss = torch.nn.functional.mse_loss(pred, y[train_i]); opt.zero_grad(); loss.backward(); torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0); opt.step()
        with torch.no_grad():
            train_mse = torch.nn.functional.mse_loss(model(x[train_i]), y[train_i]).item(); val_mse = torch.nn.functional.mse_loss(model(x[val_i]), y[val_i]).item()
        checkpoint = OUT / f'residual_adapter_seed_{seed}.pt'; torch.save({'state_dict': model.cpu().state_dict(), 'feature_order': ['panda_joint_position_x7', 'raw_pi05_arm_action_x7'], 'residual_target': 'dls_oracle_velocity_minus_raw_pi05_action', 'seed': seed}, checkpoint)
        summary['seeds'].append({'seed': seed, 'train_mse': train_mse, 'validation_mse': val_mse, 'checkpoint': str(checkpoint)})
    (OUT / 'training_report.json').write_text(json.dumps(summary, indent=2)); print(json.dumps(summary, indent=2))
if __name__ == '__main__': main()
