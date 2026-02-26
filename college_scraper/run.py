"""
run.py
======
All-in-one launcher:
  1. Starts the mock college HTTP server (port 8765)
  2. Runs the `local_colleges` Scrapy spider
  3. Shuts down the mock server
  4. Prints a ranked summary of scraped files

Usage:
    python run.py
"""
import glob
import json
import os
import signal
import subprocess
import sys
import time


def main() -> None:
    project_dir = os.path.dirname(os.path.abspath(__file__))
    venv_python = os.path.join(project_dir, ".venv", "bin", "python")
    python_exe  = venv_python if os.path.isfile(venv_python) else sys.executable
    output_dir  = os.path.join(project_dir, "output")
    os.makedirs(output_dir, exist_ok=True)

    print("=" * 65)
    print("  College Scraper  --  Scrapy Project")
    print("  Scraping Top-20 Indian Engineering Colleges")
    print("=" * 65)

    # 1. Start mock server ────────────────────────────────────────────────
    print("\n[1/3] Starting local mock college data server ...")
    # Clean output dir
    for f in glob.glob(os.path.join(output_dir, "*.json")):
        os.remove(f)

    server_proc = subprocess.Popen(
        [python_exe, "mock_server/server.py", "--port", "8765"],
        cwd=project_dir,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    time.sleep(1.5)
    print(f"      Mock server PID {server_proc.pid}  ->  http://127.0.0.1:8765/")

    # 2. Run spider ───────────────────────────────────────────────────────
    print("\n[2/3] Running Scrapy spider  (local_colleges) ...\n")
    start_all = time.time()
    spider_result = subprocess.run(
        [python_exe, "-m", "scrapy", "crawl", "local_colleges"],
        cwd=project_dir,
    )
    total_time = time.time() - start_all

    # 3. Stop mock server ─────────────────────────────────────────────────
    print("\n[3/3] Stopping mock server ...")
    try:
        server_proc.send_signal(signal.SIGTERM)
        server_proc.wait(timeout=5)
    except Exception:
        server_proc.kill()

    # Summary ─────────────────────────────────────────────────────────────
    files = sorted(glob.glob(os.path.join(output_dir, "*.json")))
    print()
    print("-" * 80)
    print(f"  Done!  Scraped {len(files)} colleges in {total_time:.2f}s  ->  output/")
    print("-" * 80)
    print(f"  {'NIRF':<7} {'CONFERENCE TIME':<10} {'COLLEGE NAME':<40} {'AVG CTC':<10}")
    print("-" * 80)
    for fp in files:
        try:
            with open(fp) as fh:
                data = json.load(fh)
            name = data.get("college_name", "?")
            duration = data.get("scrape_duration", 0)
            nirf = next(
                (d["value"] for d in data.get("additional_details", [])
                 if "NIRF Ranking (Engineering)" in d.get("category", "")),
                "N/A",
            )
            avg_pkg = next(
                (s["value"] for s in data.get("student_statistics", [])
                 if "Average package" in s.get("category", "")),
                "N/A",
            )
            print(f"  #{str(nirf):<6} {duration:7.4f}s  {name:<40}  {avg_pkg}")
        except Exception:
            print(f"  ?  {fp}")
    print()
    if spider_result.returncode != 0:
        print(f"[WARNING] Spider exit code: {spider_result.returncode}")


if __name__ == "__main__":
    main()
