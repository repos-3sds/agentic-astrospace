"""Source-faithful knowledge ingestion for EPUB astrology texts."""

from .epub import EpubExtractor
from .pipeline import IngestionPipeline

__all__ = ["EpubExtractor", "IngestionPipeline"]
