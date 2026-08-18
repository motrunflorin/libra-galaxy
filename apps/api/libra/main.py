"""Command-line entry point.

``serve``            run the API
``indexes``          apply the declared MongoDB indexes
``knowledge-plan``   dry-run the RAG pipeline: catalogue -> chunking -> plan,
                     without calling the embedding provider
"""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

from libra.ai.knowledge.catalog import KnowledgeCatalog
from libra.ai.knowledge.chunking import ChunkingPolicy
from libra.core.config import get_settings
from libra.core.logging import setup_logging

KNOWLEDGE_DIR = Path(__file__).resolve().parents[1] / "knowledge"


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Libra Galaxy API")
    parser.add_argument(
        "command",
        nargs="?",
        choices=("serve", "indexes", "knowledge-plan"),
        default="serve",
    )
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--reload", action="store_true")
    return parser.parse_args()


async def _apply_indexes() -> None:
    from libra.core.persistence.mongo import MongoDatabaseProvider

    settings = get_settings()
    provider = MongoDatabaseProvider(settings.mongo)
    applied = await provider.ensure_indexes()
    await provider.close()
    print(f"Applied {applied} index specification(s).")


def _knowledge_plan() -> None:
    """Show what the RAG pipeline would do. No provider calls, no cost."""
    settings = get_settings()
    documents = KnowledgeCatalog(KNOWLEDGE_DIR).load()
    policy = ChunkingPolicy(
        size_tokens=settings.rag.chunk_size_tokens,
        overlap_tokens=settings.rag.chunk_overlap_tokens,
    )

    report = []
    for document in documents:
        chunks = policy.split(document)
        report.append(
            {
                "document_id": document.document_id,
                "language": document.language,
                "document_type": document.document_type.value,
                "version": document.version,
                "checksum": document.checksum[:12],
                "chunker": policy.chunker_for(document.document_type).name,
                "chunks": len(chunks),
            }
        )

    print(json.dumps({"documents": len(documents), "plan": report}, indent=2))


def main() -> None:
    args = _parse_args()
    settings = get_settings()
    setup_logging(settings.observability)

    if args.command == "indexes":
        asyncio.run(_apply_indexes())
        return

    if args.command == "knowledge-plan":
        _knowledge_plan()
        return

    import uvicorn

    uvicorn.run(
        "libra.app:create_app",
        factory=True,
        host=args.host,
        port=args.port,
        reload=args.reload,
    )


if __name__ == "__main__":
    main()
