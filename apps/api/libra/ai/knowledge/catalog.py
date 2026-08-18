"""Knowledge catalogue.

Documents are declared in ``knowledge/registry.json`` together with their
governance metadata (type, language, version, audience) instead of being
discovered by directory scan. Adapted from the reference project's registry
idea and extended with the fields a bank needs in order to answer "which
version of which document produced this answer?".
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Sequence

from libra.ai.knowledge.indexing import content_checksum
from libra.ai.knowledge.models import Audience, DocumentType, KnowledgeDocument
from libra.core.errors import ConfigurationError

LOGGER = logging.getLogger("libra.ai.knowledge")

REGISTRY_FILE = "registry.json"


class KnowledgeCatalog:
    """Loads registered documents from a knowledge directory."""

    def __init__(self, root: Path) -> None:
        self._root = Path(root)

    def load(self) -> Sequence[KnowledgeDocument]:
        registry_path = self._root / REGISTRY_FILE
        if not registry_path.exists():
            raise ConfigurationError(f"Knowledge registry not found: {registry_path}")

        try:
            raw = json.loads(registry_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as error:
            raise ConfigurationError("The knowledge registry is not valid JSON.") from error

        entries = raw.get("documents", []) if isinstance(raw, dict) else raw
        if not isinstance(entries, list):
            raise ConfigurationError("The knowledge registry must contain a document list.")

        documents: list[KnowledgeDocument] = []
        for entry in entries:
            document = self._load_document(entry)
            if document is not None:
                documents.append(document)
        return tuple(documents)

    def _load_document(self, entry: dict[str, Any]) -> KnowledgeDocument | None:
        document_id = str(entry.get("id", "")).strip()
        path_value = str(entry.get("path", "")).strip()
        if not document_id or not path_value:
            LOGGER.warning("knowledge.entry_incomplete", extra={"event_data": {"entry": entry}})
            return None

        path = self._root / path_value
        if not path.is_file():
            LOGGER.warning(
                "knowledge.file_missing",
                extra={"event_data": {"document_id": document_id, "path": path_value}},
            )
            return None

        content = path.read_text(encoding="utf-8").strip()
        if not content:
            return None

        return KnowledgeDocument(
            document_id=document_id,
            title=str(entry.get("title", document_id)),
            document_type=DocumentType(entry.get("document_type", DocumentType.FAQ.value)),
            language=str(entry.get("language", "en")),
            content=content,
            version=str(entry.get("version", "1")),
            audience=Audience(entry.get("audience", Audience.CUSTOMER.value)),
            source=path_value,
            checksum=content_checksum(content),
            metadata={"tags": entry.get("tags", [])},
        )
