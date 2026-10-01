import chromadb
from langchain_core.tools import tool
from app.sample_data import KNOWLEDGE_DOCS


class CreditPolicyRetriever:
    def __init__(self, path: str = "./chroma_sme_loan"):
        self.client = chromadb.PersistentClient(path=path)
        self.collection = self.client.get_or_create_collection(name="sme_credit_knowledge")
        existing = self.collection.get()
        if existing.get("ids"):
            self.collection.delete(ids=existing["ids"])
        self.collection.add(
            ids=[d["id"] for d in KNOWLEDGE_DOCS],
            documents=[d["text"] for d in KNOWLEDGE_DOCS],
            metadatas=[{"title": d["title"]} for d in KNOWLEDGE_DOCS],
        )

    def retrieve(self, query: str, top_k: int = 3) -> str:
        result = self.collection.query(query_texts=[query], n_results=top_k)
        docs = result.get("documents", [[]])[0]
        metas = result.get("metadatas", [[]])[0]
        return "\n\n".join(
            f"[{m.get('title', 'Knowledge')}] {d}" for d, m in zip(docs, metas)
        ) or "No relevant policy context found."


_retriever = CreditPolicyRetriever()


@tool
def retrieve_credit_policy(query: str, top_k: int = 3) -> str:
    """Retrieve relevant SME credit-policy and SOP context."""
    return _retriever.retrieve(query, top_k)
