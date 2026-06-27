"""
BountyRAG — persistent ChromaDB store with BM25 fallback.
Venv: /home/altave/venv
"""
from __future__ import annotations
import sys, json, hashlib, time
from pathlib import Path

VENV_SITE = "/home/altave/venv/lib/python3.12/site-packages"
if VENV_SITE not in sys.path:
    sys.path.insert(0, VENV_SITE)

import chromadb
from chromadb.utils import embedding_functions
from rank_bm25 import BM25Okapi

RAG_DIR   = Path(__file__).parent
DATA_DIR  = RAG_DIR / "data"
CHROMA_DB = DATA_DIR / "chroma_db"

COLLECTIONS = [
    "mitre_attack",    # ATT&CK techniques / tactics / subtechniques
    "mitre_defend",    # D3FEND defensive countermeasures
    "bb_writeups",     # Bug-bounty public writeups
    "pentest_kb",      # The elite cybersec system-prompt knowledge base
    "cysa_kb",         # CySA+ concepts
    "bounty_reports",  # User-added / retroalimenta as new bounties come in
]

def _hash(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()[:16]

class BountyRAG:
    """
    Thin wrapper over ChromaDB (ONNX default embeddings, no GPU needed).
    Falls back to BM25 keyword search when ChromaDB is cold (empty collection).
    """

    def __init__(self):
        CHROMA_DB.mkdir(parents=True, exist_ok=True)
        self.client = chromadb.PersistentClient(path=str(CHROMA_DB))
        self._ef   = embedding_functions.DefaultEmbeddingFunction()
        self._cols = {}
        for name in COLLECTIONS:
            self._cols[name] = self.client.get_or_create_collection(
                name=name,
                embedding_function=self._ef,
                metadata={"hnsw:space": "cosine"},
            )
        self._bm25_cache: dict[str, BM25Okapi] = {}

    # ------------------------------------------------------------------ #
    # Write                                                                #
    # ------------------------------------------------------------------ #

    def upsert(
        self,
        collection: str,
        text: str,
        metadata: dict,
        doc_id: str | None = None,
    ) -> str:
        col = self._cols[collection]
        doc_id = doc_id or _hash(text)
        col.upsert(ids=[doc_id], documents=[text], metadatas=[metadata])
        self._bm25_cache.pop(collection, None)   # invalidate BM25 cache
        return doc_id

    def upsert_batch(
        self,
        collection: str,
        items: list[tuple[str, dict]],          # [(text, metadata), ...]
        batch_size: int = 100,
    ) -> list[str]:
        col = self._cols[collection]
        ids, docs, metas = [], [], []
        for text, meta in items:
            doc_id = _hash(text)
            ids.append(doc_id); docs.append(text); metas.append(meta)

        for i in range(0, len(ids), batch_size):
            col.upsert(
                ids=ids[i:i+batch_size],
                documents=docs[i:i+batch_size],
                metadatas=metas[i:i+batch_size],
            )
        self._bm25_cache.pop(collection, None)
        return ids

    # ------------------------------------------------------------------ #
    # Read                                                                 #
    # ------------------------------------------------------------------ #

    def query(
        self,
        query_text: str,
        collections: list[str] | None = None,
        n_results: int = 8,
        where: dict | None = None,
    ) -> list[dict]:
        """
        Semantic search across one or more collections.
        Returns list of {source, text, metadata, score} sorted by relevance.
        """
        target_cols = collections or COLLECTIONS
        results: list[dict] = []

        for col_name in target_cols:
            col = self._cols.get(col_name)
            if col is None:
                continue
            count = col.count()
            if count == 0:
                continue
            kw = {"query_texts": [query_text], "n_results": min(n_results, count)}
            if where:
                kw["where"] = where
            r = col.query(**kw, include=["documents", "metadatas", "distances"])
            for doc, meta, dist in zip(
                r["documents"][0], r["metadatas"][0], r["distances"][0]
            ):
                results.append({
                    "source":   col_name,
                    "text":     doc,
                    "metadata": meta,
                    "score":    round(1 - dist, 4),  # cosine similarity
                })

        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:n_results]

    def keyword_search(
        self,
        query_text: str,
        collections: list[str] | None = None,
        n_results: int = 8,
    ) -> list[dict]:
        """BM25 keyword fallback — useful for exact CVE IDs, technique IDs, etc."""
        target_cols = collections or COLLECTIONS
        all_results: list[dict] = []

        for col_name in target_cols:
            col = self._cols.get(col_name)
            if col is None or col.count() == 0:
                continue

            # build BM25 index lazily per collection
            if col_name not in self._bm25_cache:
                data = col.get(include=["documents", "metadatas"])
                corpus = data["documents"]
                self._bm25_cache[col_name] = (
                    BM25Okapi([d.lower().split() for d in corpus]),
                    corpus,
                    data["metadatas"],
                )

            bm25, corpus, metas = self._bm25_cache[col_name]
            scores = bm25.get_scores(query_text.lower().split())
            ranked = sorted(
                enumerate(scores), key=lambda x: x[1], reverse=True
            )[:n_results]

            for idx, sc in ranked:
                if sc > 0:
                    all_results.append({
                        "source":   col_name,
                        "text":     corpus[idx],
                        "metadata": metas[idx],
                        "score":    round(sc, 4),
                    })

        all_results.sort(key=lambda x: x["score"], reverse=True)
        return all_results[:n_results]

    # ------------------------------------------------------------------ #
    # Stats                                                                #
    # ------------------------------------------------------------------ #

    def stats(self) -> dict:
        return {name: self._cols[name].count() for name in COLLECTIONS}


# Singleton
_rag: BountyRAG | None = None

def get_rag() -> BountyRAG:
    global _rag
    if _rag is None:
        _rag = BountyRAG()
    return _rag
