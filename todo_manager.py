#!/usr/bin/env python3
"""
Todo Manager - A desktop todo app for macOS
Built with Python + tkinter. No external dependencies required.
"""

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import json
import os
from datetime import datetime

# ---------- Data file ----------
DATA_FILE = os.path.join(os.path.expanduser("~"), ".todo_manager.json")

# ---------- Colors (dark theme) ----------
BG       = "#1a1a2e"
SIDEBAR  = "#16213e"
CARD     = "#0f3460"
ACCENT   = "#e94560"
FG       = "#eaeaea"
FG_DIM   = "#888888"
GREEN    = "#4ecca3"
YELLOW   = "#f5a623"
RED      = "#e94560"

PRIORITIES = {"High": RED, "Medium": YELLOW, "Low": GREEN}
CATEGORIES = ["Personal", "Work", "Shopping", "Health", "Other"]


# ─────────────────────────────────────────────
#  Data helpers
# ─────────────────────────────────────────────
def load_todos():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return []


def save_todos(todos):
    with open(DATA_FILE, "w") as f:
        json.dump(todos, f, indent=2)


# ─────────────────────────────────────────────
#  Add / Edit Dialog
# ─────────────────────────────────────────────
class TodoDialog(tk.Toplevel):
    def __init__(self, parent, title="Add Task", todo=None):
        super().__init__(parent)
        self.title(title)
        self.resizable(False, False)
        self.configure(bg=BG)
        self.result = None

        self.transient(parent)
        self.grab_set()

        # Center on parent
        self.geometry("+%d+%d" % (parent.winfo_rootx() + 80,
                                   parent.winfo_rooty() + 80))

        self._build(todo)
        self.wait_window()

    def _label(self, parent, text):
        tk.Label(parent, text=text, bg=BG, fg=FG_DIM,
                 font=("Helvetica", 10)).pack(anchor="w", pady=(8, 2))

    def _build(self, todo):
        pad = dict(padx=20, pady=6)

        # Title
        self._label(self, "Task Title *")
        self.title_var = tk.StringVar(value=todo["title"] if todo else "")
        tk.Entry(self, textvariable=self.title_var, bg=CARD, fg=FG,
                 insertbackground=FG, font=("Helvetica", 12),
                 relief="flat", width=40).pack(**pad)

        # Notes
        self._label(self, "Notes")
        self.notes_text = tk.Text(self, bg=CARD, fg=FG, insertbackground=FG,
                                  font=("Helvetica", 11), relief="flat",
                                  height=4, width=40)
        self.notes_text.pack(**pad)
        if todo and todo.get("notes"):
            self.notes_text.insert("1.0", todo["notes"])

        # Due date
        self._label(self, "Due Date (YYYY-MM-DD)")
        self.due_var = tk.StringVar(value=todo.get("due", "") if todo else "")
        tk.Entry(self, textvariable=self.due_var, bg=CARD, fg=FG,
                 insertbackground=FG, font=("Helvetica", 11),
                 relief="flat", width=40).pack(**pad)

        # Priority + Category row
        row = tk.Frame(self, bg=BG)
        row.pack(fill="x", padx=20, pady=6)

        # Priority
        pl = tk.Frame(row, bg=BG)
        pl.pack(side="left", padx=(0, 10))
        tk.Label(pl, text="Priority", bg=BG, fg=FG_DIM,
                 font=("Helvetica", 10)).pack(anchor="w")
        self.priority_var = tk.StringVar(value=todo.get("priority", "Medium") if todo else "Medium")
        priority_menu = ttk.Combobox(pl, textvariable=self.priority_var,
                                     values=list(PRIORITIES.keys()),
                                     state="readonly", width=12)
        priority_menu.pack()

        # Category
        cl = tk.Frame(row, bg=BG)
        cl.pack(side="left")
        tk.Label(cl, text="Category", bg=BG, fg=FG_DIM,
                 font=("Helvetica", 10)).pack(anchor="w")
        self.category_var = tk.StringVar(value=todo.get("category", "Personal") if todo else "Personal")
        category_menu = ttk.Combobox(cl, textvariable=self.category_var,
                                     values=CATEGORIES, state="readonly", width=14)
        category_menu.pack()

        # Buttons
        btn_row = tk.Frame(self, bg=BG)
        btn_row.pack(pady=14)
        tk.Button(btn_row, text="Save", bg=ACCENT, fg=FG,
                  font=("Helvetica", 11, "bold"), relief="flat",
                  padx=20, pady=6, cursor="hand2",
                  command=self._save).pack(side="left", padx=6)
        tk.Button(btn_row, text="Cancel", bg=CARD, fg=FG,
                  font=("Helvetica", 11), relief="flat",
                  padx=20, pady=6, cursor="hand2",
                  command=self.destroy).pack(side="left", padx=6)

    def _save(self):
        title = self.title_var.get().strip()
        if not title:
            messagebox.showwarning("Missing Title", "Please enter a task title.", parent=self)
            return
        due = self.due_var.get().strip()
        if due:
            try:
                datetime.strptime(due, "%Y-%m-%d")
            except ValueError:
                messagebox.showwarning("Invalid Date",
                                       "Date must be YYYY-MM-DD format.", parent=self)
                return
        self.result = {
            "title":    title,
            "notes":    self.notes_text.get("1.0", "end").strip(),
            "due":      due,
            "priority": self.priority_var.get(),
            "category": self.category_var.get(),
        }
        self.destroy()


