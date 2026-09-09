"""
Verified RAG Retriever for Official Legal Provisions and Emergency Support.
Enforces zero hallucination by selecting only validated government provisions.
"""

import re
import logging
from typing import List, Optional, Tuple
from .knowledge_base import VERIFIED_KNOWLEDGE_DOCUMENTS, KnowledgeDocument

logger = logging.getLogger(__name__)


class VerifiedRAGRetriever:
    """
    Precision retriever for official statutory provisions and emergency helplines.
    """

    def __init__(self, documents: Optional[List[KnowledgeDocument]] = None):
        self.documents = documents or VERIFIED_KNOWLEDGE_DOCUMENTS

    def retrieve_context(
        self,
        query: str,
        risk_level: str = "LOW",
        language_code: str = "or-IN",
        top_k: int = 2
    ) -> str:
        """
        Retrieves the most relevant verified document text formatted for LLM system prompt injection.
        """
        scored_docs = self.rank_documents(query, risk_level)
        if not scored_docs:
            return ""

        top_docs = [doc for doc, score in scored_docs[:top_k]]
        snippets = []

        is_odia = "or" in language_code.lower()

        for doc in top_docs:
            if is_odia and doc.content_odia:
                content = doc.content_odia
            else:
                content = doc.content
            
            snippets.append(
                f"- [Doc: {doc.id} | {doc.title} | Source: {doc.source}]\n  {content}"
            )

        return "\n\n".join(snippets)

    def rank_documents(
        self,
        query: str,
        risk_level: str
    ) -> List[Tuple[KnowledgeDocument, float]]:
        """
        Ranks verified knowledge documents based on lexical match, query keywords,
        and current triage risk level.
        """
        tokens = set(re.findall(r"\w+", query.lower()))
        scored = []

        for doc in self.documents:
            score = 0.0

            # 1. Direct keyword match
            matches = sum(1 for kw in doc.keywords if kw in query.lower() or kw in tokens)
            score += matches * 2.0

            # 2. Risk-level category alignment
            if risk_level in ["CRITICAL", "HIGH"]:
                if doc.category == "emergency":
                    score += 5.0
                elif doc.id == "POA-SEC-15A-RIGHTS":
                    score += 3.0
            elif risk_level == "MODERATE":
                if doc.category in ["legal", "counselling"]:
                    score += 3.0
            else:
                if doc.id == "NHAA-14566-CORE" or doc.category == "scheme":
                    score += 2.0

            if score > 0:
                scored.append((doc, score))

        scored.sort(key=lambda x: x[1], reverse=True)
        return scored
