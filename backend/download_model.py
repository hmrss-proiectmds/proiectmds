"""
Download the ChessBot HuggingFace model to backend/models/chessbot.

Usage:
    python download_model.py

This downloads ~140MB of model weights from huggingface.co/Maxlegrec/ChessBot.
The model is a transformer trained on 750M chess positions from the LCZero project.
It predicts chess moves from FEN positions using a policy head + value head.
"""

from huggingface_hub import snapshot_download
from pathlib import Path
import sys

MODEL_ID = "Maxlegrec/ChessBot"
TARGET_DIR = Path(__file__).resolve().parent / "models" / "chessbot"


def main():
    if TARGET_DIR.exists() and (TARGET_DIR / "model.safetensors").exists():
        print(f"✅ Model already downloaded at {TARGET_DIR}")
        print("   Delete the directory to re-download.")
        return

    print(f"📥 Downloading {MODEL_ID} to {TARGET_DIR} ...")
    path = snapshot_download(MODEL_ID, local_dir=str(TARGET_DIR))
    print(f"✅ Downloaded to: {path}")
    print(f"   Model size: {(TARGET_DIR / 'model.safetensors').stat().st_size / 1024 / 1024:.1f} MB")


if __name__ == "__main__":
    main()
