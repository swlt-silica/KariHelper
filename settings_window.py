"""设置窗口：OpenAI 兼容 API 配置、模型库路径、Blender 路径、默认提示词。"""
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from config import load_config, save_config, find_blender


class SettingsWindow(tk.Toplevel):
    def __init__(self, master):
        super().__init__(master)
        self.title("设置")
        self.geometry("620x520")
        self.transient(master)
        self.cfg = load_config()
        pad = {"padx": 8, "pady": 4}
        frm = ttk.Frame(self, padding=10)
        frm.pack(fill="both", expand=True)
        ttk.Label(frm, text="AI 接口配置（OpenAI 兼容）", font=("", 11, "bold")).grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 6))
        ttk.Label(frm, text="接口地址(API Base):").grid(row=1, column=0, sticky="e", **pad)
        self.var_base = tk.StringVar(value=self.cfg["api_base"])
        ttk.Entry(frm, textvariable=self.var_base, width=50).grid(row=1, column=1, columnspan=2, sticky="we", **pad)
        ttk.Label(frm, text="API Key:").grid(row=2, column=0, sticky="e", **pad)
        self.var_key = tk.StringVar(value=self.cfg["api_key"])
        ttk.Entry(frm, textvariable=self.var_key, width=50, show="*").grid(row=2, column=1, columnspan=2, sticky="we", **pad)
        ttk.Label(frm, text="模型名:").grid(row=3, column=0, sticky="e", **pad)
        self.var_model = tk.StringVar(value=self.cfg["model"])
        ttk.Entry(frm, textvariable=self.var_model, width=50).grid(row=3, column=1, columnspan=2, sticky="we", **pad)
        ttk.Separator(frm).grid(row=4, column=0, columnspan=3, sticky="we", pady=8)
        ttk.Label(frm, text="本地路径", font=("", 11, "bold")).grid(row=5, column=0, columnspan=3, sticky="w", pady=(0, 6))
        ttk.Label(frm, text="模型库路径:").grid(row=6, column=0, sticky="e", **pad)
        self.var_lib = tk.StringVar(value=self.cfg["model_lib"])
        ttk.Entry(frm, textvariable=self.var_lib, width=40).grid(row=6, column=1, sticky="we", **pad)
        ttk.Button(frm, text="浏览", command=lambda: self._browse(self.var_lib, isdir=True)).grid(row=6, column=2, **pad)
        ttk.Label(frm, text="Blender 路径:").grid(row=7, column=0, sticky="e", **pad)
        self.var_blender = tk.StringVar(value=self.cfg["blender_path"] or "")
        ttk.Entry(frm, textvariable=self.var_blender, width=40).grid(row=7, column=1, sticky="we", **pad)
        ttk.Button(frm, text="浏览", command=lambda: self._browse(self.var_blender, isdir=False)).grid(row=7, column=2, **pad)
        if not self.var_blender.get():
            auto = find_blender()
            if auto:
                self.var_blender.set(auto)
                ttk.Label(frm, text=f"已自动探测: {auto}", foreground="#666").grid(row=8, column=1, sticky="w", **pad)
        ttk.Label(frm, text="检索表路径:").grid(row=9, column=0, sticky="e", **pad)
        self.var_index = tk.StringVar(value=self.cfg.get("index_path", "") or "")
        ttk.Entry(frm, textvariable=self.var_index, width=40).grid(row=9, column=1, sticky="we", **pad)
        ttk.Button(frm, text="浏览", command=self._browse_index).grid(row=9, column=2, **pad)
        ttk.Label(frm, text="留空用软件内置；可指向别人的检索表 json", foreground="#888").grid(row=10, column=1, sticky="w", **pad)
        ttk.Separator(frm).grid(row=11, column=0, columnspan=3, sticky="we", pady=8)
        ttk.Label(frm, text="默认提示词", font=("", 11, "bold")).grid(row=12, column=0, columnspan=3, sticky="w", pady=(0, 6))
        self.txt_prompt = tk.Text(frm, width=70, height=10, wrap="word")
        self.txt_prompt.insert("1.0", self.cfg["prompt"])
        self.txt_prompt.grid(row=13, column=0, columnspan=3, sticky="we", **pad)
        ttk.Button(frm, text="保存", command=self._save).grid(row=14, column=1, sticky="e", **pad)
        ttk.Button(frm, text="取消", command=self.destroy).grid(row=14, column=2, sticky="w", **pad)
        frm.columnconfigure(1, weight=1)

    def _browse(self, var, isdir):
        if isdir:
            p = filedialog.askdirectory(initialdir=var.get() or "")
        else:
            p = filedialog.askopenfilename(filetypes=[("exe", "*.exe")])
        if p:
            var.set(p)

    def _browse_index(self):
        p = filedialog.askopenfilename(filetypes=[("JSON", "*.json"), ("所有文件", "*.*")], initialdir=self.var_index.get() or "")
        if p:
            self.var_index.set(p)

    def _save(self):
        self.cfg["api_base"] = self.var_base.get().strip()
        self.cfg["api_key"] = self.var_key.get().strip()
        self.cfg["model"] = self.var_model.get().strip()
        self.cfg["model_lib"] = self.var_lib.get().strip()
        self.cfg["blender_path"] = self.var_blender.get().strip()
        self.cfg["index_path"] = self.var_index.get().strip()
        self.cfg["prompt"] = self.txt_prompt.get("1.0", "end").strip()
        save_config(self.cfg)
        messagebox.showinfo("设置", "已保存（重启后生效检索表路径）")
        self.destroy()
