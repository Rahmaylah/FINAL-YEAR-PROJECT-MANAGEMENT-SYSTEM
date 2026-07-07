"""
Duplicate Detection Utilities - Embedding Generation and Management

This module provides the core embedding functionality for the duplicate detection system.
It handles text preprocessing, embedding generation using Sentence-BERT, and vector operations.
"""

import os
import logging
from typing import List, Optional, Dict, Any
from sentence_transformers import SentenceTransformer
import numpy as np
from django.conf import settings

logger = logging.getLogger(__name__)

class EmbeddingService:
    """
    Service class for generating and managing text embeddings using Sentence-BERT.

    This class provides methods to:
    - Generate embeddings from text
    - Preprocess text for better embeddings
    - Handle batch operations
    - Cache and reuse embeddings
    """

    def __init__(self, model_name: str = None):
        """
        Initialize the embedding service with a Sentence-BERT model.

        Args:
            model_name: Name of the Sentence-BERT model to use.
                       Defaults to 'sentence-transformers/all-mpnet-base-v2'
        """
        if model_name is None:
            model_name = getattr(settings, 'EMBEDDING_MODEL', 'sentence-transformers/all-mpnet-base-v2')

        try:
            self.model = SentenceTransformer(model_name)
            self.model_name = model_name
            logger.info(f"Loaded embedding model: {model_name}")
        except Exception as e:
            logger.error(f"Failed to load embedding model {model_name}: {e}")
            raise

    def preprocess_text(self, text: str) -> str:
        """
        Preprocess text for better embedding quality.

        Args:
            text: Raw text to preprocess

        Returns:
            Preprocessed text
        """
        if not text:
            return ""

        # Convert to lowercase
        text = text.lower()

        # Remove extra whitespace
        text = ' '.join(text.split())

        # Basic cleaning - remove special characters but keep meaningful punctuation
        # Keep: periods, commas, parentheses for technical terms
        # Remove: excessive symbols, quotes, etc.
        import re
        text = re.sub(r'[^\w\s.,()-]', ' ', text)

        # Normalize whitespace again
        text = ' '.join(text.split())

        return text.strip()

    def generate_embedding(self, text: str) -> Optional[List[float]]:
        """
        Generate embedding vector for a single text.
        ALWAYS RETURNS A LIST, NOT NUMPY ARRAY.

        Args:
            text: Text to embed

        Returns:
            List of floats representing the embedding vector, or None if failed
        """
        try:
            if not text or not text.strip():
                logger.warning("Empty text provided for embedding generation")
                return None

            # Preprocess the text
            processed_text = self.preprocess_text(text)

            if not processed_text:
                logger.warning("Text became empty after preprocessing")
                return None

            # Generate embedding as numpy array
            embedding = self.model.encode(processed_text, convert_to_numpy=True)

            # IMPORTANT: Convert numpy array to list immediately
            embedding_list = embedding.tolist()

            logger.debug(f"Generated embedding with {len(embedding_list)} dimensions")
            return embedding_list

        except Exception as e:
            logger.error(f"Failed to generate embedding for text: {e}")
            return None

    def generate_multiple_embeddings(self, texts: List[str]) -> List[Optional[List[float]]]:
        """
        Generate embeddings for multiple texts in batch.
        ALWAYS RETURNS LISTS, NOT NUMPY ARRAYS.

        Args:
            texts: List of texts to embed

        Returns:
            List of embedding vectors (or None for failed embeddings)
        """
        try:
            if not texts:
                return []

            # Preprocess all texts
            processed_texts = [self.preprocess_text(text) for text in texts]

            # Filter out empty texts
            valid_texts = []
            valid_indices = []

            for i, text in enumerate(processed_texts):
                if text and text.strip():
                    valid_texts.append(text)
                    valid_indices.append(i)

            if not valid_texts:
                logger.warning("No valid texts to embed")
                return [None] * len(texts)

            # Generate embeddings in batch
            embeddings = self.model.encode(valid_texts, convert_to_numpy=True, batch_size=32)

            # Convert to lists and map back to original positions
            result = [None] * len(texts)
            for i, embedding in enumerate(embeddings):
                original_index = valid_indices[i]
                # IMPORTANT: Convert numpy array to list
                result[original_index] = embedding.tolist()

            logger.info(f"Generated embeddings for {len(valid_texts)}/{len(texts)} texts")
            return result

        except Exception as e:
            logger.error(f"Failed to generate batch embeddings: {e}")
            return [None] * len(texts)

    def calculate_cosine_similarity(self, embedding1: List[float], embedding2: List[float]) -> float:
        """
        Calculate cosine similarity between two embedding vectors.

        Args:
            embedding1: First embedding vector
            embedding2: Second embedding vector

        Returns:
            Cosine similarity score between 0 and 1
        """
        try:
            if embedding1 is None or embedding2 is None:
                return 0.0
            if len(embedding1) == 0 or len(embedding2) == 0:
                return 0.0

            # Convert to numpy arrays for calculation
            vec1 = np.array(embedding1)
            vec2 = np.array(embedding2)

            # Calculate cosine similarity
            dot_product = np.dot(vec1, vec2)
            norm1 = np.linalg.norm(vec1)
            norm2 = np.linalg.norm(vec2)

            if norm1 == 0 or norm2 == 0:
                return 0.0

            similarity = dot_product / (norm1 * norm2)

            # Ensure result is between 0 and 1
            similarity = max(0.0, min(1.0, similarity))

            return float(similarity)

        except Exception as e:
            logger.error(f"Failed to calculate cosine similarity: {e}")
            return 0.0

    def get_model_info(self) -> Dict[str, Any]:
        """
        Get information about the current embedding model.

        Returns:
            Dictionary with model information
        """
        return {
            'model_name': self.model_name,
            'embedding_dimension': self.model.get_sentence_embedding_dimension(),
            'max_seq_length': self.model.get_max_seq_length(),
            'device': str(self.model.device)
        }


