"""解析 .blend 工程，提取用到的模型/场景（依赖本机 Blender 后台模式）。"""
import json
import os
import re
import subprocess
import tempfile

DUMP_SCRIPT = r'''
import sys, bpy, json
blendfile = sys.argv[sys.argv.index("--") + 1]
bpy.ops.wm.open_mainfile(filepath=blendfile)
result = {"blendfile": blendfile, "scenes": []}
def walk(coll, out):
    out.append({"name": coll.name, "objects": [o.name for o in coll.objects]})
    for ch in coll.children:
        walk(ch, out)
for scene in bpy.data.scenes:
    sc = {"name": scene.name, "collections": []}
    for coll in scene.collection.children:
        walk(coll, sc["collections"])
    result["scenes"].append(sc)
with open(sys.argv[sys.argv.index("--") + 2], "w", encoding="utf-8") as f:
    json.dump(result, f, ensure_ascii=False)
print("DUMP_DONE")
'''

SKIP_EXACT = {
    "rigidbodies", "joints", "temporary", ".placeholder", ".dummy_armature",
    "Light", "Camera", "点光", "面光", "聚光", "体积", "立方体",
}
SKIP_PREFIX = ("面光", "聚光", "点光", "temporary")


def _candidates(names):
    out = set()
    for n in names:
        if n.startswith("RIG-") or n.startswith(SKIP_PREFIX):
            continue
        if n.endswith("_arm") or n.endswith("_mesh"):
            out.add(n)
    for n in names:
        if n.startswith("RIG-") or n.startswith(SKIP_PREFIX):
            continue
        if re.match(r"^\d+_", n):
            continue
        if n.startswith("J."):
            continue
        if n.startswith("ncc") or n.startswith("mmd_bonetrack"):
            continue
        if n in SKIP_EXACT:
            continue
        if re.search(r"[぀-ヿ一-鿿]", n) or re.search(r"ver\d", n, re.I):
            out.add(n)
    return out


def parse_blend(path, blender_path=None):
    if not blender_path:
        import config
        blender_path = config.find_blender()
    if not blender_path or not os.path.exists(blender_path):
        raise RuntimeError("未找到 Blender，请在设置中填写 Blender 路径")
    tmp_json = os.path.join(tempfile.gettempdir(), f"_blend_dump_{os.path.basename(path)}.json")
    script_path = os.path.join(tempfile.gettempdir(), "_mmd_dump_blend.py")
    with open(script_path, "w", encoding="utf-8") as f:
        f.write(DUMP_SCRIPT)
    cmd = [blender_path, "--background", "--python", script_path, "--", path, tmp_json]
    proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if not os.path.exists(tmp_json):
        raise RuntimeError(f"Blender 解析失败: {proc.stderr[-500:] if proc.stderr else '未知错误'}")
    with open(tmp_json, "r", encoding="utf-8") as f:
        data = json.load(f)
    models = set()
    for scene in data.get("scenes", []):
        for coll in scene.get("collections", []):
            if coll.get("name") != "Collection":
                continue
            models |= _candidates(coll.get("objects", []))
    clean = set()
    for m in models:
        if m.endswith("_arm") or m.endswith("_mesh"):
            continue
        clean.add(m)
    return sorted(clean)
