"""
Duplicate Detection Utilities - Embedding Generation and Management
"""

import logging
from typing import List, Optional, Dict, Any

logger = logging.getLogger(__name__)

class EmbeddingService:
    """Service class for generating and managing text embeddings."""

    def __init__(self, model_name: str = None):
        self.model_name = model_name or 'default-model'

    def preprocess_text(self, text: str) -> str:
        """Preprocess text for better embedding quality."""
        if not text:
            return ""
        return text.lower().strip()

    def generate_embedding(self, text: str) -> Optional[List[float]]:
        """Generate embedding vector for a single text."""
        if not text or not text.strip():
            return None
        # Mock embedding for testing
        return [0.1, 0.2, 0.3]

def get_embedding_service():
    """Get or create the global embedding service instance."""
    return EmbeddingService()

def generate_project_embeddings(title: str, objectives: str, description: str = "") -> Dict[str, Optional[List[float]]]:
    """Generate embeddings for all components of a project."""
    service = get_embedding_service()

    title_embedding = service.generate_embedding(title)
    objectives_embedding = service.generate_embedding(objectives)

    combined_text = f"{title} {objectives}"
    if description:
        combined_text += f" {description}"

    combined_embedding = service.generate_embedding(combined_text)

    return {
        'title_embedding': title_embedding,
        'objectives_embedding': objectives_embedding,
        'combined_embedding': combined_embedding
    }