"""借物表生成核心：工程解析 → 查检索表 → 缺失则 AI 提取 → 生成/导出借物表。

支持来源：
- .pmm：用模型库文件名在二进制里精确匹配
- .emm：同目录 MME 特效分配文件，提供 Object 路径辅助定位 + MME Effect 特效
- .blend：调 Blender 后台解析
"""
import os

from config import load_config
from index_db import IndexDB
from util import find_readme_in_dir
from pmx_reader import find_pmx_in_dir
from ai_extract import extract_author_from_readme, extract_author_from_pmx

CATEGORY_DEFAULT = "模型"
CATEGORY_ORDER = ["角色", "场景", "道具", "舞台", "MME", "动作", "镜头", "表情", "模型", "其他"]


def list_lib_files(model_lib):
    if not model_lib or not os.path.isdir(model_lib):
        return []
    files = []
    exts = (".pmx", ".pmd", ".x")
    for root, dirs, fnames in os.walk(model_lib):
        for fn in fnames:
            if fn.lower().endswith(exts):
                files.append(os.path.relpath(os.path.join(root, fn), model_lib))
    return files


def find_model_folder(model_lib, model_name):
    if not model_lib or not os.path.isdir(model_lib):
        return None
    name_low = model_name.lower()
    for root, dirs, files in os.walk(model_lib):
        for fn in files:
            if fn.lower().endswith((".pmx", ".pmd", ".x")) and fn.lower().startswith(name_low):
                return root
    for entry in os.listdir(model_lib):
        p = os.path.join(model_lib, entry)
        if os.path.isdir(p) and name_low in entry.lower():
            return p
    return None


def _resolve_key(model_name, folder, lib):
    key = model_name
    if folder and lib:
        try:
            rel = os.path.relpath(folder, lib)
            key = os.path.join(rel, model_name).replace("\\", "/")
        except Exception:
            pass
    return key


def resolve_model(model_name, index_db, cfg, auto_extract=True, category=None):
    lib = cfg.get("model_lib", "")
    folder = find_model_folder(lib, model_name) if lib else None
    readme = find_readme_in_dir(folder) if folder else None
    pmx = find_pmx_in_dir(folder) if folder else None

    key = _resolve_key(model_name, folder, lib)
    entry = index_db.get(key)
    if entry:
        return entry, key, "index"
    alt = key.replace("/", "\\\\")
    if alt != key:
        entry = index_db.get(alt)
        if entry:
            return entry, alt, "index"

    if not readme and not pmx:
        return None, key, "not_found"
    if not auto_extract:
        return None, key, "pending"
    try:
        if readme:
            new_entry = extract_author_from_readme(readme, model_name)
        else:
            new_entry = extract_author_from_pmx(pmx, model_name)
        if category:
            new_entry["category"] = category
        index_db.set(key, new_entry)
        return new_entry, key, "ai_new"
    except Exception as e:
        return None, key, f"ai_error: {e}"


def resolve_by_path(path, index_db, cfg, auto_extract=True, category=None):
    key = path.replace("\\\\", "/")
    entry = index_db.get(key)
    if entry:
        return entry, key, "index"
    entry = index_db.get(path.replace("/", "\\\\"))
    if entry:
        return entry, path.replace("/", "\\\\"), "index"
    folder = os.path.dirname(path) if os.path.exists(path) else None
    readme = find_readme_in_dir(folder) if folder else None
    pmx = path if (path.lower().endswith(".pmx") and os.path.exists(path)) else None
    if not readme and not pmx:
        return None, key, "not_found"
    if not auto_extract:
        return None, key, "pending"
    try:
        name = os.path.splitext(os.path.basename(path))[0]
        if readme:
            new_entry = extract_author_from_readme(readme, name)
        elif pmx:
            new_entry = extract_author_from_pmx(pmx, name)
        if category:
            new_entry["category"] = category
        index_db.set(key, new_entry)
        return new_entry, key, "ai_new"
    except Exception as e:
        return None, key, f"ai_error: {e}"


