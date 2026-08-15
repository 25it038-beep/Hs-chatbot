"""HSBot retrieval pipeline.

Modular: /router /search /fetcher /cache /ranker /extractor /image-search
/news-search /security /streaming /observability — see orchestrator.py.
"""

from .config import retrieval_config
from .orchestrator import RetrievalResult, RetrievalOrchestrator, retrieval_orchestrator

__all__ = [
    "retrieval_config",
    "RetrievalResult",
    "RetrievalOrchestrator",
    "retrieval_orchestrator",
]
