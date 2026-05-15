# wgvpn_min.py -- minimal proof of concept. Run as Administrator.
import subprocess, sys
from pathlib import Path

# Path to WireGuard executable
WG = r"C:\Program Files\WireGuard\wireguard.exe"

def up(conf_path: Path):
    r = subprocess.run([WG, "/installtunnelservice", str(conf_path)],
                       capture_output=True, text=True)
    if r.returncode != 0:
        print("FAILED:", r.stderr)
        sys.exit(1)
    print("Tunnel up:", conf_path.stem)

def down(name: str):
    r = subprocess.run([WG, "/uninstalltunnelservice", name],
                       capture_output=True, text=True)
    if r.returncode != 0:
        print("FAILED:", r.stderr)
        sys.exit(1)
    print("Tunnel down:", name)

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python wgvpn_min.py up <path_to_conf>")
        print("       python wgvpn_min.py down <tunnel_name>")
        sys.exit(1)
    cmd, arg = sys.argv[1], sys.argv[2]
    if cmd == "up":
        up(Path(arg))
    elif cmd == "down":
        down(arg)
    else:
        print("Unknown command:", cmd)