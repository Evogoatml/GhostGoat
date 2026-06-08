"""
GhostGoat Conversation Memory
==============================

Stores every conversation turn as a vector embedding in ChromaDB.
On each query, retrieves the top-k most semantically relevant past turns
so the LLM always has useful context — not just the last N messages.

Compression
-----------
When a user's entry count exceeds COMPRESS_THRESHOLD (default 300),
the compressor groups entries older than COMPRESS_AGE_DAYS into daily
batches and asks the LLM to summarise each batch into one entry.
This keeps the memory bounded while preserving the important stuff.

Fallback
--------
If ChromaDB fails for any reason the system degrades gracefully to a
simple in-memory list (conversations still work, just no persistence).
"""

from __future__ import annotations

import json
import logging
import os
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# ── Tunables ──────────────────────────────────────────────────────────────────
COMPRESS_THRESHOLD = 120    # entries per user before compression runs
COMPRESS_AGE_DAYS  = 3      # only compress entries older than this
SUMMARY_TTL_DAYS   = 90     # delete summaries older than this
RETRIEVE_TOP_K     = 6      # relevant memories injected per query
MIN_ENTRY_LEN      = 12     # skip storing entries shorter than this (noise)
DEDUP_SIMILARITY   = 0.97   # cosine similarity above which we skip storing
MEMORY_DIR         = Path(os.path.expanduser("~")) / ".ghostgoat_chroma"


# ── Embedding helper (no sentence-transformers needed) ────────────────────────

