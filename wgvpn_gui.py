# wgvpn_gui.py -- Tkinter GUI for WireGuard VPN client
# Run as Administrator

import tkinter as tk
from tkinter import filedialog, messagebox
import threading
import sys
from pathlib import Path

# Import our CLI core
import wgvpn_core as core

# ── Constants ──────────────────────────────────────────────────
BG       = "#1e1e2e"
FG       = "#cdd6f4"
ACCENT   = "#89b4fa"
RED      = "#f38ba8"
GREEN    = "#a6e3a1"
GRAY     = "#45475a"
FONT     = ("Consolas", 10)
FONT_BIG = ("Consolas", 12, "bold")

class VPNApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("WGEduVPN")
        self.geometry("480x400")
        self.resizable(False, False)
        self.configure(bg=BG)

        # Find WireGuard
        if not core.find_wireguard():
            messagebox.showerror("Error", "WireGuard not found.\nInstall from wireguard.com")
            sys.exit(1)

        self._build_ui()
        self._refresh_list()
        self._tick()

    # ── UI Building ────────────────────────────────────────────
    def _build_ui(self):
        # Title
        tk.Label(self, text="WGEduVPN Client", font=FONT_BIG,
                 bg=BG, fg=ACCENT).pack(pady=(12, 4))

        # Profile list frame
        list_frame = tk.Frame(self, bg=BG)
        list_frame.pack(fill=tk.BOTH, padx=16, pady=4)

        tk.Label(list_frame, text="Profiles", font=FONT,
                 bg=BG, fg=FG).pack(anchor="w")

        self.listbox = tk.Listbox(
            list_frame, font=FONT, bg=GRAY, fg=FG,
            selectbackground=ACCENT, selectforeground=BG,
            height=6, borderwidth=0, highlightthickness=0
        )
        self.listbox.pack(fill=tk.BOTH)
        self.listbox.bind("<<ListboxSelect>>", self._on_select)

        # Status frame
        status_frame = tk.Frame(self, bg=BG)
        status_frame.pack(fill=tk.X, padx=16, pady=4)

        tk.Label(status_frame, text="Status", font=FONT,
                 bg=BG, fg=FG).pack(anchor="w")

        self.status_var = tk.StringVar(value="No profile selected")
        tk.Label(status_frame, textvariable=self.status_var,
                 font=FONT, bg=BG, fg=ACCENT,
                 wraplength=440, justify="left").pack(anchor="w")

        # Buttons
        btn_frame = tk.Frame(self, bg=BG)
        btn_frame.pack(pady=8)

        self.btn_connect = tk.Button(
            btn_frame, text="Connect", font=FONT,
            bg=GREEN, fg=BG, width=10,
            command=self._connect, relief=tk.FLAT
        )
        self.btn_connect.grid(row=0, column=0, padx=6)

        self.btn_disconnect = tk.Button(
            btn_frame, text="Disconnect", font=FONT,
            bg=RED, fg=BG, width=10,
            command=self._disconnect, relief=tk.FLAT
        )
        self.btn_disconnect.grid(row=0, column=1, padx=6)

        self.btn_import = tk.Button(
            btn_frame, text="Import .conf", font=FONT,
            bg=ACCENT, fg=BG, width=10,
            command=self._import, relief=tk.FLAT
        )
        self.btn_import.grid(row=0, column=2, padx=6)

    # ── List Management ────────────────────────────────────────
    def _refresh_list(self):
        self.listbox.delete(0, tk.END)
        core.PROFILES_DIR.mkdir(parents=True, exist_ok=True)
        profiles = sorted(core.PROFILES_DIR.glob("*.conf"))
        for p in profiles:
            name   = p.stem
            status = core.get_tunnel_status(name)
            dot    = "● " if status == "CONNECTED" else "○ "
            self.listbox.insert(tk.END, f"{dot}{name}")

    def _selected_name(self):
        sel = self.listbox.curselection()
        if not sel:
            return None
        item = self.listbox.get(sel[0])
        return item[2:]  # strip the dot + space

    def _on_select(self, event):
        self._update_status()

    # ── Status Update ──────────────────────────────────────────
    def _update_status(self):
        name = self._selected_name()
        if not name:
            self.status_var.set("No profile selected")
            return
        status = core.get_tunnel_status(name)
        if status == "DISCONNECTED":
            self.status_var.set(f"{name}  |  Disconnected")
            return
        # Get detailed status
        wg = core.find_wg()
        if not wg:
            self.status_var.set(f"{name}  |  Connected (wg.exe not found)")
            return
        import subprocess
        r = subprocess.run(
            [wg, "show", name, "dump"],
            capture_output=True, text=True,
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        if r.returncode != 0:
            self.status_var.set(f"{name}  |  Connected")
            return
        lines = r.stdout.strip().splitlines()
        if len(lines) >= 2:
            parts = lines[1].split('\t')
            if len(parts) >= 7:
                endpoint = parts[2]
                rx_kb    = int(parts[5]) // 1024
                tx_kb    = int(parts[6]) // 1024
                self.status_var.set(
                    f"{name}  |  Connected\n"
                    f"Endpoint: {endpoint}\n"
                    f"↓ {rx_kb} KB   ↑ {tx_kb} KB"
                )

    # ── Tick (polling) ─────────────────────────────────────────
    def _tick(self):
        try:
            sel = self.listbox.curselection()
            self._refresh_list()
            if sel:
                self.listbox.selection_set(sel[0])
            self._update_status()
        finally:
            self.after(1500, self._tick)

    # ── Button Actions ─────────────────────────────────────────
    def _connect(self):
        name = self._selected_name()
        if not name:
            messagebox.showwarning("No profile", "Please select a profile first.")
            return
        threading.Thread(target=self._do_connect, args=(name,), daemon=True).start()

    def _do_connect(self, name):
        try:
            core.cmd_up(name)
        except SystemExit:
            pass

    def _disconnect(self):
        name = self._selected_name()
        if not name:
            messagebox.showwarning("No profile", "Please select a profile first.")
            return
        threading.Thread(target=self._do_disconnect, args=(name,), daemon=True).start()

    def _do_disconnect(self, name):
        try:
            core.cmd_down(name)
        except SystemExit:
            pass

    def _import(self):
        path = filedialog.askopenfilename(
            title="Select WireGuard config",
            filetypes=[("WireGuard config", "*.conf")]
        )
        if path:
            try:
                core.cmd_import(path)
                self._refresh_list()
            except SystemExit:
                pass

# ── Entry Point ────────────────────────────────────────────────
if __name__ == "__main__":
    app = VPNApp()
    app.mainloop()