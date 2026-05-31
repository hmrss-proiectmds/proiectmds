"""
Pre-download the HuggingFace model used by the MahjongBot AI.

The MahjongBot uses sshleifer/tiny-gpt2 — the same lightweight text-generation
model that powers the PokerBot, so it is likely already cached.  Running this
script ensures the model is available locally before the first game starts.

Usage:
    cd backend
    source .venv/bin/activate
    python download_mahjong_model.py
"""

from transformers import pipeline

MODEL_NAME = "sshleifer/tiny-gpt2"

print(f"Downloading / verifying '{MODEL_NAME}' ...")
pipe = pipeline("text-generation", model=MODEL_NAME, device=-1)
# Smoke-test
out = pipe("Test:", max_new_tokens=3, pad_token_id=pipe.tokenizer.eos_token_id)
print(f"Model ready. Sample output: {out[0]['generated_text']!r}")
print("Done.")