# ─────────────────────────────────────────────
#  Main Application
# ─────────────────────────────────────────────
class TodoApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Todo Manager")
        self.geometry("900x620")
        self.minsize(700, 480)
        self.configure(bg=BG)

        # State
        self.todos = load_todos()
        self.filter_cat  = tk.StringVar(value="All")
        self.filter_pri  = tk.StringVar(value="All")
        self.filter_done = tk.StringVar(value="Active")
        self.search_var  = tk.StringVar()
        self.search_var.trace_add("write", lambda *_: self._refresh())

        self._build_ui()
        self._refresh()

    # ── UI construction ──────────────────────
    def _build_ui(self):
        self._build_sidebar()
        self._build_main()

    def _build_sidebar(self):
        sb = tk.Frame(self, bg=SIDEBAR, width=200)
        sb.pack(side="left", fill="y")
        sb.pack_propagate(False)

        # App title
        tk.Label(sb, text="✅ Todo\nManager", bg=SIDEBAR, fg=ACCENT,
                 font=("Helvetica", 16, "bold"), justify="center").pack(pady=20)

        tk.Frame(sb, bg=CARD, height=1).pack(fill="x", padx=14)

        # Filter: Status
        tk.Label(sb, text="SHOW", bg=SIDEBAR, fg=FG_DIM,
                 font=("Helvetica", 9, "bold")).pack(anchor="w", padx=16, pady=(14, 4))
        for label in ("Active", "Completed", "All"):
            tk.Radiobutton(sb, text=label, variable=self.filter_done,
                           value=label, bg=SIDEBAR, fg=FG,
                           activebackground=SIDEBAR, selectcolor=CARD,
                           font=("Helvetica", 11),
                           command=self._refresh).pack(anchor="w", padx=20)

        tk.Frame(sb, bg=CARD, height=1).pack(fill="x", padx=14, pady=10)

        # Filter: Category
        tk.Label(sb, text="CATEGORY", bg=SIDEBAR, fg=FG_DIM,
                 font=("Helvetica", 9, "bold")).pack(anchor="w", padx=16, pady=(4, 4))
        for cat in ["All"] + CATEGORIES:
            tk.Radiobutton(sb, text=cat, variable=self.filter_cat,
                           value=cat, bg=SIDEBAR, fg=FG,
                           activebackground=SIDEBAR, selectcolor=CARD,
                           font=("Helvetica", 11),
                           command=self._refresh).pack(anchor="w", padx=20)

        tk.Frame(sb, bg=CARD, height=1).pack(fill="x", padx=14, pady=10)

        # Filter: Priority
        tk.Label(sb, text="PRIORITY", bg=SIDEBAR, fg=FG_DIM,
                 font=("Helvetica", 9, "bold")).pack(anchor="w", padx=16, pady=(4, 4))
        for pri in ["All"] + list(PRIORITIES.keys()):
            tk.Radiobutton(sb, text=pri, variable=self.filter_pri,
                           value=pri, bg=SIDEBAR, fg=FG,
                           activebackground=SIDEBAR, selectcolor=CARD,
                           font=("Helvetica", 11),
                           command=self._refresh).pack(anchor="w", padx=20)

        # Stats at bottom
        self.stats_label = tk.Label(sb, text="", bg=SIDEBAR, fg=FG_DIM,
                                    font=("Helvetica", 9), justify="left")
        self.stats_label.pack(side="bottom", padx=16, pady=16, anchor="w")

    def _build_main(self):
        main = tk.Frame(self, bg=BG)
        main.pack(side="left", fill="both", expand=True)

        # Top bar
        top = tk.Frame(main, bg=BG)
        top.pack(fill="x", padx=16, pady=12)

        tk.Label(top, text="My Tasks", bg=BG, fg=FG,
                 font=("Helvetica", 18, "bold")).pack(side="left")

        tk.Button(top, text="+ Add Task", bg=ACCENT, fg=FG,
                  font=("Helvetica", 11, "bold"), relief="flat",
                  padx=14, pady=6, cursor="hand2",
                  command=self._add_task).pack(side="right")

        # Search bar
        search_frame = tk.Frame(main, bg=CARD, padx=8, pady=4)
        search_frame.pack(fill="x", padx=16, pady=(0, 10))
        tk.Label(search_frame, text="🔍", bg=CARD, fg=FG_DIM).pack(side="left")
        tk.Entry(search_frame, textvariable=self.search_var,
                 bg=CARD, fg=FG, insertbackground=FG,
                 font=("Helvetica", 11), relief="flat",
                 width=40).pack(side="left", padx=6)

        # Scrollable task list
        container = tk.Frame(main, bg=BG)
        container.pack(fill="both", expand=True, padx=16)

        canvas = tk.Canvas(container, bg=BG, highlightthickness=0)
        scrollbar = tk.Scrollbar(container, orient="vertical",
                                 command=canvas.yview)
        self.task_frame = tk.Frame(canvas, bg=BG)

        self.task_frame.bind("<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all")))

        canvas.create_window((0, 0), window=self.task_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Mouse wheel scroll
        canvas.bind_all("<MouseWheel>",
            lambda e: canvas.yview_scroll(int(-1*(e.delta/120)), "units"))

        self.canvas = canvas

        # Bulk action bar
        bulk = tk.Frame(main, bg=SIDEBAR)
        bulk.pack(fill="x", padx=16, pady=8)
        tk.Button(bulk, text="Delete Completed", bg=CARD, fg=RED,
                  font=("Helvetica", 10), relief="flat", padx=10, pady=4,
                  cursor="hand2",
                  command=self._delete_completed).pack(side="left", padx=4)
        tk.Button(bulk, text="Mark All Done", bg=CARD, fg=GREEN,
                  font=("Helvetica", 10), relief="flat", padx=10, pady=4,
                  cursor="hand2",
                  command=self._mark_all_done).pack(side="left", padx=4)
        tk.Button(bulk, text="Export .txt", bg=CARD, fg=FG,
                  font=("Helvetica", 10), relief="flat", padx=10, pady=4,
                  cursor="hand2",
                  command=self._export_txt).pack(side="right", padx=4)

    # ── Refresh / render tasks ───────────────
    def _filtered(self):
        query    = self.search_var.get().lower()
        show     = self.filter_done.get()
        cat_f    = self.filter_cat.get()
        pri_f    = self.filter_pri.get()
        result   = []
        for i, t in enumerate(self.todos):
            done = t.get("done", False)
            if show == "Active"    and done:   continue
            if show == "Completed" and not done: continue
            if cat_f != "All" and t.get("category") != cat_f: continue
            if pri_f != "All" and t.get("priority") != pri_f: continue
            if query and query not in t["title"].lower() \
                     and query not in t.get("notes","").lower(): continue
            result.append((i, t))
        return result

    def _refresh(self):
        for w in self.task_frame.winfo_children():
            w.destroy()

        items = self._filtered()

        if not items:
            tk.Label(self.task_frame, text="No tasks found.",
                     bg=BG, fg=FG_DIM,
                     font=("Helvetica", 13)).pack(pady=40)
        else:
            for idx, (orig_i, todo) in enumerate(items):
                self._render_card(orig_i, todo)

        # Stats
        total     = len(self.todos)
        done_cnt  = sum(1 for t in self.todos if t.get("done"))
        active    = total - done_cnt
        self.stats_label.config(
            text=f"Total:     {total}\nActive:    {active}\nDone:      {done_cnt}")

    def _render_card(self, idx, todo):
        done = todo.get("done", False)
        pri  = todo.get("priority", "Medium")
        color = PRIORITIES.get(pri, YELLOW)

        card = tk.Frame(self.task_frame, bg=CARD, padx=12, pady=10)
        card.pack(fill="x", pady=4)

        # Priority stripe
        tk.Frame(card, bg=color, width=4).pack(side="left", fill="y", padx=(0, 10))

        # Checkbox
        done_var = tk.BooleanVar(value=done)
        cb = tk.Checkbutton(card, variable=done_var, bg=CARD,
                            activebackground=CARD, command=lambda: self._toggle(idx, done_var))
        cb.pack(side="left")

        # Content
        content = tk.Frame(card, bg=CARD)
        content.pack(side="left", fill="both", expand=True)

        title_font = ("Helvetica", 12, "overstrike" if done else "bold")
        title_fg   = FG_DIM if done else FG
        tk.Label(content, text=todo["title"], bg=CARD, fg=title_fg,
                 font=title_font, anchor="w").pack(anchor="w")

        if todo.get("notes"):
            tk.Label(content, text=todo["notes"][:80] + ("…" if len(todo.get("notes","")) > 80 else ""),
                     bg=CARD, fg=FG_DIM,
                     font=("Helvetica", 10), anchor="w").pack(anchor="w")

        meta = []
        if todo.get("due"):
            meta.append(f"Due: {todo['due']}")
        if todo.get("category"):
            meta.append(todo["category"])
        meta.append(pri)
        if meta:
            tk.Label(content, text="  ·  ".join(meta),
                     bg=CARD, fg=color,
                     font=("Helvetica", 9), anchor="w").pack(anchor="w", pady=(2, 0))

        # Action buttons
        btn_frame = tk.Frame(card, bg=CARD)
        btn_frame.pack(side="right")
        tk.Button(btn_frame, text="✏", bg=CARD, fg=FG,
                  font=("Helvetica", 12), relief="flat", cursor="hand2",
                  command=lambda: self._edit_task(idx)).pack(side="left")
        tk.Button(btn_frame, text="🗑", bg=CARD, fg=RED,
                  font=("Helvetica", 12), relief="flat", cursor="hand2",
                  command=lambda: self._delete_task(idx)).pack(side="left")

    # ── Actions ──────────────────────────────
    def _add_task(self):
        dlg = TodoDialog(self, title="Add Task")
        if dlg.result:
            self.todos.insert(0, {**dlg.result, "done": False,
                                  "created": datetime.now().strftime("%Y-%m-%d %H:%M")})
            save_todos(self.todos)
            self._refresh()

    def _edit_task(self, idx):
        dlg = TodoDialog(self, title="Edit Task", todo=self.todos[idx])
        if dlg.result:
            self.todos[idx].update(dlg.result)
            save_todos(self.todos)
            self._refresh()

    def _delete_task(self, idx):
        if messagebox.askyesno("Delete", "Delete this task?", parent=self):
            self.todos.pop(idx)
            save_todos(self.todos)
            self._refresh()

    def _toggle(self, idx, var):
        self.todos[idx]["done"] = var.get()
        save_todos(self.todos)
        self._refresh()

    def _delete_completed(self):
        before = len(self.todos)
        self.todos = [t for t in self.todos if not t.get("done")]
        if len(self.todos) < before:
            save_todos(self.todos)
            self._refresh()

    def _mark_all_done(self):
        for t in self.todos:
            t["done"] = True
        save_todos(self.todos)
        self._refresh()

    def _export_txt(self):
        path = os.path.join(os.path.expanduser("~"), "Desktop", "todos_export.txt")
        lines = [f"Todo Export — {datetime.now().strftime('%Y-%m-%d %H:%M')}\n",
                 "=" * 50 + "\n"]
        for t in self.todos:
            status = "[x]" if t.get("done") else "[ ]"
            lines.append(f"{status} {t['title']}")
            if t.get("due"):      lines.append(f"    Due:      {t['due']}")
            if t.get("priority"): lines.append(f"    Priority: {t['priority']}")
            if t.get("category"): lines.append(f"    Category: {t['category']}")
            if t.get("notes"):    lines.append(f"    Notes:    {t['notes']}")
            lines.append("")
        with open(path, "w") as f:
            f.write("\n".join(lines))
        messagebox.showinfo("Exported", f"Saved to:\n{path}", parent=self)


# ─────────────────────────────────────────────
if __name__ == "__main__":
    app = TodoApp()
    app.mainloop()
