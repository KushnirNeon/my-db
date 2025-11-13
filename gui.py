import tkinter as tk
from tkinter import messagebox, simpledialog, filedialog, ttk
from models import Database, Table, Column, join_tables
from storage import save_to_file, load_from_file

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Mini DBMS (Desktop)")
        self.geometry("960x540")
        self.db: Database | None = None
        self.db_name_var = tk.StringVar(value="Database: (none)")
        self._cur_table_name: str | None = None  # поточна таблиця (джерело істини)
        self._build_ui()

    def _build_ui(self):
        menubar = tk.Menu(self)
        filem = tk.Menu(menubar, tearoff=0)
        filem.add_command(label="New DB", command=self.new_db)
        filem.add_command(label="Open...", command=self.open_db)
        filem.add_command(label="Save As...", command=self.save_db)
        filem.add_separator()
        filem.add_command(label="Exit", command=self.destroy)
        menubar.add_cascade(label="File", menu=filem)
        self.config(menu=menubar)

        header = tk.Frame(self); header.pack(side="top", fill="x")
        tk.Label(header, textvariable=self.db_name_var, font=("Arial", 12, "bold")).pack(pady=4)

        toolbar = tk.Frame(self); toolbar.pack(side="top", fill="x", padx=8, pady=(0,6))
        self.btn_add_table = tk.Button(toolbar, text="Add table", command=self.add_table)
        self.btn_add_table.pack(side="left")
        self.btn_join = tk.Button(toolbar, text="Join...", command=self.join_tables_dialog)
        self.btn_join.pack(side="left", padx=(6,0))

        left = tk.Frame(self); left.pack(side="left", fill="y")
        tk.Label(left, text="Tables").pack(anchor="w", padx=8, pady=6)
        self.tables_list = tk.Listbox(left, width=26)
        self.tables_list.pack(fill="y", expand=False, padx=8, pady=4)
        self.tables_list.bind("<<ListboxSelect>>", self.on_listbox_select)  # надійний хендлер

        btns = tk.Frame(left); btns.pack(padx=8, pady=4, fill="x")
        self.btn_rename_table = tk.Button(btns, text="Rename", command=self.rename_table)
        self.btn_delete_table = tk.Button(btns, text="Delete", command=self.delete_table)
        self.btn_rename_table.grid(row=0, column=0, sticky="ew")
        self.btn_delete_table.grid(row=0, column=1, sticky="ew")
        for i in range(2): btns.grid_columnconfigure(i, weight=1)

        right = tk.Frame(self); right.pack(side="left", fill="both", expand=True)
        self.table_name_var = tk.StringVar(value="(no table)")
        tk.Label(right, textvariable=self.table_name_var, font=("Arial", 14, "bold")).pack(anchor="w", padx=8, pady=(6,2))

        cols_frame = tk.LabelFrame(right, text="Columns"); cols_frame.pack(fill="x", padx=8, pady=4)
        self.cols_tree = ttk.Treeview(cols_frame, columns=("name","dtype","enum"), show="headings", height=6)
        self.cols_tree.heading("name", text="Column")
        self.cols_tree.heading("dtype", text="Type")
        self.cols_tree.heading("enum", text="Enum values")
        self.cols_tree.column("name", width=200); self.cols_tree.column("dtype", width=120); self.cols_tree.column("enum", width=300)
        self.cols_tree.pack(side="left", fill="x", expand=True, padx=4, pady=4)
        cbtns = tk.Frame(cols_frame); cbtns.pack(side="left", fill="y", padx=4)
        self.btn_add_col = tk.Button(cbtns, text="Add column", command=self.add_column)
        self.btn_edit_col = tk.Button(cbtns, text="Edit column", command=self.edit_column)
        self.btn_del_col = tk.Button(cbtns, text="Delete column", command=self.delete_column)
        self.btn_add_col.pack(fill="x", pady=2); self.btn_edit_col.pack(fill="x", pady=2); self.btn_del_col.pack(fill="x", pady=2)

        rows_frame = tk.LabelFrame(right, text="Rows"); rows_frame.pack(fill="both", expand=True, padx=8, pady=4)
        self.rows_tree = ttk.Treeview(rows_frame, show="headings")
        self.rows_tree.pack(side="left", fill="both", expand=True, padx=4, pady=4)
        rbtns = tk.Frame(rows_frame); rbtns.pack(side="left", fill="y")
        self.btn_add_row = tk.Button(rbtns, text="Add row", command=self.add_row)
        self.btn_edit_row = tk.Button(rbtns, text="Edit row", command=self.edit_row)
        self.btn_del_row = tk.Button(rbtns, text="Delete row", command=self.delete_row)
        self.btn_add_row.pack(fill="x", padx=4, pady=2)
        self.btn_edit_row.pack(fill="x", padx=4, pady=2)
        self.btn_del_row.pack(fill="x", padx=4, pady=2)

        self.update_controls()
        self.refresh_tables_list()

    def on_listbox_select(self, event=None):
        if not self.db:
            return
        sel = self.tables_list.curselection()
        if not sel:
            if self._cur_table_name and self._cur_table_name in self.db.tables:
                names = self.db.list_tables()
                idx = names.index(self._cur_table_name)
                self.tables_list.selection_set(idx)
                self.tables_list.activate(idx)
            return
        name = self.tables_list.get(sel[0])
        self._cur_table_name = name
        self.refresh_table_view()

    def update_controls(self):
        enabled = self.db is not None
        for w in [self.btn_add_table, self.btn_join, self.btn_rename_table, self.btn_delete_table,
                  self.btn_add_col, self.btn_edit_col, self.btn_del_col,
                  self.btn_add_row, self.btn_edit_row, self.btn_del_row,
                  self.tables_list]:
            state = "normal" if enabled else "disabled"
            try: w.config(state=state)
            except: pass
        if not enabled:
            self.tables_list.delete(0, tk.END)
            self._cur_table_name = None
            self.table_name_var.set("(no table)")
            for w in (self.cols_tree, self.rows_tree):
                for i in w.get_children(): w.delete(i)
            self.rows_tree["columns"] = tuple()

    def current_table(self) -> Table | None:
        if not self.db:
            return None
        if self._cur_table_name and self._cur_table_name in self.db.tables:
            return self.db.get_table(self._cur_table_name)
        sel = self.tables_list.curselection()
        if sel:
            name = self.tables_list.get(sel[0])
            self._cur_table_name = name
            return self.db.get_table(name)
        return None

    def refresh_tables_list(self, select_name: str | None = None):
        if not self.db:
            self.update_controls()
            return
        self.tables_list.delete(0, tk.END)
        names = self.db.list_tables()
        for t in names:
            self.tables_list.insert(tk.END, t)

        target = select_name or self._cur_table_name
        if target in names:
            idx = names.index(target)
            self.tables_list.selection_clear(0, tk.END)
            self.tables_list.selection_set(idx)
            self.tables_list.activate(idx)
            self._cur_table_name = target
        else:
            self.tables_list.selection_clear(0, tk.END)
            self._cur_table_name = None

        self.refresh_table_view()

    def refresh_table_view(self):
        t = self.current_table()
        if not t:
            self.table_name_var.set(self._cur_table_name or "(no table)")
            if not (self._cur_table_name and self.db and self._cur_table_name in self.db.tables):
                for w in (self.cols_tree, self.rows_tree):
                    for i in w.get_children():
                        w.delete(i)
                self.rows_tree["columns"] = tuple()
            return

        self.table_name_var.set(t.name)

        for i in self.cols_tree.get_children():
            self.cols_tree.delete(i)
        for c in t.columns:
            self.cols_tree.insert("", "end", values=(c.name, c.dtype, ",".join(c.enum_values or [])))

        self.rows_tree['columns'] = tuple(t.column_names())
        self.rows_tree["show"] = "headings"
        for col in t.column_names():
            self.rows_tree.heading(col, text=col)
            self.rows_tree.column(col, width=120, stretch=True)
        for i in self.rows_tree.get_children():
            self.rows_tree.delete(i)
        for r in t.rows:
            self.rows_tree.insert("", "end", values=[r.get(c) for c in t.column_names()])

    def center_dialog(self, dlg: tk.Toplevel):
        dlg.update_idletasks()
        w, h = dlg.winfo_width(), dlg.winfo_height()
        sw, sh = self.winfo_width(), self.winfo_height()
        sx, sy = self.winfo_rootx(), self.winfo_rooty()
        x = sx + (sw - w)//2
        y = sy + (sh - h)//2
        dlg.geometry(f"+{x}+{y}")

    def new_db(self):
        name = simpledialog.askstring("New DB", "Database name:")
        if not name: return
        self.db = Database(name=name)
        self.db_name_var.set(f"Database: {self.db.name}")
        self._cur_table_name = None
        self.update_controls()
        self.refresh_tables_list()

    def open_db(self):
        path = filedialog.askopenfilename(filetypes=[("JSON","*.json")])
        if not path: return
        try:
            self.db = load_from_file(path)
            self.db_name_var.set(f"Database: {self.db.name}")
            self._cur_table_name = None
            self.update_controls()
            self.refresh_tables_list()
            messagebox.showinfo("Open", "Database loaded successfully.")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def save_db(self):
        if not self.db:
            messagebox.showerror("Save", "No database to save. Use File → New DB or Open...")
            return
        path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON","*.json")])
        if not path: return
        try:
            save_to_file(self.db, path)
            messagebox.showinfo("Save", "Database saved successfully.")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def add_table(self):
        if not self.db: return
        name = simpledialog.askstring("Add table", "Table name:")
        if not name: return
        try:
            self.db.create_table(name)
            self.refresh_tables_list(select_name=name)
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def rename_table(self):
        t = self.current_table()
        if not t: return
        name = simpledialog.askstring("Rename table", "New name:", initialvalue=t.name)
        if not name: return
        if name in self.db.tables and name != t.name:
            messagebox.showerror("Error", "Table with this name exists.")
            return
        del self.db.tables[t.name]
        t.name = name
        self.db.tables[name] = t
        self.refresh_tables_list(select_name=name)

    def delete_table(self):
        t = self.current_table()
        if not t: return
        if messagebox.askyesno("Delete", f"Delete table '{t.name}'?"):
            self.db.delete_table(t.name)
            self.refresh_tables_list()

    def add_column(self):
        t = self.current_table()
        if not t: return
        dlg = tk.Toplevel(self); dlg.title("Add column"); dlg.resizable(False, False)
        dlg.transient(self); dlg.grab_set()
        frm = tk.Frame(dlg); frm.pack(padx=12, pady=10)

        tk.Label(frm, text="Name:").grid(row=0, column=0, sticky="e", padx=6, pady=4)
        name_var = tk.StringVar()
        name_entry = tk.Entry(frm, textvariable=name_var, width=24)
        name_entry.grid(row=0, column=1, sticky="w", padx=6, pady=4)

        tk.Label(frm, text="Type:").grid(row=1, column=0, sticky="e", padx=6, pady=4)
        dtype_var = tk.StringVar(value="string")
        dtype_combo = ttk.Combobox(frm, textvariable=dtype_var, values=["integer","real","char","string","email","enum"], state="readonly", width=21)
        dtype_combo.grid(row=1, column=1, sticky="w", padx=6, pady=4)

        enum_lbl = tk.Label(frm, text="Enum values (comma-separated):")
        enum_var = tk.StringVar()
        enum_entry = tk.Entry(frm, textvariable=enum_var, width=24)
        def on_dtype_change(event=None):
            if dtype_var.get() == "enum":
                enum_lbl.grid(row=2, column=0, sticky="e", padx=6, pady=4)
                enum_entry.grid(row=2, column=1, sticky="w", padx=6, pady=4)
            else:
                enum_lbl.grid_forget(); enum_entry.grid_forget()
        dtype_combo.bind("<<ComboboxSelected>>", on_dtype_change)
        on_dtype_change()

        btns = tk.Frame(dlg); btns.pack(pady=8)
        ok = {"pressed": False}
        def submit():
            if not name_var.get().strip():
                messagebox.showerror("Error", "Name cannot be empty"); return
            ok["pressed"] = True; dlg.destroy()
        def cancel(): dlg.destroy()
        tk.Button(btns, text="OK", width=10, command=submit).grid(row=0, column=0, padx=6)
        tk.Button(btns, text="Cancel", width=10, command=cancel).grid(row=0, column=1, padx=6)
        name_entry.focus_set(); self.center_dialog(dlg)
        self.wait_window(dlg)
        if not ok["pressed"]: return

        name = name_var.get().strip()
        dtype = dtype_var.get().strip().lower()
        enum_values = None
        if dtype == "enum":
            enum_values = [x.strip() for x in enum_var.get().split(",") if x.strip()]
            if not enum_values:
                messagebox.showerror("Error", "Enum values cannot be empty"); return
        try:
            t.add_column(Column(name=name, dtype=dtype, enum_values=enum_values))
            self.refresh_table_view()
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def edit_column(self):
        t = self.current_table()
        if not t or not t.columns:
            return
        dlg = tk.Toplevel(self); dlg.title("Edit column"); dlg.resizable(False, False)
        dlg.transient(self); dlg.grab_set()
        frm = tk.Frame(dlg); frm.pack(padx=12, pady=10)

        tk.Label(frm, text="Column:").grid(row=0, column=0, sticky="e", padx=6, pady=4)
        col_names = t.column_names()
        col_var = tk.StringVar(value=col_names[0])
        ttk.Combobox(frm, values=col_names, textvariable=col_var, state="readonly", width=24).grid(row=0, column=1, sticky="w", padx=6, pady=4)

        tk.Label(frm, text="New type:").grid(row=1, column=0, sticky="e", padx=6, pady=4)
        dtype_var = tk.StringVar(value=next(c.dtype for c in t.columns if c.name == col_var.get()))
        dtype_box = ttk.Combobox(frm, values=["integer","real","char","string","email","enum"], textvariable=dtype_var, state="readonly", width=21)
        dtype_box.grid(row=1, column=1, sticky="w", padx=6, pady=4)

        enum_lbl = tk.Label(frm, text="Enum values (comma-separated):")
        enum_var = tk.StringVar()
        enum_entry = tk.Entry(frm, textvariable=enum_var, width=24)
        def refresh_enum_visibility(event=None):
            if dtype_var.get() == "enum":
                enum_lbl.grid(row=2, column=0, sticky="e", padx=6, pady=4)
                enum_entry.grid(row=2, column=1, sticky="w", padx=6, pady=4)
            else:
                enum_lbl.grid_forget(); enum_entry.grid_forget()
        dtype_box.bind("<<ComboboxSelected>>", refresh_enum_visibility)
        refresh_enum_visibility()

        btns = tk.Frame(dlg); btns.pack(pady=8)
        result = {"ok": False}
        def submit():
            name = col_var.get()
            new_dtype = dtype_var.get()
            enum_values = None
            if new_dtype == "enum":
                enum_values = [x.strip() for x in enum_var.get().split(",") if x.strip()]
                if not enum_values:
                    messagebox.showerror("Error", "Enum values cannot be empty"); return
            from models import Column as _Col
            validator = _Col(name, new_dtype, enum_values)
            try:
                for r in t.rows:
                    v = r.get(name)
                    if v is None:
                        continue
                    r[name] = validator.validate(v)
            except Exception as e:
                messagebox.showerror("Error", f"Cannot convert existing values: {e}")
                return
            for c in t.columns:
                if c.name == name:
                    c.dtype = new_dtype
                    c.enum_values = enum_values
                    break
            result["ok"] = True
            dlg.destroy()
        def cancel(): dlg.destroy()
        tk.Button(btns, text="OK", width=10, command=submit).grid(row=0, column=0, padx=6)
        tk.Button(btns, text="Cancel", width=10, command=cancel).grid(row=0, column=1, padx=6)
        self.center_dialog(dlg)
        self.wait_window(dlg)
        if result["ok"]:
            self.refresh_table_view()

    def delete_column(self):
        t = self.current_table()
        if not t: return
        name = simpledialog.askstring("Delete column", "Column name to delete:")
        if not name: return
        try:
            t.delete_column(name)
            self.refresh_table_view()
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def _prompt_row_values(self, t: Table, initial=None):
        dlg = tk.Toplevel(self); dlg.title("Row values"); dlg.resizable(False, False)
        dlg.transient(self); dlg.grab_set()
        frm = tk.Frame(dlg); frm.pack(padx=12, pady=10, fill="both", expand=True)

        widgets = {}
        rowi = 0
        for c in t.columns:
            tk.Label(frm, text=f"{c.name} ({c.dtype})").grid(row=rowi, column=0, sticky="e", padx=6, pady=4)
            init_val = "" if initial is None else ("" if initial.get(c.name) is None else str(initial.get(c.name)))
            if c.dtype == "enum" and c.enum_values:
                var = tk.StringVar(value=init_val if init_val in c.enum_values else (c.enum_values[0] if c.enum_values else ""))
                w = ttk.Combobox(frm, values=c.enum_values, textvariable=var, state="readonly", width=24)
                w.grid(row=rowi, column=1, sticky="w", padx=6, pady=4)
                widgets[c.name] = ("enum", var, c)
            else:
                var = tk.StringVar(value=init_val)
                w = tk.Entry(frm, textvariable=var, width=26)
                w.grid(row=rowi, column=1, sticky="w", padx=6, pady=4)
                widgets[c.name] = ("entry", var, c)
            rowi += 1

        btns = tk.Frame(dlg); btns.pack(pady=8)
        ok = {"pressed": False, "values": None}

        def collect_and_validate():
            vals = {}
            for name, (kind, var, col) in widgets.items():
                raw = var.get()
                if raw == "":
                    vals[name] = None
                else:
                    try:
                        vals[name] = col.validate(raw)
                    except Exception as e:
                        messagebox.showerror("Validation error", f"{name}: {e}")
                        return
            ok["pressed"] = True
            ok["values"] = vals
            dlg.destroy()

        def cancel(): dlg.destroy()

        tk.Button(btns, text="OK", width=10, command=collect_and_validate).grid(row=0, column=0, padx=6)
        tk.Button(btns, text="Cancel", width=10, command=cancel).grid(row=0, column=1, padx=6)
        try:
            for child in frm.grid_slaves(row=0, column=1):
                child.focus_set(); break
        except Exception: pass
        dlg.bind("<Return>", lambda e: collect_and_validate())
        dlg.bind("<Escape>", lambda e: cancel())
        self.center_dialog(dlg)
        self.wait_window(dlg)
        if not ok["pressed"]:
            return None
        return ok["values"]

    def add_row(self):
        t = self.current_table()
        if not t: return
        vals = self._prompt_row_values(t)
        if vals is None: return
        try:
            t.add_row(vals)
            self.refresh_table_view()
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def edit_row(self):
        t = self.current_table()
        if not t: return
        sel = self.rows_tree.selection()
        if not sel: return
        idx = self.rows_tree.index(sel[0])
        vals = self._prompt_row_values(t, t.rows[idx])
        if vals is None: return
        try:
            t.edit_row(idx, vals)
            self.refresh_table_view()
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def delete_row(self):
        t = self.current_table()
        if not t: return
        sel = self.rows_tree.selection()
        if not sel: return
        idx = self.rows_tree.index(sel[0])
        t.delete_row(idx)
        self.refresh_table_view()

    def join_tables_dialog(self):
        if not self.db or len(self.db.tables) < 2:
            messagebox.showerror("Join", "Need at least 2 tables (and an opened DB)")
            return
        names = self.db.list_tables()
        left = simpledialog.askstring("Join", f"Left table name ({', '.join(names)}):", initialvalue=names[0])
        if not left or left not in self.db.tables:
            return
        right_default = names[1] if len(names) > 1 else names[0]
        right = simpledialog.askstring("Join", f"Right table name ({', '.join(names)}):", initialvalue=right_default)
        if not right or right not in self.db.tables:
            return
        lk = self.db.get_table(left).column_names()
        key = simpledialog.askstring("Join", f"Join key (common column): {lk}")
        if not key: return
        try:
            res = join_tables(self.db.get_table(left), self.db.get_table(right), key)
            base = res.name; i=1
            while base in self.db.tables:
                base = f"{res.name}_{i}"; i+=1
            res.name = base
            self.db.tables[res.name] = res
            cur = self.current_table().name if self.current_table() else None
            self.refresh_tables_list(select_name=cur)
            messagebox.showinfo("Join", f"Join created as table '{res.name}'")
        except Exception as e:
            messagebox.showerror("Error", str(e))

def run():
    app = App()
    app.mainloop()

if __name__ == "__main__":
    run()
