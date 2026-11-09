#!/usr/bin/env python3
"""Merge the matugen palette into the oh-my-posh design -> matugen.omp.json."""
import json, os
d = os.path.expanduser("~/.config/ohmyposh")
cfg = json.load(open(f"{d}/viet.omp.json"))
try:
    cfg["palette"] = json.load(open(f"{d}/matugen-palette.json"))
except FileNotFoundError:
    pass  # keep the fallback palette baked into viet.omp.json
tmp = f"{d}/matugen.omp.json.tmp"
with open(tmp, "w") as f:
    json.dump(cfg, f, indent=2, ensure_ascii=False)
os.replace(tmp, f"{d}/matugen.omp.json")