# Global service instance
_embedding_service = None

def get_embedding_service() -> EmbeddingService:
    """
    Get or create the global embedding service instance.

    Returns:
        EmbeddingService instance
    """
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService()
    return _embedding_service


def generate_project_embeddings(title: str, objectives: str, description: str = "") -> Dict[str, Optional[List[float]]]:
    """
    Generate embeddings for all components of a project.
    ALWAYS RETURNS LISTS, NOT NUMPY ARRAYS.

    Args:
        title: Project title
        objectives: Project objectives
        description: Project description (optional)

    Returns:
        Dictionary with embeddings for title, objectives, and combined text (all as lists)
    """
    service = get_embedding_service()

    # Generate individual embeddings (already return lists)
    title_embedding = service.generate_embedding(title)
    objectives_embedding = service.generate_embedding(objectives)

    # Generate combined embedding
    combined_text = f"{title} {objectives}"
    if description:
        combined_text += f" {description}"

    combined_embedding = service.generate_embedding(combined_text)

    return {
        'title_embedding': title_embedding,
        'objectives_embedding': objectives_embedding,
        'combined_embedding': combined_embedding
    }


def ensure_list_embedding(embedding):
    """
    Utility function to ensure an embedding is a list, not a numpy array.
    """
    if embedding is None:
        return None
    
    # If it's already a list, return it
    if isinstance(embedding, list):
        return embedding
    
    # If it's a numpy array, convert to list
    if isinstance(embedding, np.ndarray):
        return embedding.tolist()
    
    # If it has tolist method
    if hasattr(embedding, 'tolist'):
        try:
            return embedding.tolist()
        except Exception:
            pass
    
    # If it's a tuple
    if isinstance(embedding, tuple):
        return list(embedding)
    
    # Return as is
    return embedding