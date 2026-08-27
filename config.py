"""配置管理：API 设置、Blender 路径、默认提示词、数据文件路径。"""
import json
import os
import sys

if getattr(sys, "frozen", False):
    # PyInstaller 单文件版解压到临时目录运行；配置和检索表应保存在 EXE 旁边。
    APP_DIR = os.path.dirname(os.path.abspath(sys.executable))
else:
    APP_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(APP_DIR, "data")
CONFIG_FILE = os.path.join(APP_DIR, "config.json")
INDEX_FILE = os.path.join(DATA_DIR, "models_index.json")

DEFAULT_PROMPT = (
    "你是模型作者识别助手。给你一个 MMD/Blender 模型的 readme 文本，"
    "请找出这个模型的【主要作者】（如果是改変模型，取改変/配布者作为主要作者）。"
    "只输出 JSON，不要其他文字，格式："
    '{"name":"模型名","author":"主要作者","all_authors":["作者1","作者2"],"rules":"使用规约简述","category":"角色|场景|道具|舞台"}'
)

DEFAULT_CONFIG = {
    "ai_provider": "openai_compatible",
    "api_base": "https://api.deepseek.com/v1",
    "api_key": "",
    "model": "deepseek-chat",
    "codex_cli_path": "",
    "openai_models": [],
    "codex_models": [],
    "prompt": DEFAULT_PROMPT,
    "blender_path": "",
    "model_lib": r"D:\\模型",
    "index_path": "",
}


def ensure_dirs():
    os.makedirs(DATA_DIR, exist_ok=True)


def load_config():
    ensure_dirs()
    cfg = dict(DEFAULT_CONFIG)
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                loaded = json.load(f)
            cfg.update({k: v for k, v in loaded.items() if k in cfg})
        except Exception:
            pass
    return cfg


def save_config(cfg):
    ensure_dirs()
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)


def find_blender():
    """自动探测 Blender 可执行文件路径，找不到返回 None。"""
    import glob
    candidates = [
        r"C:\\Program Files\\Blender Foundation\\*\\blender.exe",
        r"C:\\Program Files (x86)\\Blender Foundation\\*\\blender.exe",
        r"D:\\*\\blender.exe",
        r"D:\\blender*\\blender.exe",
    ]
    for pat in candidates:
        hits = glob.glob(pat)
        if hits:
            return sorted(hits)[-1]
    return None
