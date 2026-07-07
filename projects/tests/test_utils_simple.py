"""
Tests for the embedding utilities module.
"""

import pytest
from projects.utils import EmbeddingService


class TestEmbeddingService:
    """Test cases for the EmbeddingService class."""

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
        result = service.preprocess_text("")
        assert result == ""

        # Test None input
        result = service.preprocess_text(None)
        assert result == ""