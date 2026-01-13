import sys
import app.db.storage as s
from pathlib import Path

print("PY", sys.version)
print("FILE", s.__file__)
print("HAS_get_bytes_raw", hasattr(s, "get_bytes_raw"))

p = Path(s.__file__)
lines = p.read_text().splitlines()
start, end = 130, 190
print("---TAIL---")
for i, line in enumerate(lines[start:end], start=start+1):
    print(f"{i}: {line}")
