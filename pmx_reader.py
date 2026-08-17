"""PMX 读取器：从 PMX 内部提取模型名/注释（模型文件夹无 readme 时的作者来源）。"""
import os
import re


def is_readable(o):
    return (0x20 <= o <= 0x7e) or (0x3000 <= o <= 0x9fff) or (0xff01 <= o <= 0xff60)


def _find_strings(data, head_len=8192):
    found = []
    for i in range(min(head_len, len(data)) - 6):
        n = int.from_bytes(data[i:i + 4], "little", signed=True)
        if not (0 < n < 4000):
            continue
        chunk = data[i + 4:i + 4 + n]
        if len(chunk) != n:
            continue
        try:
            s = chunk.decode("utf-16-le")
        except Exception:
            continue
        if len(s) < 2:
            continue
        good = sum(1 for ch in s if is_readable(ord(ch)))
        if good / len(s) > 0.7:
            found.append(s)
    return found


def extract_pmx_info(path):
    """从 PMX 提取 (模型名, 注释/作者线索文本)。返回 (name, text)。"""
    if not os.path.exists(path):
        return None, ""
    with open(path, "rb") as f:
        data = f.read()
    if data[:4] != b"PMX ":
        return os.path.basename(path), ""

    strings = _find_strings(data)
    seen = set()
    uniq = []
    for s in strings:
        if s not in seen:
            seen.add(s)
            uniq.append(s)

    clue = [s for s in uniq if re.search(r"(式|制作|作った|モデリング|作者|作成)", s)]
    name = uniq[0] if uniq else os.path.basename(path)
    text = "\n".join(clue[:6]) if clue else "\n".join(uniq[:6])
    return name, text


def find_pmx_in_dir(folder):
    """在文件夹里找一个 .pmx 文件（任意深度优先，浅层优先）。"""
    if not os.path.isdir(folder):
        return None
    for fn in sorted(os.listdir(folder)):
        if fn.lower().endswith(".pmx"):
            return os.path.join(folder, fn)
    return None