def find_emm_for(project_path):
    base = os.path.splitext(project_path)[0]
    cand = base + ".emm"
    return cand if os.path.exists(cand) else None


def process_project(project_path, index_db, cfg, auto_extract=True, log=None):
    ext = os.path.splitext(project_path)[1].lower()
    items = []
    msgs = []

    def emit(msg):
        msgs.append(msg)
        if log:
            log(msg)

    if ext in (".pmm",):
        from parser.pmm_parser import parse_pmm
        lib = cfg.get("model_lib", "")
        lib_files = list_lib_files(lib) if lib else []
        res = parse_pmm(project_path, lib_files)
        names = [os.path.splitext(r["name"])[0] for r in res]
        emit(f"[PMM] 解析到 {len(names)} 个模型/场景")
        for n in names:
            entry, key, status = resolve_model(n, index_db, cfg, auto_extract)
            items.append({"model": n, "key": key, "entry": entry, "status": status, "category": "模型"})
            emit(format_status(n, status, entry))

        emm = find_emm_for(project_path)
        if emm:
            from parser.emm_parser import parse_emm
            emm_data = parse_emm(emm)
            emit(f"[EMM] 找到 {os.path.basename(emm)}：{len(emm_data['objects'])} 个对象，"
                 f"{sum(1 for e in emm_data['effects'] if e['fx'].strip().lower() != 'none')} 个 MME 特效")
            for e in emm_data["effects"]:
                fx = e["fx"].strip()
                if fx and fx.lower() != "none" and not fx.lower().endswith((".x", ".pmx")):
                    fx_name = os.path.splitext(os.path.basename(fx))[0]
                    entry, key, status = resolve_model(fx_name, index_db, cfg, auto_extract,
                                                       category="MME")
                    items.append({"model": fx_name, "key": key, "entry": entry,
                                  "status": status, "category": "MME"})
                    emit(format_status(fx_name, status, entry))
        else:
            emit("[EMM] 未找到同目录 .emm 文件")

    elif ext in (".blend",):
        from parser.blend_parser import parse_blend
        names = parse_blend(project_path, cfg.get("blender_path", ""))
        emit(f"[BLEND] 解析到 {len(names)} 个模型/场景")
        for n in names:
            entry, key, status = resolve_model(n, index_db, cfg, auto_extract)
            items.append({"model": n, "key": key, "entry": entry, "status": status, "category": "模型"})
            emit(format_status(n, status, entry))
    else:
        return [], f"不支持的文件类型: {ext}"

    return items, msgs


def format_status(name, status, entry):
    if status == "index":
        return f"[命中检索表] {name} → {entry.get('author', '') if entry else ''}"
    if status == "ai_new":
        return f"[新识别] {name} → {entry.get('author', '')}"
    if status.startswith("ai_error"):
        return f"[失败] {name}: {status}"
    if status == "pending":
        return f"[待识别] {name}（需 AI 提取作者）"
    if status == "not_found":
        return f"[未找到] {name}（模型库中无此资源或无 readme）"
    return f"[{status}] {name}"


def build_credit_text(items, project_label=None, all_authors=False):
    groups = {}
    for it in items:
        entry = it.get("entry")
        if not entry:
            continue
        cat = entry.get("category") or CATEGORY_DEFAULT
        if all_authors:
            authors = entry.get("all_authors") or [entry.get("author", "")]
            line = f"{entry.get('name', it['model'])}-{'、'.join(authors)}"
        else:
            line = f"{entry.get('name', it['model'])}-{entry.get('author', '?')}"
        groups.setdefault(cat, []).append(line)

    lines = []
    if project_label:
        lines.append(f"【{project_label}】")
    present = [c for c in CATEGORY_ORDER if c in groups]
    for c in present + [c for c in groups if c not in CATEGORY_ORDER]:
        lines.append(f"{c}：")
        lines.extend(sorted(set(groups[c])))
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def merge_projects(project_results):
    merged = {}
    for label, items in project_results:
        for it in items:
            if not it.get("entry"):
                continue
            m = it["model"]
            if m in merged:
                continue
            merged[m] = it
    return list(merged.values())


def export_txt(text, path):
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
