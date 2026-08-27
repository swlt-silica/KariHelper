"""AI 作者提取：支持 OpenAI 兼容 API 与本机 Codex CLI。"""
import json

from ai_clients import PROVIDER_CODEX, call_openai_chat, run_codex_prompt
from config import APP_DIR, load_config
from util import read_readme_text
from pmx_reader import extract_pmx_info


AUTHOR_SCHEMA = {
    "type": "object",
    "properties": {
        "name": {"type": "string"},
        "author": {"type": "string"},
        "all_authors": {"type": "array", "items": {"type": "string"}},
        "rules": {"type": "string"},
        "category": {"type": "string"},
    },
    "required": ["name", "author", "all_authors", "rules", "category"],
    "additionalProperties": False,
}


def _call_chat(cfg, user_content):
    if cfg.get("ai_provider") == PROVIDER_CODEX:
        prompt = (
            f"{cfg.get('prompt', '')}\n\n"
            "不要读取文件、不要调用工具，只根据下面提供的文本回答。\n\n"
            f"{user_content}"
        )
        return run_codex_prompt(
            cfg.get("codex_cli_path", ""),
            cfg.get("model", ""),
            prompt,
            output_schema=AUTHOR_SCHEMA,
            cwd=APP_DIR,
        )
    return call_openai_chat(cfg, user_content)


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
    if not cfg.get("model"):
        raise RuntimeError("未配置模型，请在设置中填写或获取模型")
    if cfg.get("ai_provider") != PROVIDER_CODEX and not cfg.get("api_base"):
        raise RuntimeError("未配置 API Base，请在设置中填写")
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
