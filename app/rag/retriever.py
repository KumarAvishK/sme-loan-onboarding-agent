"""Resilient local retrieval for the EXL Bank SME lending demo.

Chroma is optional: if it cannot initialize in a hosted environment, use a
small deterministic keyword retriever rather than failing application startup.
The knowledge base contains synthetic/demo policy text only.
"""
from __future__ import annotations

from typing import Optional
from langchain_core.tools import tool
from app.sample_data import KNOWLEDGE_DOCS

try:  # Do not make a vector-store installation a hard startup dependency.
    import chromadb
except Exception:  # pragma: no cover - exercised on hosts without Chroma
    chromadb = None


class CreditPolicyRetriever:
    def __init__(self):
        self.client = None
        self.collection = None
        if chromadb is None:
            return
        try:
            # In-memory storage avoids write-permission and persistent-path issues
            # on Streamlit Community Cloud and keeps the demo self-contained.
            self.client = chromadb.Client()
            self.collection = self.client.get_or_create_collection(name="sme_credit_knowledge")
            existing = self.collection.get()
            existing_ids = set(existing.get("ids") or [])
            docs_to_add = [d for d in KNOWLEDGE_DOCS if d["id"] not in existing_ids]
            if docs_to_add:
                self.collection.add(
                    ids=[d["id"] for d in docs_to_add],
                    documents=[d["text"] for d in docs_to_add],
                    metadatas=[{"title": d["title"]} for d in docs_to_add],
                )
        except Exception:
            # Fall back to deterministic retrieval if Chroma cannot initialize.
            self.client = None
            self.collection = None

    def retrieve(self, query: str, top_k: int = 3) -> str:
        if self.collection is not None:
            try:
                result = self.collection.query(query_texts=[query], n_results=max(1, int(top_k)))
                docs = result.get("documents", [[]])[0]
                metas = result.get("metadatas", [[]])[0]
                if docs:
                    return "\n\n".join(
                        f"[{m.get('title', 'Knowledge')}] {d}" for d, m in zip(docs, metas)
                    )
            except Exception:
                pass
        # Simple token-overlap fallback; never fabricates policy facts.
        tokens = {t.lower() for t in query.split() if len(t) > 2}
        ranked = []
        for doc in KNOWLEDGE_DOCS:
            text = str(doc.get("text", ""))
            title = str(doc.get("title", "Knowledge"))
            haystack = f"{title} {text}".lower()
            score = sum(1 for token in tokens if token in haystack)
            ranked.append((score, title, text))
        ranked.sort(key=lambda item: item[0], reverse=True)
        selected = [item for item in ranked[:max(1, int(top_k))] if item[0] > 0]
        if not selected:
            selected = ranked[:max(1, int(top_k))]
        return "\n\n".join(f"[{title}] {text}" for _, title, text in selected) or "No relevant policy context found."


_retriever: Optional[CreditPolicyRetriever] = None


def _get_retriever() -> CreditPolicyRetriever:
    global _retriever
    if _retriever is None:
        _retriever = CreditPolicyRetriever()
    return _retriever


@tool
def retrieve_credit_policy(query: str, top_k: int = 3) -> str:
    """Retrieve relevant SME credit-policy and SOP context from local demo documents."""
    return _get_retriever().retrieve(query, top_k)
