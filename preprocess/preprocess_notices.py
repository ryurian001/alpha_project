"""Preprocess crawled Kookmin notice data for a RAG chatbot.

Input:
    JSON list made by crawler/movinggyu/main.py

Outputs:
    data/clean/notices_clean.jsonl
    data/chunks/notices_chunks.jsonl
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT_CANDIDATES = [
    PROJECT_ROOT / "data" / "raw" / "kookmin_notices.json",
    PROJECT_ROOT / "crawler" / "movinggyu" / "kookmin_notices.json",
    PROJECT_ROOT / "kookmin_notices.json",
]
DEFAULT_CLEAN_OUTPUT = PROJECT_ROOT / "data" / "clean" / "notices_clean.jsonl"
DEFAULT_CHUNK_OUTPUT = PROJECT_ROOT / "data" / "chunks" / "notices_chunks.jsonl"


ZERO_WIDTH_RE = re.compile(r"[\u200b\u200c\u200d\ufeff]")
SPACE_RE = re.compile(r"[ \t\r\f\v]+")
NEWLINE_RE = re.compile(r"\n{3,}")
URL_RE = re.compile(r"https?://\S+")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Clean and chunk Kookmin notice crawler JSON for RAG."
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=None,
        help="Path to kookmin_notices.json. Defaults to common project locations.",
    )
    parser.add_argument(
        "--clean-output",
        type=Path,
        default=DEFAULT_CLEAN_OUTPUT,
        help="Output path for cleaned JSONL notices.",
    )
    parser.add_argument(
        "--chunk-output",
        type=Path,
        default=DEFAULT_CHUNK_OUTPUT,
        help="Output path for chunked JSONL documents.",
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=900,
        help="Target chunk size in Korean/English characters.",
    )
    parser.add_argument(
        "--chunk-overlap",
        type=int,
        default=120,
        help="Characters to overlap between neighboring chunks.",
    )
    return parser.parse_args()


def resolve_input_path(input_path: Path | None) -> Path:
    if input_path:
        path = input_path if input_path.is_absolute() else PROJECT_ROOT / input_path
        if not path.exists():
            raise FileNotFoundError(f"Input file not found: {path}")
        return path

    for candidate in DEFAULT_INPUT_CANDIDATES:
        if candidate.exists():
            return candidate

    candidates = "\n".join(f"  - {path}" for path in DEFAULT_INPUT_CANDIDATES)
    raise FileNotFoundError(
        "Could not find crawler output JSON. Put kookmin_notices.json in one of:\n"
        f"{candidates}\n"
        "or pass --input PATH."
    )


def load_json(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8-sig") as file:
        data = json.load(file)

    if not isinstance(data, list):
        raise ValueError("Input JSON must be a list of notice objects.")

    return [item for item in data if isinstance(item, dict)]


def clean_text(value: Any) -> str:
    text = "" if value is None else str(value)
    text = text.replace("\xa0", " ")
    text = ZERO_WIDTH_RE.sub("", text)
    text = URL_RE.sub(" ", text)
    text = text.replace("·", " ")
    text = text.replace("•", " ")

    lines = []
    for line in text.splitlines():
        line = SPACE_RE.sub(" ", line).strip()
        if line:
            lines.append(line)

    cleaned = "\n".join(lines)
    cleaned = NEWLINE_RE.sub("\n\n", cleaned)
    return cleaned.strip()


def normalize_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []

    normalized = []
    seen = set()
    for item in value:
        text = clean_text(item)
        if text and text not in seen:
            normalized.append(text)
            seen.add(text)
    return normalized


def stable_id(*parts: str) -> str:
    joined = "\n".join(parts)
    return hashlib.sha1(joined.encode("utf-8")).hexdigest()[:16]


def clean_notice(item: dict[str, Any]) -> dict[str, Any] | None:
    title = clean_text(item.get("title"))
    content = clean_text(item.get("content"))
    url = clean_text(item.get("url"))

    if not title and not content:
        return None

    notice_id = stable_id(url, title, clean_text(item.get("date")))
    return {
        "id": notice_id,
        "source": clean_text(item.get("source")),
        "category": clean_text(item.get("category")),
        "title": title,
        "date": clean_text(item.get("date")),
        "url": url,
        "content": content,
        "attachments": normalize_list(item.get("attachments")),
        "attached_links": normalize_list(item.get("attached_links")),
        "attached_images": normalize_list(item.get("attached_images")),
    }


def build_document_text(notice: dict[str, Any]) -> str:
    parts = [
        f"제목: {notice['title']}",
        f"출처: {notice['source']}" if notice["source"] else "",
        f"분류: {notice['category']}" if notice["category"] else "",
        f"날짜: {notice['date']}" if notice["date"] else "",
        "",
        notice["content"],
    ]
    return "\n".join(part for part in parts if part).strip()


def split_into_paragraphs(text: str) -> list[str]:
    paragraphs = []
    for block in re.split(r"\n{2,}", text):
        block = block.strip()
        if not block:
            continue
        paragraphs.extend(line.strip() for line in block.splitlines() if line.strip())
    return paragraphs


def split_long_text(text: str, chunk_size: int) -> list[str]:
    return [text[start : start + chunk_size] for start in range(0, len(text), chunk_size)]


def chunk_text(text: str, chunk_size: int, overlap: int) -> list[str]:
    if chunk_size <= 0:
        raise ValueError("--chunk-size must be greater than 0.")
    if overlap < 0 or overlap >= chunk_size:
        raise ValueError("--chunk-overlap must be 0 or greater and smaller than --chunk-size.")

    chunks = []
    current = ""
    paragraphs = split_into_paragraphs(text)

    for paragraph in paragraphs:
        paragraph_parts = (
            split_long_text(paragraph, chunk_size)
            if len(paragraph) > chunk_size
            else [paragraph]
        )

        for part in paragraph_parts:
            if not current:
                current = part
                continue

            candidate = f"{current}\n{part}"
            if len(candidate) <= chunk_size:
                current = candidate
            else:
                chunks.append(current.strip())
                prefix = current[-overlap:].strip() if overlap else ""
                current = f"{prefix}\n{part}".strip() if prefix else part

    if current.strip():
        chunks.append(current.strip())

    return chunks


def make_chunks(
    notices: list[dict[str, Any]], chunk_size: int, overlap: int
) -> list[dict[str, Any]]:
    chunks = []
    for notice in notices:
        document_text = build_document_text(notice)
        for index, chunk in enumerate(chunk_text(document_text, chunk_size, overlap)):
            chunks.append(
                {
                    "chunk_id": f"{notice['id']}_{index:03d}",
                    "notice_id": notice["id"],
                    "chunk_index": index,
                    "text": chunk,
                    "metadata": {
                        "source": notice["source"],
                        "category": notice["category"],
                        "title": notice["title"],
                        "date": notice["date"],
                        "url": notice["url"],
                    },
                }
            )
    return chunks


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as file:
        for row in rows:
            file.write(json.dumps(row, ensure_ascii=False) + "\n")


def deduplicate_notices(notices: list[dict[str, Any]]) -> list[dict[str, Any]]:
    deduplicated = []
    seen = set()
    for notice in notices:
        key = notice["url"] or notice["id"]
        if key in seen:
            continue
        deduplicated.append(notice)
        seen.add(key)
    return deduplicated


def main() -> None:
    args = parse_args()
    input_path = resolve_input_path(args.input)

    raw_items = load_json(input_path)
    cleaned = [notice for item in raw_items if (notice := clean_notice(item))]
    cleaned = deduplicate_notices(cleaned)
    chunks = make_chunks(cleaned, args.chunk_size, args.chunk_overlap)

    write_jsonl(args.clean_output, cleaned)
    write_jsonl(args.chunk_output, chunks)

    print(f"Input: {input_path}")
    print(f"Clean notices: {len(cleaned)} -> {args.clean_output}")
    print(f"Chunks: {len(chunks)} -> {args.chunk_output}")


if __name__ == "__main__":
    main()
