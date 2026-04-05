#!/usr/bin/env python3
import tkinter as tk
from tkinter import ttk, messagebox
import json
import random
import string
import pyperclip
from cryptography.fernet import Fernet
from pathlib import Path

class PasswordManager:
    def __init__(self):
        self.window = tk.Tk()
        self.window.title("Password Manager")
        self.window.geometry("900x600")
        self.window.configure(bg="#1a1a2e")
        self.window.resizable(True, True)

        self.data_file = Path.home() / ".password_manager_data"
        self.key_file = Path.home() / ".password_manager_key"
        
        self.setup_encryption()
        self.load_data()
        self.setup_ui()

    def setup_encryption(self):
        if self.key_file.exists():
            with open(self.key_file, "rb") as f:
                self.key = f.read()
        else:
            self.key = Fernet.generate_key()
            with open(self.key_file, "wb") as f:
                f.write(self.key)
        self.cipher = Fernet(self.key)

    def load_data(self):
        if self.data_file.exists():
            try:
                with open(self.data_file, "rb") as f:
                    encrypted = f.read()
                decrypted = self.cipher.decrypt(encrypted)
                self.passwords = json.loads(decrypted)
            except:
                self.passwords = []
        else:
            self.passwords = []

    def save_data(self):
        json_data = json.dumps(self.passwords, indent=2)
        encrypted = self.cipher.encrypt(json_data.encode())
        with open(self.data_file, "wb") as f:
            f.write(encrypted)

    def setup_ui(self):
        style = ttk.Style()
        style.theme_use('clam')
        
        style.configure("TFrame", background="#1a1a2e")
        style.configure("Treeview", background="#16213e", foreground="#e0e0e0", 
                       fieldbackground="#16213e", rowheight=35, font=("Segoe UI", 10))
        style.configure("Treeview.Heading", background="#0f3460", foreground="#fff",
                       font=("Segoe UI", 10, "bold"))
        style.map("Treeview", background=[('selected', '#4facfe')])
        style.configure("Search.TEntry", padding=10, font=("Segoe UI", 10))

        main_frame = ttk.Frame(self.window)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        title_label = tk.Label(main_frame, text="Password Manager", font=("Segoe UI", 24, "bold"),
                              bg="#1a1a2e", fg="#00ff88")
        title_label.pack(pady=(0, 20))

        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(0, 15))

        buttons = [
            ("Add Password", self.add_password, "#00c853"),
            ("Generate Password", self.generate_password_gui, "#ff9800"),
            ("Edit", self.edit_password, "#2196f3"),
            ("Delete", self.delete_password, "#f44336"),
            ("Copy Password", self.copy_password, "#9c27b0"),
            ("Copy Username", self.copy_username, "#673ab7"),
        ]

        for text, cmd, color in buttons:
            btn = tk.Button(button_frame, text=text, command=cmd, 
                          bg=color, fg="white", activebackground=color, activeforeground="white",
                          font=("Segoe UI", 10, "bold"), padx=15, pady=8,
                          relief=tk.RAISED, cursor="hand2", borderwidth=2)
            btn.pack(side=tk.LEFT, padx=5)

        search_frame = ttk.Frame(main_frame)
        search_frame.pack(fill=tk.X, pady=(0, 15))

        tk.Label(search_frame, text="Search:", bg="#1a1a2e", fg="#e0e0e0",
                 font=("Segoe UI", 10)).pack(side=tk.LEFT, padx=(0, 10))
        
        self.search_var = tk.StringVar()
        self.search_var.trace("w", lambda *args: self.filter_passwords())
        search_entry = ttk.Entry(search_frame, textvariable=self.search_var, width=40,
                                 style="Search.TEntry")
        search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)

        list_frame = ttk.Frame(main_frame)
        list_frame.pack(fill=tk.BOTH, expand=True)

        columns = ("Site", "Username", "Password", "Notes")
        self.tree = ttk.Treeview(list_frame, columns=columns, show="headings", selectmode="browse")

        self.tree.heading("Site", text="Site", anchor=tk.CENTER)
        self.tree.heading("Username", text="Username", anchor=tk.CENTER)
        self.tree.heading("Password", text="Password", anchor=tk.CENTER)
        self.tree.heading("Notes", text="Notes", anchor=tk.CENTER)

        self.tree.column("Site", width=200, anchor=tk.W)
        self.tree.column("Username", width=200, anchor=tk.W)
        self.tree.column("Password", width=200, anchor=tk.W)
        self.tree.column("Notes", width=200, anchor=tk.W)

        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.tree.tag_configure('even', background='#16213e')
        self.tree.tag_configure('odd', background='#1a1a2e')

        self.populate_tree()

        self.tree.bind("<Double-1>", lambda e: self.copy_password())

        stats_frame = ttk.Frame(main_frame)
        stats_frame.pack(fill=tk.X, pady=(15, 0))
        
        stats_label = tk.Label(stats_frame, text=f"Total Passwords: {len(self.passwords)}",
                               bg="#1a1a2e", fg="#888", font=("Segoe UI", 10))
        stats_label.pack(side=tk.LEFT)

    def populate_tree(self, passwords=None):
        for item in self.tree.get_children():
            self.tree.delete(item)

        data = passwords if passwords is not None else self.passwords
        
        for i, pwd in enumerate(data):
            tags = ('even' if i % 2 == 0 else 'odd',)
            self.tree.insert("", tk.END, values=(
                pwd.get("site", ""),
                pwd.get("username", ""),
                "********" if pwd.get("password") else "",
                pwd.get("notes", "")[:30] + ("..." if len(pwd.get("notes", "")) > 30 else "")
            ), tags=tags)

    def filter_passwords(self):
        search_term = self.search_var.get().lower()
        if not search_term:
            self.populate_tree()
            return

        filtered = [
            p for p in self.passwords
            if search_term in p.get("site", "").lower() 
            or search_term in p.get("username", "").lower()
        ]
        self.populate_tree(filtered)

    def add_password(self):
        dialog = PasswordDialog(self.window, "Add Password", self)
        self.window.wait_window(dialog)
        if dialog.result:
            self.passwords.append(dialog.result)
            self.save_data()
            self.populate_tree()
            messagebox.showinfo("Success", "Password added successfully!")

    def edit_password(self):
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a password to edit")
            return

        idx = self.tree.index(selection[0])
        pwd_data = self.passwords[idx]

        dialog = PasswordDialog(self.window, "Edit Password", self, pwd_data)
        self.window.wait_window(dialog)
        if dialog.result:
            self.passwords[idx] = dialog.result
            self.save_data()
            self.populate_tree()
            messagebox.showinfo("Success", "Password updated successfully!")

    def delete_password(self):
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a password to delete")
            return

        if messagebox.askyesno("Confirm", "Are you sure you want to delete this password?"):
            idx = self.tree.index(selection[0])
            del self.passwords[idx]
            self.save_data()
            self.populate_tree()
            messagebox.showinfo("Success", "Password deleted successfully!")

    def copy_password(self):
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a password to copy")
            return

        idx = self.tree.index(selection[0])
        password = self.passwords[idx].get("password", "")
        if password:
            pyperclip.copy(password)
            messagebox.showinfo("Copied", "Password copied to clipboard!")

    def copy_username(self):
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a username to copy")
            return

        idx = self.tree.index(selection[0])
        username = self.passwords[idx].get("username", "")
        if username:
            pyperclip.copy(username)
            messagebox.showinfo("Copied", "Username copied to clipboard!")

    def generate_password_gui(self):
        dialog = GeneratePasswordDialog(self.window)
        self.window.wait_window(dialog)
        if dialog.password:
            pyperclip.copy(dialog.password)
            messagebox.showinfo("Generated", f"Password copied to clipboard!\n\n{dialog.password}")

    def run(self):
        self.window.mainloop()


