"""主窗口：添加工程 → 解析生成借物表（表格）→ 双击编辑 → 同步检索表 → 导出 txt。"""
import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from config import load_config
from index_db import IndexDB
from credit_gen import process_project, build_credit_text, merge_projects, export_txt
from settings_window import SettingsWindow
from index_window import IndexWindow
from about_window import AboutWindow
from editable_tree import EditableTree


class MainWindow(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("借物表生成器")
        self.geometry("1020x720")
        self.cfg = load_config()
        self.db = IndexDB(self.cfg.get("index_path") or None)
        self.projects = []
        self.project_results = []
        self._row_to_item = {}
        self._build_ui()

    def _build_ui(self):
        menubar = tk.Menu(self)
        m_file = tk.Menu(menubar, tearoff=0)
        m_file.add_command(label="打开检索表管理", command=self.open_index)
        m_file.add_separator()
        m_file.add_command(label="退出", command=self.quit)
        menubar.add_cascade(label="检索表", menu=m_file)
        m_tool = tk.Menu(menubar, tearoff=0)
        m_tool.add_command(label="设置", command=self.open_settings)
        m_tool.add_separator()
        m_tool.add_command(label="关于", command=self.open_about)
        menubar.add_cascade(label="工具", menu=m_tool)
        self.config(menu=menubar)
        main = ttk.Frame(self, padding=8)
        main.pack(fill="both", expand=True)
        left = ttk.LabelFrame(main, text="工程文件", padding=6)
        left.pack(side="left", fill="y", padx=(0, 8))
        self.list_proj = tk.Listbox(left, width=34, height=26, selectmode="extended")
        self.list_proj.pack(side="left", fill="both", expand=True)
        sb = ttk.Scrollbar(left, orient="vertical", command=self.list_proj.yview)
        sb.pack(side="right", fill="y")
        self.list_proj.config(yscrollcommand=sb.set)
        btns = ttk.Frame(left)
        btns.pack(fill="x", pady=(6, 0))
        ttk.Button(btns, text="添加工程", command=self.add_projects).pack(side="left", padx=2)
        ttk.Button(btns, text="移除选中", command=self.remove_selected).pack(side="left", padx=2)
        right = ttk.Frame(main)
        right.pack(side="left", fill="both", expand=True)
        top = ttk.Frame(right)
        top.pack(fill="x", pady=(0, 6))
        ttk.Button(top, text="解析并生成借物表", command=self.generate).pack(side="left")
        self.var_mode = tk.StringVar(value="per")
        ttk.Radiobutton(top, text="按工程", variable=self.var_mode, value="per", command=self._render).pack(side="left", padx=(10, 2))
        ttk.Radiobutton(top, text="合并", variable=self.var_mode, value="merged", command=self._render).pack(side="left")
        ttk.Label(top, text="（双击单元格可修改）", foreground="#888").pack(side="left")
        self._cols = ("project", "category", "model", "author", "all_authors", "rules")
        heads = ("工程", "类别", "模型", "主要作者", "全部作者", "规约")
        widths = (90, 60, 180, 130, 170, 220)
        self.tree = EditableTree(right, self._cols, heads, widths, on_edit=self._on_cell_edit)
        self.tree.pack(fill="both", expand=True)
        logfrm = ttk.LabelFrame(right, text="解析日志", padding=4)
        logfrm.pack(fill="x", side="bottom", pady=(6, 0))
        self.txt_log = tk.Text(logfrm, height=8, wrap="word", state="disabled")
        self.txt_log.pack(fill="x")
        logbar = ttk.Frame(logfrm)
        logbar.pack(fill="x", pady=(2, 0))
        ttk.Button(logbar, text="清空日志", command=self._clear_log).pack(side="left")
        bottom = ttk.Frame(right)
        bottom.pack(fill="x", pady=(6, 0))
        ttk.Button(bottom, text="同步修改到检索表", command=self.sync_to_index).pack(side="left", padx=2)
        ttk.Button(bottom, text="导出 txt", command=self.export).pack(side="left", padx=2)
        self.var_all = tk.BooleanVar(value=False)
        ttk.Checkbutton(bottom, text="借物表包含全部作者", variable=self.var_all).pack(side="left", padx=10)
        self.var_status = tk.StringVar(value="就绪")
        ttk.Label(self, textvariable=self.var_status, anchor="w", relief="sunken").pack(fill="x", side="bottom")

    def _log(self, msg):
        self.txt_log.config(state="normal")
        self.txt_log.insert("end", msg + "\n")
        self.txt_log.see("end")
        self.txt_log.config(state="disabled")
        self.update_idletasks()

    def _clear_log(self):
        self.txt_log.config(state="normal")
        self.txt_log.delete("1.0", "end")
        self.txt_log.config(state="disabled")

    def add_projects(self):
        files = filedialog.askopenfilenames(filetypes=[("工程文件", "*.blend *.pmm"), ("所有文件", "*.*")])
        for f in files:
            if f not in self.projects:
                self.projects.append(f)
                self.list_proj.insert("end", os.path.basename(f) + f"  [{os.path.dirname(f)}]")
        self._set_status(f"已添加 {len(files)} 个工程，共 {len(self.projects)} 个")

    def remove_selected(self):
        for i in reversed(self.list_proj.curselection()):
            self.list_proj.delete(i)
            del self.projects[i]
        self.project_results = []
        self._render()

    def generate(self):
        if not self.projects:
            messagebox.showinfo("提示", "请先添加工程文件")
            return
        self._set_status("解析中…")
        self._clear_log()
        self._log(f"开始解析 {len(self.projects)} 个工程")
        self.update_idletasks()
        results = []
        for p in self.projects:
            label = os.path.splitext(os.path.basename(p))[0]
            self._log(f"\n===== {label} =====")
            try:
                items, _ = process_project(p, self.db, self.cfg, log=self._log)
            except Exception as e:
                self._log(f"[错误] {e}")
                items = []
            results.append((label, items))
            self.update_idletasks()
        self.project_results = results
        self._render()
        self._set_status(f"完成。共 {len(results)} 个工程，{sum(len(it) for _, it in results)} 个资源已解析")

    def _render(self):
        self.tree.delete(*self.tree.get_children())
        self._row_to_item.clear()
        mode = self.var_mode.get()
        if mode == "merged":
            merged = merge_projects(self.project_results)
            self.tree["displaycolumns"] = self._cols[1:]
            for it in merged:
                entry = it.get("entry")
                if not entry:
                    continue
                row = self.tree.insert("", "end", values=("", entry.get("category", "模型"), entry.get("name", it["model"]), entry.get("author", ""), "、".join(entry.get("all_authors", [])) if entry.get("all_authors") else "", entry.get("rules", "")))
                self._row_to_item[row] = ("", it)
        else:
            self.tree["displaycolumns"] = self._cols
            for label, items in self.project_results:
                for it in items:
                    entry = it.get("entry")
                    if not entry:
                        continue
                    row = self.tree.insert("", "end", values=(label, entry.get("category", "模型"), entry.get("name", it["model"]), entry.get("author", ""), "、".join(entry.get("all_authors", [])) if entry.get("all_authors") else "", entry.get("rules", "")))
                    self._row_to_item[row] = (label, it)

    def _on_cell_edit(self, row_id, col, old, new):
        item = self._row_to_item.get(row_id)
        if not item:
            return
        _, it = item
        if not it.get("entry"):
            return
        entry = it["entry"]
        field_map = {"category": "category", "model": "name", "author": "author", "all_authors": "_all_authors_str", "rules": "rules"}
        fld = field_map.get(col)
        if not fld:
            return
        if fld == "_all_authors_str":
            entry["all_authors"] = [x.strip() for x in new.split("、") if x.strip()]
        else:
            entry[fld] = new
        self.db.set(it["key"], entry)
        self._set_status(f"已更新 {it['model']} 的「{col}」并同步到检索表")

    def sync_to_index(self):
        n = 0
        for _, it in self._row_to_item.values():
            if it.get("entry"):
                self.db.set(it["key"], it["entry"])
                n += 1
        self._set_status(f"已同步 {n} 条到检索表")

    def export(self):
        mode = self.var_mode.get()
        if mode == "per":
            parts = []
            for label, items in self.project_results:
                text = build_credit_text(items, project_label=label, all_authors=self.var_all.get())
                if text.strip():
                    parts.append(text)
            content = "\n".join(parts)
        else:
            merged = merge_projects(self.project_results)
            content = build_credit_text(merged, all_authors=self.var_all.get())
        if not content.strip():
            messagebox.showinfo("提示", "没有可导出的内容")
            return
        path = filedialog.asksaveasfilename(defaultextension=".txt", initialfile="借物表.txt", filetypes=[("文本文件", "*.txt")])
        if path:
            export_txt(content, path)
            self._set_status(f"已导出: {path}")

    def open_settings(self):
        SettingsWindow(self)
    def open_index(self):
        IndexWindow(self, self.db)
    def open_about(self):
        AboutWindow(self)
    def _set_status(self, msg):
        self.var_status.set(msg)
