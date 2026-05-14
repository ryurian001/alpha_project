from __future__ import annotations

import argparse
import json
import logging
import subprocess
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
LOG_DIR = PROJECT_ROOT / "logs"
LOG_PATH = LOG_DIR / "rag_pipeline.log"


def setup_logging() -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        handlers=[
            logging.FileHandler(LOG_PATH, encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Production RAG pipeline operations.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("crawl", help="Run crawler only.")
    subparsers.add_parser("preprocess", help="Run preprocessing only.")
    subparsers.add_parser("rebuild-index", help="Rebuild FAISS index only.")
    subparsers.add_parser("refresh", help="Run crawl, preprocess, and index rebuild.")

    scheduled = subparsers.add_parser("scheduled-refresh", help="Run refresh periodically.")
    scheduled.add_argument("--interval-minutes", type=int, default=360)
    scheduled.add_argument("--max-runs", type=int, default=0, help="0 means run forever.")

    subparsers.add_parser("healthcheck", help="Print pipeline artifact health.")
    return parser.parse_args()


def run_step(name: str, command: list[str], cwd: Path = PROJECT_ROOT) -> None:
    started_at = time.perf_counter()
    logging.info("step.start name=%s command=%s", name, " ".join(command))
    try:
        subprocess.run(command, cwd=cwd, check=True)
    except subprocess.CalledProcessError:
        logging.exception("step.failed name=%s", name)
        raise
    logging.info("step.completed name=%s latency_ms=%.2f", name, (time.perf_counter() - started_at) * 1000)


def crawl() -> None:
    run_step("crawl", [sys.executable, "main.py"], cwd=PROJECT_ROOT / "crawler" / "movinggyu")


def preprocess() -> None:
    run_step("preprocess", [sys.executable, "preprocess/preprocess_notices.py"])


def rebuild_index() -> None:
    run_step("rebuild-index", [sys.executable, "vector_db/build_faiss_index.py"])


def refresh() -> None:
    crawl()
    preprocess()
    rebuild_index()


def scheduled_refresh(interval_minutes: int, max_runs: int) -> None:
    runs = 0
    while True:
        runs += 1
        try:
            refresh()
        except Exception:
            logging.exception("scheduled_refresh.failed run=%d", runs)
        if max_runs and runs >= max_runs:
            return
        time.sleep(interval_minutes * 60)


def healthcheck() -> None:
    artifacts = [
        PROJECT_ROOT / "crawler" / "movinggyu" / "kookmin_notices.json",
        PROJECT_ROOT / "data" / "clean" / "notices_clean.jsonl",
        PROJECT_ROOT / "data" / "chunks" / "notices_chunks.jsonl",
        PROJECT_ROOT / "vector_db" / "kmu_notice_index.faiss",
        PROJECT_ROOT / "vector_db" / "kmu_notice_store.pkl",
    ]
    report = []
    for artifact in artifacts:
        report.append(
            {
                "path": str(artifact.relative_to(PROJECT_ROOT)),
                "exists": artifact.exists(),
                "size_bytes": artifact.stat().st_size if artifact.exists() else 0,
                "updated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z", time.localtime(artifact.stat().st_mtime))
                if artifact.exists()
                else "",
            }
        )
    print(json.dumps(report, ensure_ascii=False, indent=2))


def main() -> None:
    setup_logging()
    args = parse_args()
    if args.command == "crawl":
        crawl()
    elif args.command == "preprocess":
        preprocess()
    elif args.command == "rebuild-index":
        rebuild_index()
    elif args.command == "refresh":
        refresh()
    elif args.command == "scheduled-refresh":
        scheduled_refresh(args.interval_minutes, args.max_runs)
    elif args.command == "healthcheck":
        healthcheck()


if __name__ == "__main__":
    main()
