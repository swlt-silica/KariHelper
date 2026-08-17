"""AI 作者提取：调用 OpenAI 兼容 API，让模型从 readme 或 PMX 注释中找出作者。"""
import json
import os
import urllib.request

from config import load_config
from util import read_readme_text
from pmx_reader import extract_pmx_info


def _call_chat(cfg, user_content):
    url = cfg["api_base"].rstrip("/") + "/chat/completions"
    payload = {
        "model": cfg.get("model", "deepseek-chat"),
        "messages": [
            {"role": "system", "content": cfg.get("prompt", "")},
            {"role": "user", "content": user_content},
        ],
        "temperature": 0,
        "max_tokens": 1000,
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": "Bearer " + cfg.get("api_key", ""),
        },
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        body = json.loads(resp.read().decode("utf-8"))
    return body["choices"][0]["message"]["content"]


def _extract_json(text):
    text = text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        text = "\n".join(lines[1:-1]).strip()
    s, e = text.find("{"), text.rfind("}")
    if s == -1 or e == -1 or e < s:
        raise ValueError("AI 未返回 JSON")
    return json.loads(text[s:e + 1])


def _entry_from_data(data, model_name, source):
    return {
        "name": data.get("name") or model_name,
        "author": data.get("author", ""),
        "all_authors": data.get("all_authors", []),
        "rules": data.get("rules", ""),
        "category": data.get("category", "模型"),
        "readme": source,
    }


def extract_author(model_name, content, source):
    """给模型名 + 任意文本内容（readme 或 PMX 注释），AI 提取作者。"""
    cfg = load_config()
    if not cfg.get("api_key"):
        raise RuntimeError("未配置 API Key，请在设置中填写")
    if not content.strip():
        raise RuntimeError("无可用内容")
    user_content = f"模型名（参考）: {model_name}\n内容来源: {source}\n--- 内容 ---\n{content[:6000]}"
    resp = _call_chat(cfg, user_content)
    return _entry_from_data(_extract_json(resp), model_name, source)


def extract_author_from_readme(readme_path, model_name):
    text = read_readme_text(readme_path)
    if not text:
        raise RuntimeError(f"readme 为空或不存在: {readme_path}")
    return extract_author(model_name, text, readme_path)


def extract_author_from_pmx(pmx_path, model_name):
    name, text = extract_pmx_info(pmx_path)
    if not text:
        raise RuntimeError(f"PMX 无可用注释: {pmx_path}")
    return extract_author(model_name, text, pmx_path)