class PasswordDialog(tk.Toplevel):
    def __init__(self, parent, title, app, data=None):
        super().__init__(parent)
        self.app = app
        self.title(title)
        self.geometry("450x420")
        self.resizable(False, False)
        self.configure(bg="#1a1a2e")
        self.result = None

        main_frame = tk.Frame(self, bg="#1a1a2e", padx=20, pady=20)
        main_frame.pack(fill=tk.BOTH, expand=True)

        fields = [
            ("Site/URL:", "site", data.get("site", "") if data else ""),
            ("Username:", "username", data.get("username", "") if data else ""),
            ("Password:", "password", data.get("password", "") if data else ""),
            ("Notes:", "notes", data.get("notes", "") if data else ""),
        ]

        self.entries = {}
        
        for i, (label_text, key, default) in enumerate(fields):
            tk.Label(main_frame, text=label_text, bg="#1a1a2e", fg="#ffffff",
                    font=("Segoe UI", 11, "bold")).grid(row=i, column=0, sticky=tk.W, pady=10)
            
            if key == "notes":
                entry = tk.Text(main_frame, height=4, width=35, bg="#2a2a4e", fg="#ffffff",
                               font=("Segoe UI", 11), relief=tk.SUNKEN, bd=2)
                entry.insert("1.0", default)
                entry.grid(row=i, column=1, pady=10, padx=(10, 0))
            else:
                show = "*" if key == "password" else ""
                entry = tk.Entry(main_frame, width=35, bg="#2a2a4e", fg="#ffffff",
                               font=("Segoe UI", 11), relief=tk.SUNKEN, bd=2, show=show)
                entry.insert(0, default)
                entry.grid(row=i, column=1, pady=10, padx=(10, 0))
            
            self.entries[key] = entry

        btn_frame = tk.Frame(main_frame, bg="#1a1a2e")
        btn_frame.grid(row=len(fields), column=0, columnspan=2, pady=20)

        tk.Button(btn_frame, text="Generate Password", bg="#ff9800", fg="white",
                 font=("Segoe UI", 10, "bold"), command=self.generate_password,
                 relief=tk.RAISED, padx=15, pady=8, cursor="hand2", borderwidth=2).pack(side=tk.LEFT, padx=5)

        tk.Button(btn_frame, text="Save", bg="#00c853", fg="white",
                 font=("Segoe UI", 10, "bold"), command=self.save,
                 relief=tk.RAISED, padx=20, pady=8, cursor="hand2", borderwidth=2).pack(side=tk.LEFT, padx=5)

        tk.Button(btn_frame, text="Cancel", bg="#666666", fg="white",
                 font=("Segoe UI", 10, "bold"), command=self.on_cancel,
                 relief=tk.RAISED, padx=15, pady=8, cursor="hand2", borderwidth=2).pack(side=tk.LEFT, padx=5)

        self.protocol("WM_DELETE_WINDOW", self.on_cancel)
        self.entries["site"].focus()
        self.grab_set()

    def generate_password(self):
        length = 16
        chars = string.ascii_letters + string.digits + "!@#$%^&*"
        password = ''.join(random.choice(chars) for _ in range(length))
        self.entries["password"].delete(0, tk.END)
        self.entries["password"].insert(0, password)

    def save(self):
        site = self.entries["site"].get().strip()
        username = self.entries["username"].get().strip()
        password = self.entries["password"].get()
        notes = self.entries["notes"].get("1.0", tk.END).strip()

        if not site:
            messagebox.showwarning("Warning", "Site/URL is required", parent=self)
            return
        if not username:
            messagebox.showwarning("Warning", "Username is required", parent=self)
            return
        if not password:
            messagebox.showwarning("Warning", "Password is required", parent=self)
            return

        self.result = {
            "site": site,
            "username": username,
            "password": password,
            "notes": notes
        }
        self.destroy()

    def on_cancel(self):
        self.result = None
        self.destroy()


