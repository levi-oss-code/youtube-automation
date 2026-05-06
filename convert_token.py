"""Convert token.pickle to token.json for Render compatibility."""
import json
import pickle
from pathlib import Path

pickle_path = Path("token.pickle")
json_path = Path("token.json")

with open(pickle_path, "rb") as f:
    credentials = pickle.load(f)

with open(json_path, "w", encoding="utf-8") as f:
    json.dump(json.loads(credentials.to_json()), f, indent=2)

print(f"Converted {pickle_path} to {json_path}")
