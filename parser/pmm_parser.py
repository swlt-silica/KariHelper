"""解析 .pmm 工程，提取用到的模型/场景文件（纯 Python，无外部依赖）。"""
import os
import re

def _sjis_try(b):
    try:
        return b.decode("shift_jis")
    except Exception:
        return None

def _extract_paths(data):
    pat = re.compile(rb"\.(pmx|pmd|fx|vmd|sph|spa|x)\b")
    found = {}
    for m in pat.finditer(data):
        end = m.end()
        i = m.start()
        while i >= 2:
            pair = data[i - 2:i]
            if _sjis_try(pair) is not None:
                i -= 2
                continue
            b = data[i - 1]
            if 0x20 <= b <= 0x7E:
                i -= 1
                continue
            break
        seg = data[i:end]
        try:
            s = seg.decode("shift_jis")
        except Exception:
            continue
        base = s.split("\\\\")[-1].split("/")[-1].strip()
        if not base:
            continue
        key = base.lower()
        if key not in found:
            found[key] = (base, s)
    return list(found.values())


def parse_pmm(path, lib_files=None):
    with open(path, "rb") as f:
        data = f.read()
    resources = []
    if lib_files:
        hits = []
        for rel in lib_files:
            fname = os.path.basename(rel)
            stem = os.path.splitext(fname)[0]
            clean = re.sub(r"\s*ver\d+(\.\d+)*\s*$", "", stem, flags=re.I).strip()
            probes = list(dict.fromkeys([fname, stem, clean]))
            for probe in probes:
                if len(probe) < 2:
                    continue
                for enc in ("shift_jis", "cp932"):
                    try:
                        needle = probe.encode(enc)
                    except Exception:
                        continue
                    if needle in data:
                        hits.append((len(probe), fname, rel, probe))
                        break
        hits.sort(key=lambda h: -h[0])
        accepted = []
        accepted_probes = []
        for plen, fname, rel, probe in hits:
            if any(probe in ap for ap in accepted_probes):
                continue
            accepted.append({"name": fname, "path": rel})
            accepted_probes.append(probe)
        return accepted
    for base, s in _extract_paths(data):
        if len(base) < 5 or base.startswith((".", ")", "(")):
            continue
        resources.append({"name": base, "path": s})
    return resources
