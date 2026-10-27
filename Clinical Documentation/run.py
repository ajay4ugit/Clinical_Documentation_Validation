"""
Quick start helper — installs deps, seeds DB, and launches the server.
Run: python run.py
Run on a custom port: python run.py --port 9000
"""

import subprocess
import sys
import os
import socket
import argparse


def is_port_free(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            s.bind(("127.0.0.1", port))
            return True
        except OSError:
            return False


def find_free_port(start: int = 8080) -> int:
    for port in range(start, start + 20):
        if is_port_free(port):
            return port
    raise RuntimeError(f"No free port found in range {start}-{start+20}")


def main():
    parser = argparse.ArgumentParser(description="ClinDoc AI — Clinical Documentation System")
    parser.add_argument("--port", type=int, default=None,
                        help="Port to run the server on (default: auto-select starting from 8080)")
    args = parser.parse_args()

    print("=" * 60)
    print("  ClinDoc AI — Clinical Documentation Validation System")
    print("  Powered by IBM Bob + IBM Granite")
    print("=" * 60)

    # 1. Install dependencies
    print("\n  Installing dependencies...")
    subprocess.check_call(
        [sys.executable, "-m", "pip", "install", "-r", "requirements.txt", "-q"],
        stdout=subprocess.DEVNULL
    )
    print("  Dependencies ready.")

    # 2. Copy env.example to .env if missing
    if not os.path.exists(".env") and os.path.exists("env.example"):
        import shutil
        shutil.copy("env.example", ".env")
        print("  Created .env from env.example")
        print("  NOTE: Edit .env to add your IBM watsonx API key for Granite AI.")
        print("        Without it the system uses rule-based validation (fully functional).")

    # 3. Pick port
    if args.port:
        port = args.port
        if not is_port_free(port):
            print(f"\n  ERROR: Port {port} is already in use.")
            print(f"  Try: python run.py --port {find_free_port(port + 1)}")
            sys.exit(1)
    else:
        port = find_free_port(8080)

    # 4. Print URLs
    print(f"\n  Starting server at http://127.0.0.1:{port}\n")
    print(f"    Dashboard:    http://127.0.0.1:{port}/")
    print(f"    Documents:    http://127.0.0.1:{port}/documents")
    print(f"    Patients:     http://127.0.0.1:{port}/patients")
    print(f"    Issues:       http://127.0.0.1:{port}/issues")
    print(f"    New Document: http://127.0.0.1:{port}/new-document")
    print(f"    API Docs:     http://127.0.0.1:{port}/docs\n")
    print("  Press Ctrl+C to stop.\n")

    # 5. Launch uvicorn (replaces current process)
    os.execvp(sys.executable, [
        sys.executable, "-m", "uvicorn", "app.main:app",
        "--reload", "--host", "127.0.0.1", "--port", str(port)
    ])


if __name__ == "__main__":
    main()
