"""检索表管理：读写 models_index.json，支持搜索、增量更新、同步修改。

检索表结构:
{
  "schema_version": 1,
  "entries": {
    "<模型文件相对路径或唯一key>": {
      "name": "模型名",
      "author": "主要作者",
      "all_authors": ["作者1", ...],
      "rules": "规约简述",
      "category": "角色|场景|道具|舞台",
      "readme": "readme 相对路径或来源说明",
      "updated": "ISO 时间"
    }
  }
}
"""
import json
import os
import time
from config import INDEX_FILE, ensure_dirs


class IndexDB:
    def __init__(self, path=None):
        if path is None:
            path = INDEX_FILE
        ensure_dirs()
        self.path = path
        self.data = {"schema_version": 1, "entries": {}}
        self.load()

    def load(self):
        if os.path.exists(self.path):
            try:
                with open(self.path, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                if isinstance(loaded, dict):
                    self.data["entries"] = loaded.get("entries", {})
                    self.data["schema_version"] = loaded.get("schema_version", 1)
            except Exception:
                self.data = {"schema_version": 1, "entries": {}}

    def save(self):
        ensure_dirs()
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)

    def get(self, key):
        return self.data["entries"].get(key)

    def set(self, key, entry):
        entry["updated"] = time.strftime("%Y-%m-%d %H:%M:%S")
        self.data["entries"][key] = entry
        self.save()

    def remove(self, key):
        if key in self.data["entries"]:
            del self.data["entries"][key]
            self.save()

    def keys(self):
        return list(self.data["entries"].keys())

    def entries(self):
        return self.data["entries"]

    def search(self, query, limit=100):
        """按 模型名/作者/路径 模糊搜索。返回 (key, entry) 列表。"""
        q = query.strip().lower()
        if not q:
            results = [(k, e) for k, e in self.data["entries"].items()]
        else:
            results = []
            for k, e in self.data["entries"].items():
                hay = " ".join([
                    k, e.get("name", ""), e.get("author", ""),
                    " ".join(e.get("all_authors", [])), e.get("category", "")
                ]).lower()
                if q in hay:
                    results.append((k, e))
        results.sort(key=lambda x: x[0])
        return results[:limit]

    def __len__(self):
        return len(self.data["entries"])
