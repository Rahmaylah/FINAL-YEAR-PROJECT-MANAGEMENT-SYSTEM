"""
Tests for the similarity algorithms module.

This module tests the hybrid similarity scoring functionality including:
- Semantic similarity calculations
- Lexical similarity calculations
- Hybrid similarity combining
"""

import pytest
import numpy as np
from unittest.mock import patch, MagicMock
import projects.similarity as projects_similarity
from projects.similarity import SimilarityScorer, get_similarity_scorer


class TestSimilarityScorer:
    """Test cases for the SimilarityScorer class."""

    def test_initialization(self):
        """Test that SimilarityScorer initializes with correct defaults."""
        mock_settings = MagicMock()
        mock_settings.configured = True
        mock_settings.DUPLICATE_SEMANTIC_WEIGHT = 0.7
        mock_settings.DUPLICATE_LEXICAL_WEIGHT = 0.3
        mock_settings.DUPLICATE_SIMILARITY_THRESHOLD = 0.6
        mock_settings.DUPLICATE_AUTO_FLAG_THRESHOLD = 0.8

        with patch('projects.similarity.settings', new=mock_settings):
            scorer = SimilarityScorer(embedding_service=MagicMock())
            assert scorer.semantic_weight == 0.7
            assert scorer.lexical_weight == 0.3
            assert scorer.similarity_threshold == 0.6
            assert scorer.auto_flag_threshold == 0.8

    def test_invalid_weights(self):
        """Test that invalid weights raise ValueError."""
        mock_settings = MagicMock()
        mock_settings.configured = True
        mock_settings.DUPLICATE_SEMANTIC_WEIGHT = 0.8
        mock_settings.DUPLICATE_LEXICAL_WEIGHT = 0.3  # Sum != 1.0

        with patch('projects.similarity.settings', new=mock_settings):
            with pytest.raises(ValueError):
                SimilarityScorer(embedding_service=MagicMock())

    def test_calculate_semantic_similarity(self):
        """Test semantic similarity calculation."""
        with patch('projects.similarity.get_embedding_service') as mock_get_service:
            mock_service = MagicMock()
            mock_service.calculate_cosine_similarity.side_effect = [1.0, 0.0, 0.894427191]
            mock_get_service.return_value = mock_service
            scorer = SimilarityScorer()

            # Test identical vectors
            vec1 = [1.0, 0.0]
            vec2 = [1.0, 0.0]
            similarity = scorer.calculate_semantic_similarity(vec1, vec2)
            assert similarity == 1.0

            # Test orthogonal vectors
            vec1 = [1.0, 0.0]
            vec2 = [0.0, 1.0]
            similarity = scorer.calculate_semantic_similarity(vec1, vec2)
            assert similarity == 0.0

            # Test partial similarity
            vec1 = [1.0, 1.0]
            vec2 = [1.0, 0.5]
            similarity = scorer.calculate_semantic_similarity(vec1, vec2)
            assert 0.8 < similarity < 1.0

    @patch('projects.similarity.connection', new=MagicMock())
    def test_calculate_lexical_similarity(self):
        """Test lexical similarity calculation using PostgreSQL."""
        scorer = SimilarityScorer(embedding_service=MagicMock())

        # Mock cursor and similarity result
        projects_similarity.connection.cursor.return_value.__enter__.return_value = MagicMock(fetchone=MagicMock(return_value=(0.75,)))

        similarity = scorer.calculate_lexical_similarity("test text", "similar text")
        assert similarity == 0.75

    @patch('projects.similarity.connection', new=MagicMock())
    def test_calculate_lexical_similarity_fallback(self):
        """Test lexical similarity fallback when PostgreSQL fails."""
        scorer = SimilarityScorer(embedding_service=MagicMock())

        # Mock connection to raise exception
        projects_similarity.connection.cursor.side_effect = Exception("Database error")

        # Test with identical texts
        similarity = scorer.calculate_lexical_similarity("hello world", "hello world")
        assert similarity == 1.0

        # Test with partial overlap
        similarity = scorer.calculate_lexical_similarity("hello world", "hello python")
        assert similarity == pytest.approx(1 / 3)

        # Test with no overlap
        similarity = scorer.calculate_lexical_similarity("hello world", "goodbye universe")
        assert similarity == 0.0

    def test_calculate_hybrid_similarity(self):
        """Test hybrid similarity calculation."""
        scorer = SimilarityScorer(embedding_service=MagicMock())

        # Mock the individual similarity methods
        with patch.object(scorer, 'calculate_semantic_similarity', return_value=0.8):
            with patch.object(scorer, 'calculate_lexical_similarity', return_value=0.6):
                similarity = scorer.calculate_hybrid_similarity(
                    [1.0, 0.0], [0.9, 0.1], "text1", "text2"
                )

                # Expected: (0.7 * 0.8) + (0.3 * 0.6) = 0.56 + 0.18 = 0.74
                assert abs(similarity - 0.74) < 0.01

    def test_calculate_hybrid_similarity_no_embeddings(self):
        """Test hybrid similarity when embeddings are not available."""
        scorer = SimilarityScorer(embedding_service=MagicMock())

        with patch.object(scorer, 'calculate_lexical_similarity', return_value=0.7):
            similarity = scorer.calculate_hybrid_similarity(
                None, None, "text1", "text2"
            )

            # Should use lexical similarity for both components
            assert similarity == 0.7

    def test_get_similarity_stats(self):
        """Test getting similarity statistics."""
        mock_service = MagicMock()
        mock_service.get_model_info.return_value = {
            'model_name': 'test-model',
            'embedding_dimension': 768,
            'max_seq_length': 512,
            'device': 'cpu'
        }
        scorer = SimilarityScorer(embedding_service=mock_service)

        stats = scorer.get_similarity_stats()

        assert 'semantic_weight' in stats
        assert 'lexical_weight' in stats
        assert 'similarity_threshold' in stats
        assert 'auto_flag_threshold' in stats
        assert 'embedding_model' in stats

        assert stats['semantic_weight'] == 0.7
        assert stats['lexical_weight'] == 0.3


class TestGlobalFunctions:
    """Test cases for global utility functions."""

    @patch('projects.similarity.SimilarityScorer')
    def test_get_similarity_scorer(self, mock_scorer_class):
        """Test getting the global similarity scorer."""
        mock_scorer = MagicMock()
        mock_scorer_class.return_value = mock_scorer

        # First call should create scorer
        scorer1 = get_similarity_scorer()
        assert scorer1 == mock_scorer
        mock_scorer_class.assert_called_once()

        # Second call should return same instance
        scorer2 = get_similarity_scorer()
        assert scorer2 == scorer1
        # Should not create new instance
        mock_scorer_class.assert_called_once()