class GeneratePasswordDialog(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Generate Password")
        self.geometry("400x320")
        self.resizable(False, False)
        self.configure(bg="#1a1a2e")
        self.password = None

        main_frame = tk.Frame(self, bg="#1a1a2e", padx=20, pady=20)
        main_frame.pack(fill=tk.BOTH, expand=True)

        tk.Label(main_frame, text="Password Generator", bg="#1a1a2e", fg="#00ff88",
                font=("Segoe UI", 16, "bold")).pack(pady=(0, 20))

        length_frame = tk.Frame(main_frame, bg="#1a1a2e")
        length_frame.pack(fill=tk.X, pady=10)

        tk.Label(length_frame, text="Length:", bg="#1a1a2e", fg="#ffffff",
                 font=("Segoe UI", 11)).pack(side=tk.LEFT)

        self.length_var = tk.IntVar(value=16)
        length_spin = tk.Spinbox(length_frame, from_=8, to=64, textvariable=self.length_var,
                                width=5, bg="#2a2a4e", fg="#ffffff", buttonbackground="#1a1a2e")
        length_spin.pack(side=tk.RIGHT)

        self.use_uppercase = tk.BooleanVar(value=True)
        self.use_lowercase = tk.BooleanVar(value=True)
        self.use_numbers = tk.BooleanVar(value=True)
        self.use_symbols = tk.BooleanVar(value=True)

        for text, var in [
            ("Uppercase (A-Z)", self.use_uppercase),
            ("Lowercase (a-z)", self.use_lowercase),
            ("Numbers (0-9)", self.use_numbers),
            ("Symbols (!@#$%)", self.use_symbols),
        ]:
            tk.Checkbutton(main_frame, text=text, variable=var,
                          bg="#1a1a2e", fg="#ffffff", selectcolor="#00c853",
                          activebackground="#1a1a2e", activeforeground="#ffffff").pack(anchor=tk.W, pady=3)

        self.password_var = tk.StringVar()
        result_entry = tk.Entry(main_frame, textvariable=self.password_var, state="readonly",
                               bg="#2a2a4e", fg="#00ff88", font=("Consolas", 14),
                               relief=tk.SUNKEN, bd=2, justify="center")
        result_entry.pack(fill=tk.X, pady=15)

        btn_frame = tk.Frame(main_frame, bg="#1a1a2e")
        btn_frame.pack(pady=10)

        tk.Button(btn_frame, text="Generate", bg="#2196f3", fg="white",
                 font=("Segoe UI", 10, "bold"), command=self.generate,
                 relief=tk.RAISED, padx=15, pady=8, cursor="hand2", borderwidth=2).pack(side=tk.LEFT, padx=5)

        tk.Button(btn_frame, text="Use Password", bg="#00c853", fg="white",
                 font=("Segoe UI", 10, "bold"), command=self.use_password,
                 relief=tk.RAISED, padx=15, pady=8, cursor="hand2", borderwidth=2).pack(side=tk.LEFT, padx=5)

        self.protocol("WM_DELETE_WINDOW", self.use_password)
        self.generate()
        self.grab_set()

    def generate(self):
        length = self.length_var.get()
        chars = ""

        if self.use_uppercase.get():
            chars += string.ascii_uppercase
        if self.use_lowercase.get():
            chars += string.ascii_lowercase
        if self.use_numbers.get():
            chars += string.digits
        if self.use_symbols.get():
            chars += "!@#$%^&*()_+-=[]{}|;:,.<>?"

        if not chars:
            chars = string.ascii_letters + string.digits

        self.password = ''.join(random.choice(chars) for _ in range(length))
        self.password_var.set(self.password)

    def use_password(self):
        self.destroy()


if __name__ == "__main__":
    app = PasswordManager()
    app.run()
