"""
Tests for the embedding utilities module.

This module tests the core embedding functionality including:
- Text preprocessing
- Embedding generation
- Cosine similarity calculations
- Batch operations
"""

import pytest
import numpy as np
from unittest.mock import patch, MagicMock
from projects.utils import EmbeddingService, get_embedding_service, generate_project_embeddings


class TestEmbeddingService:
    """Test cases for the EmbeddingService class."""

    @pytest.fixture
    def mock_sentence_transformer(self):
        """Mock SentenceTransformer for testing."""
        with patch('projects.utils.SentenceTransformer') as mock_st:
            mock_model = MagicMock()
            # Mock encode method to return numpy array - single embedding should be 1D
            mock_model.encode.return_value = np.array([0.1, 0.2, 0.3, 0.4])
            mock_model.get_sentence_embedding_dimension.return_value = 4
            mock_model.get_max_seq_length.return_value = 512
            mock_model.device = 'cpu'
            mock_st.return_value = mock_model
            yield mock_model

    def test_initialization(self, mock_sentence_transformer):
        """Test that EmbeddingService initializes correctly."""
        service = EmbeddingService('test-model')
        assert service.model_name == 'test-model'
        assert hasattr(service, 'model')

    def test_preprocess_text(self):
        """Test text preprocessing functionality."""
        service = EmbeddingService.__new__(EmbeddingService)  # Create without __init__

        # Test basic preprocessing
        text = "  Hello   World!   "
        result = service.preprocess_text(text)
        assert result == "hello world"

        # Test with special characters
        text = "Machine Learning & AI!!!"
        result = service.preprocess_text(text)
        assert result == "machine learning ai"

        # Test empty text
        assert service.preprocess_text("") == ""
        assert service.preprocess_text(None) == ""

    def test_generate_embedding_success(self, mock_sentence_transformer):
        """Test successful embedding generation."""
        service = EmbeddingService('test-model')

        result = service.generate_embedding("Test text")
        assert result == [0.1, 0.2, 0.3, 0.4]
        service.model.encode.assert_called_once()

    def test_generate_embedding_empty_text(self, mock_sentence_transformer):
        """Test embedding generation with empty text."""
        service = EmbeddingService('test-model')

        result = service.generate_embedding("")
        assert result is None

        result = service.generate_embedding("   ")
        assert result is None

    def test_generate_multiple_embeddings(self, mock_sentence_transformer):
        """Test batch embedding generation."""
        service = EmbeddingService('test-model')

        # Mock batch encoding
        service.model.encode.return_value = np.array([
            [0.1, 0.2, 0.3, 0.4],
            [0.5, 0.6, 0.7, 0.8]
        ])

        texts = ["Text 1", "Text 2"]
        result = service.generate_multiple_embeddings(texts)

        assert len(result) == 2
        assert result[0] == [0.1, 0.2, 0.3, 0.4]
        assert result[1] == [0.5, 0.6, 0.7, 0.8]

    def test_generate_multiple_embeddings_empty(self, mock_sentence_transformer):
        """Test batch embedding with empty texts."""
        service = EmbeddingService('test-model')

        result = service.generate_multiple_embeddings([])
        assert result == []

        result = service.generate_multiple_embeddings(["", "   "])
        assert result == [None, None]

    def test_calculate_cosine_similarity(self):
        """Test cosine similarity calculation."""
        service = EmbeddingService.__new__(EmbeddingService)  # Create without __init__

        # Test identical vectors
        vec1 = [1.0, 0.0]
        vec2 = [1.0, 0.0]
        similarity = service.calculate_cosine_similarity(vec1, vec2)
        assert similarity == 1.0

        # Test orthogonal vectors
        vec1 = [1.0, 0.0]
        vec2 = [0.0, 1.0]
        similarity = service.calculate_cosine_similarity(vec1, vec2)
        assert similarity == 0.0

        # Test opposite vectors
        vec1 = [1.0, 0.0]
        vec2 = [-1.0, 0.0]
        similarity = service.calculate_cosine_similarity(vec1, vec2)
        assert similarity == 0.0

        # Test partial similarity
        vec1 = [1.0, 1.0]
        vec2 = [1.0, 0.5]
        similarity = service.calculate_cosine_similarity(vec1, vec2)
        assert 0.8 < similarity < 1.0

    def test_calculate_cosine_similarity_edge_cases(self):
        """Test cosine similarity with edge cases."""
        service = EmbeddingService.__new__(EmbeddingService)  # Create without __init__

        # Test with None inputs
        assert service.calculate_cosine_similarity(None, [1.0, 0.0]) == 0.0
        assert service.calculate_cosine_similarity([1.0, 0.0], None) == 0.0

        # Test with zero vectors
        assert service.calculate_cosine_similarity([0.0, 0.0], [1.0, 0.0]) == 0.0

    def test_get_model_info(self, mock_sentence_transformer):
        """Test getting model information."""
        service = EmbeddingService('test-model')

        info = service.get_model_info()
        assert info['model_name'] == 'test-model'
        assert info['embedding_dimension'] == 4
        assert info['max_seq_length'] == 512
        assert info['device'] == 'cpu'


class TestGlobalFunctions:
    """Test cases for global utility functions."""

    @patch('projects.utils.EmbeddingService')
    def test_get_embedding_service(self, mock_service_class):
        """Test getting the global embedding service."""
        mock_service = MagicMock()
        mock_service_class.return_value = mock_service

        # First call should create service
        service1 = get_embedding_service()
        assert service1 == mock_service
        mock_service_class.assert_called_once()

        # Second call should return same instance
        service2 = get_embedding_service()
        assert service2 == service1
        # Should not create new instance
        mock_service_class.assert_called_once()

    @patch('projects.utils.get_embedding_service')
    def test_generate_project_embeddings(self, mock_get_service):
        """Test generating embeddings for project components."""
        mock_service = MagicMock()
        mock_get_service.return_value = mock_service

        # Mock embedding generation
        mock_service.generate_embedding.side_effect = [
            [0.1, 0.2],  # title
            [0.3, 0.4],  # objectives
            [0.5, 0.6]   # combined
        ]

        result = generate_project_embeddings(
            title="Test Title",
            objectives="Test Objectives",
            description="Test Description"
        )

        assert 'title_embedding' in result
        assert 'objectives_embedding' in result
        assert 'combined_embedding' in result

        assert result['title_embedding'] == [0.1, 0.2]
        assert result['objectives_embedding'] == [0.3, 0.4]
        assert result['combined_embedding'] == [0.5, 0.6]

        # Verify generate_embedding was called 3 times
        assert mock_service.generate_embedding.call_count == 3