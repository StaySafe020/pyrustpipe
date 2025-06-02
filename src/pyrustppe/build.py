import subprocess
import sys
from pathlib import Path

def build_rust_extension():
    """Build the Rust extension using maturin"""
    rust_dir = Path("src/rust")
    subprocess.check_call([sys.executable, "-m", "maturin", "develop"], cwd=rust_dir)

if __name__ == "__main__":
    build_rust_extension()