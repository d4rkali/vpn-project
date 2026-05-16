# wgvpn_core.py -- Full CLI for WireGuard VPN client
# Run as Administrator

import subprocess
import sys
import shutil
from pathlib import Path

# ── Configuration ──────────────────────────────────────────────
PROFILES_DIR = Path.home() / "AppData" / "Roaming" / "WGEduVPN" / "profiles"
WG_EXE = None  # will be found by find_wireguard()

# ── Find WireGuard ─────────────────────────────────────────────
def find_wireguard():
    global WG_EXE
    # Try PATH first
    found = shutil.which("wireguard.exe")
    if found:
        WG_EXE = found
        return True
    # Try standard install path
    standard = Path(r"C:\Program Files\WireGuard\wireguard.exe")
    if standard.exists():
        WG_EXE = str(standard)
        return True
    return False

def find_wg():
    found = shutil.which("wg.exe")
    if found:
        return found
    standard = Path(r"C:\Program Files\WireGuard\wg.exe")
    if standard.exists():
        return str(standard)
    return None

# ── Profile name validation ────────────────────────────────────
def valid_name(name: str) -> bool:
    import re
    return bool(re.match(r'^[a-zA-Z0-9_\-]{1,32}$', name))

# ── Commands ───────────────────────────────────────────────────
def cmd_paths():
    print(f"WireGuard exe : {WG_EXE}")
    print(f"Profiles dir  : {PROFILES_DIR}")

def cmd_list():
    PROFILES_DIR.mkdir(parents=True, exist_ok=True)
    profiles = list(PROFILES_DIR.glob("*.conf"))
    if not profiles:
        print("No profiles imported yet.")
        return
    print(f"{'NAME':<20} {'STATUS'}")
    print("-" * 35)
    for p in profiles:
        name = p.stem
        status = get_tunnel_status(name)
        print(f"{name:<20} {status}")

def cmd_import(conf_path: str):
    src = Path(conf_path)
    if not src.exists():
        print(f"File not found: {conf_path}")
        sys.exit(1)
    if src.suffix != ".conf":
        print("File must be a .conf file")
        sys.exit(1)
    name = src.stem
    if not valid_name(name):
        print(f"Invalid profile name: {name}")
        print("Use only letters, digits, underscores, hyphens. Max 32 chars.")
        sys.exit(1)
    PROFILES_DIR.mkdir(parents=True, exist_ok=True)
    dest = PROFILES_DIR / src.name
    if dest.exists():
        print(f"Profile '{name}' already exists. Overwrite? (y/n): ", end="")
        if input().strip().lower() != 'y':
            print("Cancelled.")
            return
    shutil.copy2(src, dest)
    print(f"Imported profile: {name}")

def cmd_up(name: str):
    if not valid_name(name):
        print(f"Invalid profile name: {name}")
        sys.exit(1)
    conf = PROFILES_DIR / f"{name}.conf"
    if not conf.exists():
        print(f"Profile '{name}' not found. Use 'import' first.")
        sys.exit(1)
    status = get_tunnel_status(name)
    if status == "CONNECTED":
        print(f"Tunnel '{name}' is already connected.")
        return
    r = subprocess.run(
        [WG_EXE, "/installtunnelservice", str(conf)],
        capture_output=True, text=True,
        creationflags=subprocess.CREATE_NO_WINDOW
    )
    if r.returncode != 0:
        print("FAILED:", r.stderr)
        sys.exit(1)
    print(f"Tunnel up: {name}")

def cmd_down(name: str):
    if not valid_name(name):
        print(f"Invalid profile name: {name}")
        sys.exit(1)
    status = get_tunnel_status(name)
    if status == "DISCONNECTED":
        print(f"Tunnel '{name}' is not connected.")
        return
    r = subprocess.run(
        [WG_EXE, "/uninstalltunnelservice", name],
        capture_output=True, text=True,
        creationflags=subprocess.CREATE_NO_WINDOW
    )
    if r.returncode != 0:
        print("FAILED:", r.stderr)
        sys.exit(1)
    print(f"Tunnel down: {name}")

def cmd_status(name: str):
    if not valid_name(name):
        print(f"Invalid profile name: {name}")
        sys.exit(1)
    wg = find_wg()
    if not wg:
        print("wg.exe not found.")
        sys.exit(1)
    r = subprocess.run(
        [wg, "show", name, "dump"],
        capture_output=True, text=True,
        creationflags=subprocess.CREATE_NO_WINDOW
    )
    if r.returncode != 0:
        print(f"Tunnel '{name}' is not running or not found.")
        return
    lines = r.stdout.strip().splitlines()
    if len(lines) < 2:
        print("No peer data available.")
        return
    # Second line is peer data
    parts = lines[1].split('\t')
    if len(parts) >= 7:
        endpoint     = parts[2]
        last_hs      = parts[4]
        rx_bytes     = int(parts[5])
        tx_bytes     = int(parts[6])
        print(f"Tunnel      : {name}")
        print(f"Status      : CONNECTED")
        print(f"Endpoint    : {endpoint}")
        print(f"Last HS     : {last_hs}s ago")
        print(f"Received    : {rx_bytes // 1024} KB")
        print(f"Sent        : {tx_bytes // 1024} KB")
    else:
        print("Could not parse status.")

# ── Helper ─────────────────────────────────────────────────────
def get_tunnel_status(name: str) -> str:
    r = subprocess.run(
        ["sc", "query", f"WireGuardTunnel${name}"],
        capture_output=True, text=True,
        creationflags=subprocess.CREATE_NO_WINDOW
    )
    if "RUNNING" in r.stdout:
        return "CONNECTED"
    return "DISCONNECTED"

# ── Main ───────────────────────────────────────────────────────
def main():
    if not find_wireguard():
        print("WireGuard not found. Install from https://www.wireguard.com/install/")
        sys.exit(1)

    if len(sys.argv) < 2:
        print("Usage:")
        print("  python wgvpn_core.py paths")
        print("  python wgvpn_core.py list")
        print("  python wgvpn_core.py import <path_to_conf>")
        print("  python wgvpn_core.py up <name>")
        print("  python wgvpn_core.py down <name>")
        print("  python wgvpn_core.py status <name>")
        sys.exit(0)

    cmd = sys.argv[1].lower()

    if cmd == "paths":
        cmd_paths()
    elif cmd == "list":
        cmd_list()
    elif cmd == "import":
        if len(sys.argv) < 3:
            print("Usage: python wgvpn_core.py import <path_to_conf>")
            sys.exit(1)
        cmd_import(sys.argv[2])
    elif cmd == "up":
        if len(sys.argv) < 3:
            print("Usage: python wgvpn_core.py up <name>")
            sys.exit(1)
        cmd_up(sys.argv[2])
    elif cmd == "down":
        if len(sys.argv) < 3:
            print("Usage: python wgvpn_core.py down <name>")
            sys.exit(1)
        cmd_down(sys.argv[2])
    elif cmd == "status":
        if len(sys.argv) < 3:
            print("Usage: python wgvpn_core.py status <name>")
            sys.exit(1)
        cmd_status(sys.argv[2])
    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)

if __name__ == "__main__":
    main()