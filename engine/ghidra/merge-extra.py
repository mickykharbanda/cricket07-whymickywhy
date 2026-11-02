"""Merge hand-recovered functions into a Ghidra export.

    merge-extra.py <functions.json> <extra-functions.json> <out.json>

Entries whose address a later export already covers are skipped, so an overlay entry
retires itself once Ghidra learns the function. build.sh calls this before translating.
"""
import bisect
import json
import sys

base_path, extra_path, out_path = sys.argv[1:4]
base = json.load(open(base_path))
extra = json.load(open(extra_path))

ranges = sorted((a, b) for f in base["functions"] for a, b in f.get("ranges", []))
starts = [a for a, _ in ranges]
entries = {f["entry"] for f in base["functions"]}


def covered(addr):
    if addr in entries:
        return True
    i = bisect.bisect_right(starts, addr) - 1
    return i >= 0 and ranges[i][0] <= addr < ranges[i][1]


added = 0
for f in extra.get("functions", []):
    if covered(f["entry"]):
        print(f"  extra-functions: 0x{f['entry']:08x} is in the export now, skipping")
        continue
    base["functions"].append({k: v for k, v in f.items() if k != "why"})
    added += 1
base["functions"].sort(key=lambda f: f["entry"])

for j in extra.get("jumptables", []):
    if not any(x["at"] == j["at"] for x in base["jumptables"]):
        base["jumptables"].append(j)

json.dump(base, open(out_path, "w"))
print(f"  extra-functions: {added} hand-recovered function(s) merged in")
