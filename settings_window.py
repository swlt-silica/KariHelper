"""设置窗口：AI 渠道、模型、模型库、Blender 与默认提示词。"""
import queue
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from ai_clients import (
    PROVIDER_CODEX,
    PROVIDER_OPENAI,
    fetch_codex_models,
    fetch_openai_models,
    find_codex_cli,
    test_codex_connection,
    test_openai_connection,
)
from config import APP_DIR, load_config, save_config, find_blender


PROVIDER_LABELS = {
    PROVIDER_OPENAI: "OpenAI 兼容",
    PROVIDER_CODEX: "GPT（Codex CLI / ChatGPT 登录）",
}
LABEL_PROVIDERS = {label: provider for provider, label in PROVIDER_LABELS.items()}


class SettingsWindow(tk.Toplevel):
    def __init__(self, master):
        super().__init__(master)
        self.title("设置")
        self.geometry("760x780")
        self.minsize(700, 730)
        self.transient(master)
        self.cfg = load_config()
        self._async_queue = queue.Queue()
        self._busy = False

        pad = {"padx": 8, "pady": 4}
        frm = ttk.Frame(self, padding=10)
        frm.pack(fill="both", expand=True)

        ttk.Label(frm, text="AI 作者识别", font=("", 11, "bold")).grid(
            row=0, column=0, columnspan=3, sticky="w", pady=(0, 6)
        )
        ttk.Label(frm, text="当前渠道:").grid(row=1, column=0, sticky="e", **pad)
        provider = self.cfg.get("ai_provider", PROVIDER_OPENAI)
        self.var_provider = tk.StringVar(value=PROVIDER_LABELS.get(provider, PROVIDER_LABELS[PROVIDER_OPENAI]))
        self.cmb_provider = ttk.Combobox(
            frm,
            textvariable=self.var_provider,
            values=list(PROVIDER_LABELS.values()),
            state="readonly",
            width=47,
        )
        self.cmb_provider.grid(row=1, column=1, columnspan=2, sticky="we", **pad)
        self.cmb_provider.bind("<<ComboboxSelected>>", self._update_provider_visibility)

        self.lbl_base = ttk.Label(frm, text="接口地址(API Base):")
        self.lbl_base.grid(row=2, column=0, sticky="e", **pad)
        self.var_base = tk.StringVar(value=self.cfg["api_base"])
        self.entry_base = ttk.Entry(frm, textvariable=self.var_base, width=55)
        self.entry_base.grid(row=2, column=1, columnspan=2, sticky="we", **pad)

        self.lbl_key = ttk.Label(frm, text="API Key:")
        self.lbl_key.grid(row=3, column=0, sticky="e", **pad)
        self.var_key = tk.StringVar(value=self.cfg["api_key"])
        self.entry_key = ttk.Entry(frm, textvariable=self.var_key, width=55, show="*")
        self.entry_key.grid(row=3, column=1, columnspan=2, sticky="we", **pad)

        self.lbl_codex_cli = ttk.Label(frm, text="Codex CLI 路径:")
        self.lbl_codex_cli.grid(row=4, column=0, sticky="e", **pad)
        configured_cli = self.cfg.get("codex_cli_path", "")
        self.var_codex_cli = tk.StringVar(value=find_codex_cli(configured_cli) or configured_cli)
        self.entry_codex_cli = ttk.Entry(frm, textvariable=self.var_codex_cli, width=45)
        self.entry_codex_cli.grid(row=4, column=1, sticky="we", **pad)
        self.btn_codex_browse = ttk.Button(frm, text="浏览", command=self._browse_codex)
        self.btn_codex_browse.grid(row=4, column=2, **pad)

        ttk.Label(frm, text="手动模型名:").grid(row=5, column=0, sticky="e", **pad)
        self.var_model = tk.StringVar(value=self.cfg["model"])
        ttk.Entry(frm, textvariable=self.var_model, width=55).grid(
            row=5, column=1, columnspan=2, sticky="we", **pad
        )

        self.lbl_openai_models = ttk.Label(frm, text="OpenAI 兼容模型:")
        self.lbl_openai_models.grid(row=6, column=0, sticky="e", **pad)
        self.var_openai_model = tk.StringVar()
        self.cmb_openai_models = ttk.Combobox(
            frm,
            textvariable=self.var_openai_model,
            values=self.cfg.get("openai_models", []),
            state="readonly",
            width=47,
        )
        self.cmb_openai_models.grid(row=6, column=1, columnspan=2, sticky="we", **pad)
        self.cmb_openai_models.bind(
            "<<ComboboxSelected>>",
            lambda _event: self._select_model(PROVIDER_OPENAI, self.var_openai_model),
        )

        self.lbl_codex_models = ttk.Label(frm, text="GPT 模型:")
        self.lbl_codex_models.grid(row=7, column=0, sticky="e", **pad)
        self.var_codex_model = tk.StringVar()
        self.cmb_codex_models = ttk.Combobox(
            frm,
            textvariable=self.var_codex_model,
            values=self.cfg.get("codex_models", []),
            state="readonly",
            width=47,
        )
        self.cmb_codex_models.grid(row=7, column=1, columnspan=2, sticky="we", **pad)
        self.cmb_codex_models.bind(
            "<<ComboboxSelected>>",
            lambda _event: self._select_model(PROVIDER_CODEX, self.var_codex_model),
        )

        actions = ttk.Frame(frm)
        actions.grid(row=8, column=1, columnspan=2, sticky="w", **pad)
        self.btn_fetch = ttk.Button(actions, text="获取模型", command=self._fetch_models)
        self.btn_fetch.pack(side="left")
        self.btn_test = ttk.Button(actions, text="测试连接", command=self._test_connection)
        self.btn_test.pack(side="left", padx=(8, 0))
        self.var_status = tk.StringVar(value="测试连接会向当前模型发送一个极短请求")
        ttk.Label(frm, textvariable=self.var_status, foreground="#666", wraplength=560).grid(
            row=9, column=1, columnspan=2, sticky="w", **pad
        )

        ttk.Separator(frm).grid(row=10, column=0, columnspan=3, sticky="we", pady=8)
        ttk.Label(frm, text="本地路径", font=("", 11, "bold")).grid(
            row=11, column=0, columnspan=3, sticky="w", pady=(0, 6)
        )
        ttk.Label(frm, text="模型库路径:").grid(row=12, column=0, sticky="e", **pad)
        self.var_lib = tk.StringVar(value=self.cfg["model_lib"])
        ttk.Entry(frm, textvariable=self.var_lib, width=45).grid(row=12, column=1, sticky="we", **pad)
        ttk.Button(frm, text="浏览", command=lambda: self._browse(self.var_lib, isdir=True)).grid(
            row=12, column=2, **pad
        )

        ttk.Label(frm, text="Blender 路径:").grid(row=13, column=0, sticky="e", **pad)
        self.var_blender = tk.StringVar(value=self.cfg["blender_path"] or "")
        ttk.Entry(frm, textvariable=self.var_blender, width=45).grid(row=13, column=1, sticky="we", **pad)
        ttk.Button(frm, text="浏览", command=lambda: self._browse(self.var_blender, isdir=False)).grid(
            row=13, column=2, **pad
        )
        self.var_blender_status = tk.StringVar()
        if not self.var_blender.get():
            auto = find_blender()
            if auto:
                self.var_blender.set(auto)
                self.var_blender_status.set(f"已自动探测: {auto}")
        ttk.Label(frm, textvariable=self.var_blender_status, foreground="#666").grid(
            row=14, column=1, columnspan=2, sticky="w", **pad
        )

        ttk.Label(frm, text="检索表路径:").grid(row=15, column=0, sticky="e", **pad)
        self.var_index = tk.StringVar(value=self.cfg.get("index_path", "") or "")
        ttk.Entry(frm, textvariable=self.var_index, width=45).grid(row=15, column=1, sticky="we", **pad)
        ttk.Button(frm, text="浏览", command=self._browse_index).grid(row=15, column=2, **pad)
        ttk.Label(frm, text="留空用软件内置；可指向别人的检索表 json", foreground="#888").grid(
            row=16, column=1, sticky="w", **pad
        )

        ttk.Separator(frm).grid(row=17, column=0, columnspan=3, sticky="we", pady=8)
        ttk.Label(frm, text="默认提示词", font=("", 11, "bold")).grid(
            row=18, column=0, columnspan=3, sticky="w", pady=(0, 6)
        )
        self.txt_prompt = tk.Text(frm, width=75, height=8, wrap="word")
        self.txt_prompt.insert("1.0", self.cfg["prompt"])
        self.txt_prompt.grid(row=19, column=0, columnspan=3, sticky="nsew", **pad)

        ttk.Button(frm, text="保存", command=self._save).grid(row=20, column=1, sticky="e", **pad)
        ttk.Button(frm, text="取消", command=self.destroy).grid(row=20, column=2, sticky="w", **pad)
        frm.columnconfigure(1, weight=1)
        frm.rowconfigure(19, weight=1)
        self._update_provider_visibility()

    def _provider_id(self):
        return LABEL_PROVIDERS.get(self.var_provider.get(), PROVIDER_OPENAI)

    def _update_provider_visibility(self, _event=None):
        openai_widgets = (
            self.lbl_base,
            self.entry_base,
            self.lbl_key,
            self.entry_key,
            self.lbl_openai_models,
            self.cmb_openai_models,
        )
        codex_widgets = (
            self.lbl_codex_cli,
            self.entry_codex_cli,
            self.btn_codex_browse,
            self.lbl_codex_models,
            self.cmb_codex_models,
        )
        shown, hidden = (
            (codex_widgets, openai_widgets)
            if self._provider_id() == PROVIDER_CODEX
            else (openai_widgets, codex_widgets)
        )
        for widget in shown:
            widget.grid()
        for widget in hidden:
            widget.grid_remove()

    def _select_model(self, provider, variable):
        model = variable.get().strip()
        if not model:
            return
        self.var_model.set(model)
        self.var_provider.set(PROVIDER_LABELS[provider])
        self._update_provider_visibility()
        self.var_status.set(f"已选择 {model}，并回填到手动模型名")

    def _current_ai_config(self):
        cfg = dict(self.cfg)
        cfg.update(
            {
                "ai_provider": self._provider_id(),
                "api_base": self.var_base.get().strip(),
                "api_key": self.var_key.get().strip(),
                "model": self.var_model.get().strip(),
                "codex_cli_path": self.var_codex_cli.get().strip(),
                "prompt": self.txt_prompt.get("1.0", "end").strip(),
            }
        )
        return cfg

    def _fetch_models(self):
        cfg = self._current_ai_config()
        if cfg["ai_provider"] == PROVIDER_CODEX:
            def action():
                path = find_codex_cli(cfg["codex_cli_path"])
                return path, fetch_codex_models(path or "", cwd=APP_DIR)

            def success(result):
                path, models = result
                if path:
                    self.var_codex_cli.set(path)
                self.cmb_codex_models["values"] = models
                self.cfg["codex_models"] = models
                self.var_status.set(f"Codex CLI 获取到 {len(models)} 个模型，请从下拉栏选择")
        else:
            def action():
                return fetch_openai_models(cfg["api_base"], cfg["api_key"])

            def success(models):
                self.cmb_openai_models["values"] = models
                self.cfg["openai_models"] = models
                self.var_status.set(f"OpenAI 兼容渠道获取到 {len(models)} 个模型，请从下拉栏选择")
        self._start_async(action, success, "正在获取模型……")

    def _test_connection(self):
        cfg = self._current_ai_config()
        if not cfg["model"]:
            messagebox.showwarning("测试连接", "请先填写或选择模型")
            return
        if cfg["ai_provider"] == PROVIDER_CODEX:
            action = lambda: test_codex_connection(cfg, cwd=APP_DIR)
        else:
            action = lambda: test_openai_connection(cfg)
        self._start_async(action, self.var_status.set, "正在测试模型连接……")

    def _start_async(self, action, on_success, busy_text):
        if self._busy:
            return
        self._busy = True
        self.btn_fetch.config(state="disabled")
        self.btn_test.config(state="disabled")
        self.var_status.set(busy_text)

        def worker():
            try:
                self._async_queue.put((True, action(), on_success))
            except Exception as exc:
                self._async_queue.put((False, exc, None))

        threading.Thread(target=worker, daemon=True).start()
        self.after(80, self._poll_async)

    def _poll_async(self):
        try:
            ok, value, on_success = self._async_queue.get_nowait()
        except queue.Empty:
            if self.winfo_exists():
                self.after(80, self._poll_async)
            return
        self._busy = False
        self.btn_fetch.config(state="normal")
        self.btn_test.config(state="normal")
        if ok:
            on_success(value)
        else:
            self.var_status.set(f"失败：{value}")
            messagebox.showerror("AI 连接", str(value))

    def _browse(self, var, isdir):
        if isdir:
            path = filedialog.askdirectory(initialdir=var.get() or "")
        else:
            path = filedialog.askopenfilename(filetypes=[("exe", "*.exe")])
        if path:
            var.set(path)

    def _browse_codex(self):
        path = filedialog.askopenfilename(
            filetypes=[("Codex CLI", "codex.exe"), ("可执行文件", "*.exe"), ("所有文件", "*.*")],
            initialdir=self.var_codex_cli.get() or "",
        )
        if path:
            self.var_codex_cli.set(path)

    def _browse_index(self):
        path = filedialog.askopenfilename(
            filetypes=[("JSON", "*.json"), ("所有文件", "*.*")],
            initialdir=self.var_index.get() or "",
        )
        if path:
            self.var_index.set(path)

    def _save(self):
        self.cfg.update(self._current_ai_config())
        self.cfg["model_lib"] = self.var_lib.get().strip()
        self.cfg["blender_path"] = self.var_blender.get().strip()
        self.cfg["index_path"] = self.var_index.get().strip()
        self.cfg["openai_models"] = list(self.cmb_openai_models["values"])
        self.cfg["codex_models"] = list(self.cmb_codex_models["values"])
        save_config(self.cfg)
        messagebox.showinfo("设置", "已保存（重启后生效检索表路径）")
        self.destroy()