def _cosine(a: List[float], b: List[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    return dot  # vectors are already L2-normalised


def _embed(text: str) -> List[float]:
    """
    Lightweight deterministic embedding using TF-IDF-style char n-grams.
    Produces a 256-dim vector.  Good enough for memory retrieval without
    requiring sentence-transformers.  Swappable for a real model later.
    """
    import hashlib, math
    DIM = 256
    vec = [0.0] * DIM
    text = text.lower()
    # 3-grams + 4-grams
    for n in (3, 4):
        for i in range(len(text) - n + 1):
            gram = text[i:i+n]
            h = int(hashlib.md5(gram.encode()).hexdigest(), 16) % DIM
            vec[h] += 1.0
    # L2 normalise
    mag = math.sqrt(sum(v*v for v in vec)) or 1.0
    return [v / mag for v in vec]


# ── Core memory class ─────────────────────────────────────────────────────────

class ConversationMemory:
    """Per-user semantic memory with automatic compression."""

    def __init__(self):
        self._chroma_client = None
        self._collections: Dict[str, object] = {}
        self._fallback: Dict[str, List[dict]] = {}   # in-memory fallback
        self._ready = False
        self._init_chroma()

    def _init_chroma(self):
        try:
            import chromadb
            from chromadb.config import Settings
            MEMORY_DIR.mkdir(parents=True, exist_ok=True)
            self._chroma_client = chromadb.PersistentClient(
                path=str(MEMORY_DIR),
                settings=Settings(anonymized_telemetry=False),
            )
            self._ready = True
            logger.info("[Memory] ChromaDB ready at %s", MEMORY_DIR)
        except Exception as e:
            logger.warning("[Memory] ChromaDB unavailable (%s) — using in-memory fallback", e)

    def _collection(self, user_id: str):
        """Get or create a ChromaDB collection for this user."""
        cid = f"user_{user_id.replace('-', '_')}"
        if cid not in self._collections:
            self._collections[cid] = self._chroma_client.get_or_create_collection(
                name=cid,
                metadata={"hnsw:space": "cosine"},
            )
        return self._collections[cid]

    # ── Public API ─────────────────────────────────────────────────────────────

    def _is_duplicate(self, user_id: str, vec: List[float]) -> bool:
        """Return True if a very similar entry already exists (dedup guard)."""
        if not self._ready:
            return False
        try:
            col = self._collection(user_id)
            if col.count() == 0:
                return False
            results = col.query(
                query_embeddings=[vec],
                n_results=1,
                include=["distances"],
            )
            distances = results.get("distances", [[]])[0]
            if distances:
                # ChromaDB cosine distance = 1 - similarity
                similarity = 1.0 - distances[0]
                return similarity >= DEDUP_SIMILARITY
        except Exception:
            pass
        return False

    def store(self, user_id: str, role: str, text: str, metadata: Optional[dict] = None):
        """Store a conversation turn."""
        if not text or not text.strip():
            return
        # Skip noise: very short entries (acks, single words)
        if len(text.strip()) < MIN_ENTRY_LEN:
            return
        entry_id = f"{user_id}_{int(time.time()*1000)}"
        ts = datetime.utcnow().isoformat()
        meta = {
            "user_id": user_id,
            "role": role,          # "user" | "assistant"
            "timestamp": ts,
            "day": ts[:10],        # YYYY-MM-DD  (used for compression grouping)
            "compressed": "false",
            **(metadata or {}),
        }

        vec = _embed(text)
        if self._ready:
            try:
                if self._is_duplicate(user_id, vec):
                    logger.debug("[Memory] Skipping near-duplicate entry for user %s", user_id)
                    return
                col = self._collection(user_id)
                col.add(
                    ids=[entry_id],
                    embeddings=[vec],
                    documents=[text],
                    metadatas=[meta],
                )
                return
            except Exception as e:
                logger.warning("[Memory] ChromaDB store failed: %s", e)

        # Fallback
        self._fallback.setdefault(user_id, []).append(
            {"id": entry_id, "text": text, "meta": meta}
        )

    def retrieve(self, user_id: str, query: str, k: int = RETRIEVE_TOP_K) -> List[str]:
        """Return the k most relevant past turns for this query."""
        if self._ready:
            try:
                col = self._collection(user_id)
                count = col.count()
                if count == 0:
                    return []
                results = col.query(
                    query_embeddings=[_embed(query)],
                    n_results=min(k, count),
                    include=["documents", "metadatas"],
                )
                docs = results.get("documents", [[]])[0]
                metas = results.get("metadatas", [[]])[0]
                out = []
                for doc, meta in zip(docs, metas):
                    role = meta.get("role", "?")
                    ts = meta.get("timestamp", "")[:16]
                    prefix = "[summary]" if meta.get("compressed") == "true" else f"[{role} {ts}]"
                    out.append(f"{prefix} {doc}")
                return out
            except Exception as e:
                logger.warning("[Memory] ChromaDB retrieve failed: %s", e)

        # Fallback: return last k entries
        entries = self._fallback.get(user_id, [])
        return [e["text"] for e in entries[-k:]]

    def count(self, user_id: str) -> int:
        if self._ready:
            try:
                return self._collection(user_id).count()
            except Exception:
                pass
        return len(self._fallback.get(user_id, []))

    def compress_if_needed(self, user_id: str, llm_call) -> Optional[str]:
        """
        Run compression if entry count > COMPRESS_THRESHOLD.
        Groups old entries by day, summarises each with the LLM,
        replaces them with a single compressed entry.
        Returns a status string or None if nothing was done.
        """
        if self.count(user_id) <= COMPRESS_THRESHOLD:
            return None

        logger.info("[Memory] Compression triggered for user %s", user_id)
        cutoff = (datetime.utcnow() - timedelta(days=COMPRESS_AGE_DAYS)).isoformat()

        if not self._ready:
            # Fallback: just trim to last 150 entries
            entries = self._fallback.get(user_id, [])
            if len(entries) > 150:
                self._fallback[user_id] = entries[-150:]
                return "Trimmed in-memory history to 150 entries."
            return None

        try:
            col = self._collection(user_id)

            # ── Prune stale summaries older than SUMMARY_TTL_DAYS ─────────────
            ttl_cutoff = (datetime.utcnow() - timedelta(days=SUMMARY_TTL_DAYS)).isoformat()
            try:
                stale = col.get(
                    where={"$and": [
                        {"compressed": {"$eq": "true"}},
                        {"timestamp": {"$lt": ttl_cutoff}},
                    ]},
                    include=["ids"],
                )
                stale_ids = stale.get("ids", [])
                if stale_ids:
                    col.delete(ids=stale_ids)
                    logger.info("[Memory] Pruned %d stale summaries for user %s", len(stale_ids), user_id)
            except Exception as e:
                logger.debug("[Memory] Stale summary pruning error: %s", e)

            # Fetch all old uncompressed entries
            results = col.get(
                where={"$and": [
                    {"timestamp": {"$lt": cutoff}},
                    {"compressed": {"$eq": "false"}},
                ]},
                include=["documents", "metadatas", "ids"],
            )

            ids      = results.get("ids", [])
            docs     = results.get("documents", [])
            metas    = results.get("metadatas", [])

            if not ids:
                return None

            # Group by day
            by_day: Dict[str, List[Tuple[str, str, str]]] = {}
            for doc, meta, eid in zip(docs, metas, ids):
                day = meta.get("day", "unknown")
                by_day.setdefault(day, []).append((eid, meta.get("role", "?"), doc))

            compressed_count = 0
            for day, entries in sorted(by_day.items()):
                convo_text = "\n".join(f"{role}: {text}" for _, role, text in entries)
                prompt = (
                    f"Summarise this conversation from {day} into 2-4 sentences, "
                    f"preserving key facts, decisions, and anything the user might want "
                    f"remembered.\n\nConversation:\n{convo_text[:4000]}"
                )
                try:
                    summary = llm_call(prompt).strip()
                except Exception:
                    summary = f"[{day}] Conversation summary unavailable."

                # Delete original entries
                entry_ids = [e[0] for e in entries]
                col.delete(ids=entry_ids)

                # Store the compressed summary
                summary_id = f"{user_id}_summary_{day}_{int(time.time())}"
                col.add(
                    ids=[summary_id],
                    embeddings=[_embed(summary)],
                    documents=[summary],
                    metadatas=[{
                        "user_id": user_id,
                        "role": "summary",
                        "timestamp": f"{day}T23:59:59",
                        "day": day,
                        "compressed": "true",
                        "original_count": str(len(entries)),
                    }],
                )
                compressed_count += len(entries)

            remaining = col.count()
            return (
                f"Compressed {compressed_count} entries from {len(by_day)} day(s) "
                f"into summaries. Memory now has {remaining} entries."
            )

        except Exception as e:
            logger.warning("[Memory] Compression failed: %s", e)
            return f"Compression error: {e}"

    def clear(self, user_id: str):
        """Wipe all memory for a user."""
        if self._ready:
            try:
                cid = f"user_{user_id.replace('-', '_')}"
                self._chroma_client.delete_collection(cid)
                self._collections.pop(cid, None)
                logger.info("[Memory] Cleared memory for user %s", user_id)
                return
            except Exception as e:
                logger.warning("[Memory] Clear failed: %s", e)
        self._fallback.pop(user_id, None)

    def stats(self, user_id: str) -> dict:
        count = self.count(user_id)
        return {
            "user_id": user_id,
            "entries": count,
            "compress_threshold": COMPRESS_THRESHOLD,
            "needs_compression": count > COMPRESS_THRESHOLD,
            "backend": "chromadb" if self._ready else "in-memory",
            "storage_path": str(MEMORY_DIR) if self._ready else "ram",
        }


# Singleton
conversation_memory = ConversationMemory()
