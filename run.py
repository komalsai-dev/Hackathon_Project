"""
Cross-platform task runner for Windows and POSIX systems.
Usage:
    python run.py setup
    python run.py generate [--scale starter|full] [--seed 20261022]
    python run.py validate
    python run.py test
    python run.py api
    python run.py clean
"""

import sys
import subprocess
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent

def run_cmd(args):
    print(f"--> Running: {' '.join(args)}")
    res = subprocess.run(args, cwd=ROOT)
    if res.returncode != 0:
        sys.exit(res.returncode)

def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    cmd = sys.argv[1].lower()
    extra_args = sys.argv[2:]

    if cmd == "setup":
        run_cmd([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
    elif cmd == "generate":
        scale = "starter"
        seed = "20261022"
        # parse optional flags
        if "--scale" in extra_args:
            idx = extra_args.index("--scale")
            if idx + 1 < len(extra_args):
                scale = extra_args[idx + 1]
        if "--seed" in extra_args:
            idx = extra_args.index("--seed")
            if idx + 1 < len(extra_args):
                seed = extra_args[idx + 1]
        run_cmd([sys.executable, "-m", "backend.generator.run", "--scale", scale, "--seed", seed])
    elif cmd == "validate":
        run_cmd([sys.executable, "-m", "backend.validation.validate"])
    elif cmd == "test":
        run_cmd([sys.executable, "-m", "pytest", "backend/tests/", "-v"])
    elif cmd == "api":
        run_cmd([sys.executable, "-m", "backend.api.main"])
    elif cmd == "clean":
        print("Cleaning generated outputs and caches...")
        for p in ["data/output", "data/ground_truth", ".pytest_cache", "__pycache__"]:
            target = ROOT / p
            if target.exists():
                if target.is_dir():
                    shutil.rmtree(target, ignore_errors=True)
                else:
                    target.unlink()
        print("Clean complete.")
    else:
        print(f"Unknown command: {cmd}")
        print(__doc__)
        sys.exit(1)

if __name__ == "__main__":
    main()
