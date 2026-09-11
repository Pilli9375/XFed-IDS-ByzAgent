"""Patch server_app.py to persist a global checkpoint every round.

Chat 04 Pre-check A found only best/last checkpoints were saved, so
intermediate global checkpoints did not exist and offline silo-local
reconstruction was impossible. This adds a per-round checkpoint save
inside global_evaluate -- the function already receives `arrays` and
`server_round` every round, so no new API surface is touched.

Run from project root: python tools/apply_checkpoint_patch.py
"""
from pathlib import Path
import shutil

TARGET = Path("federated/xfed_federated/server_app.py")
BACKUP = TARGET.with_suffix(".py.bak")

OLD_1 = '    out_dir.mkdir(parents=True, exist_ok=True)\n'
NEW_1 = (
    '    out_dir.mkdir(parents=True, exist_ok=True)\n'
    '\n'
    '    # Chat 04 Pre-check A: only best/last were saved previously, so\n'
    '    # intermediate global checkpoints did not exist and silo-local\n'
    '    # reconstruction was impossible. Every round now lands on disk.\n'
    '    round_ckpt_dir = out_dir / "round_checkpoints"\n'
    '    round_ckpt_dir.mkdir(parents=True, exist_ok=True)\n'
)

OLD_2 = (
    '        model = build_model(model_cfg, seed=seed, device=DEVICE)\n'
    '        model.load_state_dict(arrays.to_torch_state_dict())\n'
    '        Xv = torch.from_numpy(X_val.copy()).to(DEVICE)\n'
)
NEW_2 = (
    '        model = build_model(model_cfg, seed=seed, device=DEVICE)\n'
    '        model.load_state_dict(arrays.to_torch_state_dict())\n'
    '        torch.save(model.state_dict(),\n'
    '                   round_ckpt_dir / f"round_{server_round:03d}.pt")\n'
    '        Xv = torch.from_numpy(X_val.copy()).to(DEVICE)\n'
)


def main() -> int:
    if not TARGET.exists():
        print(f"NOT FOUND: {TARGET.resolve()}")
        return 1
    text = TARGET.read_text()

    if OLD_1 not in text:
        print("OLD_1 pattern not found. File may already be patched, or has "
              "drifted from the version I was shown. No changes made.")
        return 1
    if OLD_2 not in text:
        print("OLD_2 pattern not found. File may already be patched, or has "
              "drifted from the version I was shown. No changes made.")
        return 1

    shutil.copy(TARGET, BACKUP)
    text = text.replace(OLD_1, NEW_1, 1)
    text = text.replace(OLD_2, NEW_2, 1)
    TARGET.write_text(text)

    print(f"Patched: {TARGET}")
    print(f"Backup saved: {BACKUP}")
    print("\nSanity check: the file should now have a 'round_checkpoints' "
          "block right after out_dir.mkdir(), and a torch.save(...) call "
          "right after model.load_state_dict(...) inside global_evaluate.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
