from __future__ import annotations

import argparse
import json

from dotenv import load_dotenv

from .analyzer import HeuristicChunkAnalyzer
from .pipeline import IngestionPipeline
from .repository import get_knowledge_repository


def main():
    load_dotenv()
    parser = argparse.ArgumentParser(description="Ingest an EPUB into AstroSpace knowledge")
    parser.add_argument("epub")
    parser.add_argument("--storage-path", required=True)
    parser.add_argument("--source-key")
    parser.add_argument("--start-section", type=int, default=0)
    parser.add_argument("--max-sections", type=int)
    parser.add_argument("--heuristic", action="store_true",
                        help="Skip LLM analysis; generated chunks require review")
    args = parser.parse_args()
    pipeline = IngestionPipeline(
        get_knowledge_repository(),
        analyzer=HeuristicChunkAnalyzer() if args.heuristic else None,
    )
    result = pipeline.ingest(
        args.epub,
        storage_path=args.storage_path,
        source_key=args.source_key,
        start_section=args.start_section,
        max_sections=args.max_sections,
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
