"""关于窗口：软件版本、GitHub 仓库链接。"""
import tkinter as tk
from tkinter import ttk
import webbrowser

VERSION = "v1.0"
GITHUB_URL = "https://github.com/swlt-silica/KariHelper"


class AboutWindow(tk.Toplevel):
    def __init__(self, master):
        super().__init__(master)
        self.title("关于 KariHelper")
        self.geometry("360x220")
        self.resizable(False, False)
        self.transient(master)

        frm = ttk.Frame(self, padding=20)
        frm.pack(fill="both", expand=True)

        ttk.Label(frm, text="KariHelper", font=("", 16, "bold")).pack(pady=(0, 4))
        ttk.Label(frm, text=f"版本 {VERSION}", font=("", 11)).pack(pady=(0, 8))

        ttk.Label(frm, text="借物表生成工具", font=("", 10)).pack(pady=(0, 4))
        ttk.Label(frm, text="从 Blender/MMD 工程自动提取模型作者\n生成借物表",
                  justify="center", foreground="#555").pack(pady=(0, 12))

        link = ttk.Label(frm, text=GITHUB_URL, foreground="#1a73e8", cursor="hand2",
                         font=("", 10, "underline"))
        link.pack(pady=(0, 8))
        link.bind("<Button-1>", lambda e: webbrowser.open(GITHUB_URL))

        ttk.Button(frm, text="关闭", command=self.destroy).pack()
