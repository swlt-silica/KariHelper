"""可编辑表格：基于 ttk.Treeview，支持双击单元格像 Excel 一样编辑。"""
import tkinter as tk
from tkinter import ttk


class EditableTree(ttk.Treeview):
    def __init__(self, master, columns, headings, widths, on_edit=None, **kw):
        super().__init__(master, columns=columns, show="headings", **kw)
        self._cols = columns
        self._headings = headings
        self._entry = None
        self._edit_id = None
        self._edit_col = None
        self.on_edit = on_edit

        for c, h, w in zip(columns, headings, widths):
            self.heading(c, text=h)
            self.column(c, width=w)

        self.bind("<Double-1>", self._on_double_click)
        self.bind("<Button-1>", self._on_single_click)

    def get_cell(self, row_id, col):
        vals = self.item(row_id, "values")
        idx = self._cols.index(col)
        return vals[idx] if idx < len(vals) else ""

    def set_cell(self, row_id, col, value):
        vals = list(self.item(row_id, "values"))
        idx = self._cols.index(col)
        while len(vals) <= idx:
            vals.append("")
        vals[idx] = value
        self.item(row_id, values=vals)

    def _on_single_click(self, event):
        if self._entry is not None:
            self._finish_edit(commit=False)

    def _on_double_click(self, event):
        row_id = self.identify_row(event.y)
        col = self.identify_column(event.x)
        if not row_id or not col:
            return
        col = col.lstrip("#")
        if col.isdigit():
            idx = int(col) - 1
            if idx >= len(self._cols):
                return
            col_key = self._cols[idx]
        else:
            return

        self._finish_edit(commit=False)
        x, y, w, h = self.bbox(row_id, col_key)
        if x is None:
            return
        value = self.get_cell(row_id, col_key)
        self._entry = tk.Entry(self, width=max(8, w // 8))
        self._entry.place(x=x, y=y, width=w, height=h)
        self._entry.insert(0, value)
        self._entry.select_range(0, "end")
        self._entry.focus_set()
        self._entry.bind("<Return>", lambda e: self._finish_edit(commit=True))
        self._entry.bind("<Escape>", lambda e: self._finish_edit(commit=False))
        self._entry.bind("<FocusOut>", lambda e: self._finish_edit(commit=False))
        self._edit_id, self._edit_col, self._old_value = row_id, col_key, value

    def _finish_edit(self, commit):
        if self._entry is None:
            return
        new_value = self._entry.get()
        self._entry.destroy()
        self._entry = None
        if commit and self._edit_id is not None:
            old = self._old_value
            if new_value != old:
                self.set_cell(self._edit_id, self._edit_col, new_value)
                if self.on_edit:
                    try:
                        self.on_edit(self._edit_id, self._edit_col, old, new_value)
                    except Exception as e:
                        print("on_edit error:", e)
        self._edit_id = None
