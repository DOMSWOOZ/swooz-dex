import os
import tkinter as tk
from tkinter import messagebox

env_path = r"C:\Users\souls\.env"

def save_keys():
    api_key = key_var.get().strip()
    api_secret = secret_var.get().strip()
    if not api_key or not api_secret:
        messagebox.showerror("Missing Key", "Please paste both your Kraken API Key and Private Key (Secret).")
        return

    lines = []
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            lines = [
                line for line in f.readlines()
                if not line.startswith("KRAKEN_API_KEY=") and not line.startswith("KRAKEN_API_SECRET=")
            ]

    lines.append(f"KRAKEN_API_KEY={api_key}\n")
    lines.append(f"KRAKEN_API_SECRET={api_secret}\n")

    with open(env_path, "w", encoding="utf-8") as f:
        f.writelines(lines)

    print(f"Success! Saved KRAKEN_API_KEY and KRAKEN_API_SECRET to {env_path}")
    root.destroy()

def paste_to(var):
    try:
        text = root.clipboard_get().strip()
        var.set(text)
    except Exception:
        pass

root = tk.Tk()
root.title("Kraken Read-Only API Setup (swooz.eth)")
root.geometry("500x250")
root.configure(bg="#181a20")
root.attributes("-topmost", True)

key_var = tk.StringVar()
secret_var = tk.StringVar()

tk.Label(root, text="Kraken Read-Only Key Setup (Saved locally to ~/.env)", fg="#eaecef", bg="#181a20", font=("Segoe UI", 11, "bold")).pack(pady=(15, 10))

# API Key row
f1 = tk.Frame(root, bg="#181a20")
f1.pack(fill="x", padx=20, pady=5)
tk.Label(f1, text="1. API Key:", width=16, anchor="w", fg="#eaecef", bg="#181a20", font=("Segoe UI", 10)).pack(side="left")
e1 = tk.Entry(f1, textvariable=key_var, show="*", width=32, font=("Consolas", 10))
e1.pack(side="left", padx=5)
tk.Button(f1, text="Paste", command=lambda: paste_to(key_var), bg="#2b3139", fg="#eaecef", relief="flat", padx=8).pack(side="left")

# Private Key row
f2 = tk.Frame(root, bg="#181a20")
f2.pack(fill="x", padx=20, pady=5)
tk.Label(f2, text="2. Private Key:", width=16, anchor="w", fg="#eaecef", bg="#181a20", font=("Segoe UI", 10)).pack(side="left")
e2 = tk.Entry(f2, textvariable=secret_var, show="*", width=32, font=("Consolas", 10))
e2.pack(side="left", padx=5)
tk.Button(f2, text="Paste", command=lambda: paste_to(secret_var), bg="#2b3139", fg="#eaecef", relief="flat", padx=8).pack(side="left")

tk.Button(root, text="Save Keys to C:\\Users\\souls\\.env", command=save_keys, bg="#5865F2", fg="white", font=("Segoe UI", 10, "bold"), relief="flat", padx=16, pady=8).pack(pady=20)

root.mainloop()
