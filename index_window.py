"""检索表管理窗口：表格查看、搜索、双击编辑、删除。"""
import tkinter as tk
from tkinter import ttk, messagebox
from editable_tree import EditableTree


class IndexWindow(tk.Toplevel):
    def __init__(self, master, index_db):
        super().__init__(master)
        self.title("检索表管理")
        self.geometry("860x560")
        self.transient(master)
        self.db = index_db
        self._row_to_key = {}

        frm = ttk.Frame(self, padding=8)
        frm.pack(fill="both", expand=True)
        top = ttk.Frame(frm)
        top.pack(fill="x")
        ttk.Label(top, text="搜索:").pack(side="left")
        self.var_q = tk.StringVar()
        ent = ttk.Entry(top, textvariable=self.var_q, width=30)
        ent.pack(side="left", padx=4)
        ent.bind("<Return>", lambda e: self._refresh())
        ttk.Button(top, text="搜索", command=self._refresh).pack(side="left", padx=4)
        ttk.Button(top, text="新增", command=self._add).pack(side="left", padx=4)
        ttk.Label(top, text="（双击单元格修改）", foreground="#888").pack(side="right")
        ttk.Label(top, text=f"共 {len(self.db)} 条", foreground="#444").pack(side="right", padx=8)
        cols = ("key", "name", "author", "all_authors", "category", "rules")
        heads = ("检索键", "名称", "主要作者", "全部作者", "类别", "规约")
        widths = (260, 130, 110, 150, 60, 200)
        self.tree = EditableTree(frm, cols, heads, widths, on_edit=self._on_edit, height=20)
        self.tree.pack(fill="both", expand=True, pady=6)
        btns = ttk.Frame(frm)
        btns.pack(fill="x")
        ttk.Button(btns, text="删除选中", command=self._delete).pack(side="left", padx=4)
        ttk.Button(btns, text="刷新", command=self._refresh).pack(side="left", padx=4)
        self._refresh()

    def _refresh(self):
        self.tree.delete(*self.tree.get_children())
        self._row_to_key.clear()
        for key, entry in self.db.search(self.var_q.get()):
            row = self.tree.insert("", "end", values=(key, entry.get("name", ""), entry.get("author", ""), "、".join(entry.get("all_authors", [])), entry.get("category", ""), entry.get("rules", "")))
            self._row_to_key[row] = key

    def _on_edit(self, row_id, col, old, new):
        key = self._row_to_key.get(row_id)
        if not key:
            return
        entry = self.db.get(key)
        field_map = {"key": "_key", "name": "name", "author": "author", "all_authors": "_all", "category": "category", "rules": "rules"}
        fld = field_map.get(col)
        if not fld:
            return
        if fld == "_key":
            self.db.remove(key)
            self.db.set(new, entry)
            self._row_to_key[row_id] = new
        elif fld == "_all":
            entry["all_authors"] = [x.strip() for x in new.split("、") if x.strip()]
        else:
            entry[fld] = new
        self.db.set(self._row_to_key[row_id], entry)

    def _delete(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("提示", "请先选中一条")
            return
        key = self._row_to_key.get(sel[0])
        if key and messagebox.askyesno("删除", f"删除检索条目：{key}？"):
            self.db.remove(key)
            self._refresh()

    def _add(self):
        key = f"新增{len(self.db) + 1}"
        entry = {"name": "", "author": "", "all_authors": [], "category": "模型", "rules": ""}
        self.db.set(key, entry)
        self._refresh()
