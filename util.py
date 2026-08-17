"""通用工具：readme 编码探测解码、文本截断。"""
import os

ENCS = ["utf-8", "shift_jis", "cp932", "gb18030", "utf-16-le", "utf-16"]


def decode_text(data):
    """自动探测编码解码 readme。返回 (文本, 编码)。"""
    for e in ENCS:
        try:
            return data.decode(e), e
        except Exception:
            continue
    return repr(data[:100]), "?"


def read_readme_text(path, max_chars=6000):
    """读取 readme 文本，超长截断。找不到文件返回空串。"""
    if not os.path.exists(path):
        return ""
    with open(path, "rb") as f:
        data = f.read()
    text, _ = decode_text(data)
    text = text.lstrip("﻿")
    if len(text) > max_chars:
        text = text[:max_chars] + "\n...[截断]"
    return text


def find_readme_in_dir(folder):
    """在文件夹里找一个 readme 文本文件（优先 txt，其次常见命名）。"""
    if not os.path.isdir(folder):
        return None
    candidates = []
    for name in os.listdir(folder):
        low = name.lower()
        if low.endswith((".txt", ".md")):
            candidates.append(name)
    keywords = ("readme", "read me", "説明", "りどみ", "説明書", "れどめ", "利用規約")
    for k in keywords:
        for name in candidates:
            if k in name.lower() or k in name:
                return os.path.join(folder, name)
    if candidates:
        return os.path.join(folder, candidates[0])
    return None
