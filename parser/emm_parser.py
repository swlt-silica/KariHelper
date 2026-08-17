"""解析 .emm（MME 特效分配文件）。"""
import os
import re

ENCS = ("gb18030", "shift_jis", "cp932", "utf-8")
re_win_path = re.compile(r"^[A-Za-z]:[\\/]")


def _decode_candidates(b):
    out = []
    seen = set()
    for enc in ENCS:
        try:
            s = b.decode(enc).strip()
        except Exception:
            continue
        if s and s not in seen:
            seen.add(s)
            out.append(s)
    return out


def _best_path(cands):
    for s in cands:
        if re_win_path.search(s):
            return s
    return cands[0] if cands else ""


def parse_emm(path):
    result = {"objects": [], "effects": []}
    if not os.path.exists(path):
        return result
    with open(path, "rb") as f:
        lines = f.readlines()
    section = None
    for raw in lines:
        raw = raw.rstrip(b"\r\n")
        if not raw.strip():
            continue
        if raw.startswith(b"[") and raw.endswith(b"]"):
            section = raw[1:-1].decode("ascii", errors="replace").strip()
            continue
        if b"=" not in raw:
            continue
        key, _, val = raw.partition(b"=")
        key = key.decode("ascii", errors="replace").strip()
        val_b = val.strip()
        if section == "Object":
            cands = _decode_candidates(val_b)
            result["objects"].append({"id": key, "candidates": cands, "path": _best_path(cands), "name": os.path.basename(_best_path(cands)) if _best_path(cands) else ""})
        elif section == "Effect":
            result["effects"].append({"target": key, "fx": val_b.decode("ascii", errors="replace").strip()})
    return result
