#!/usr/bin/env python3
"""
Run the Maui Travel Advisor web UI.
"""
import os
import subprocess
import sys

def main():
    cwd = os.path.dirname(os.path.abspath(__file__))
    try:
        subprocess.run(
            [sys.executable, "-m", "streamlit", "run", "app.py", "--server.headless", "true"],
            cwd=cwd,
            check=True,
        )
    except FileNotFoundError:
        print("Streamlit is not installed. Run:")
        print("  python3 -m pip install streamlit")
        sys.exit(1)
    except subprocess.CalledProcessError as e:
        sys.exit(e.returncode)

if __name__ == "__main__":
    main()
