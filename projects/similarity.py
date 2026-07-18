"""
Duplicate Detection Similarity Algorithms

This module implements hybrid similarity scoring that combines:
- Semantic similarity using Sentence-BERT embeddings (cosine similarity)
- Lexical similarity using PostgreSQL trigram matching
- Configurable weights and thresholds for different similarity types
"""

import json
import logging
from typing import List, Dict, Optional, Tuple, Any
from django.db import connection
from django.conf import settings
from django.apps import apps
from django.utils import timezone
from .utils import get_embedding_service

logger = logging.getLogger(__name__)


class SimilarityScorer:
    """
    Service for calculating hybrid similarity scores between projects.

    Combines semantic similarity (embeddings) with lexical similarity (text matching)
    using configurable weights and thresholds.
    """

    def __init__(self, embedding_service=None):
        self._embedding_service = embedding_service

        # ====== FIXED: Higher thresholds for better accuracy ======
        if getattr(settings, 'configured', False):
            self.semantic_weight = getattr(settings, 'DUPLICATE_SEMANTIC_WEIGHT', 0.7)
            self.lexical_weight = getattr(settings, 'DUPLICATE_LEXICAL_WEIGHT', 0.3)
            self.similarity_threshold = getattr(settings, 'DUPLICATE_SIMILARITY_THRESHOLD', 0.4)
            self.auto_flag_threshold = getattr(settings, 'DUPLICATE_AUTO_FLAG_THRESHOLD', 0.5)
        else:
            self.semantic_weight = 0.7
            self.lexical_weight = 0.3
            self.similarity_threshold = 0.4
            self.auto_flag_threshold = 0.5
        
        self.search_years_back = getattr(settings, 'DUPLICATE_SEARCH_YEARS_BACK', 3) if getattr(settings, 'configured', False) else 3
        self.algorithm = getattr(settings, 'DUPLICATE_ALGORITHM', 'HYBRID') if getattr(settings, 'configured', False) else 'HYBRID'

        self._load_database_settings()

        # Validate weights
        if abs(self.semantic_weight + self.lexical_weight - 1.0) > 0.001:
            raise ValueError("Semantic and lexical weights must sum to 1.0")

    def _load_database_settings(self):
        try:
            if not apps.ready:
                return
            SystemSettings = apps.get_model('core', 'SystemSettings')
            settings_obj = SystemSettings.get_solo()
            self.search_years_back = settings_obj.duplicate_search_years_back
            self.similarity_threshold = settings_obj.duplicate_similarity_threshold
            self.auto_flag_threshold = settings_obj.duplicate_auto_flag_threshold
            self.algorithm = settings_obj.duplicate_algorithm
            self.semantic_weight = settings_obj.duplicate_semantic_weight
            self.lexical_weight = settings_obj.duplicate_lexical_weight
        except Exception as e:
            logger.debug(f"Using fallback similarity settings: {e}")

    @property
    def embedding_service(self):
        if self._embedding_service is None:
            self._embedding_service = get_embedding_service()
        return self._embedding_service

    def _normalize_embedding(self, embedding: Any) -> Optional[List[float]]:
        """
        Normalize different embedding input types into a list of floats.
        This handles numpy arrays, memoryview, JSON strings, etc.
        """
        if embedding is None:
            return None

        # Handle memoryview
        if isinstance(embedding, memoryview):
            embedding = list(embedding)

        # Handle numpy arrays
        try:
            import numpy as np
            if isinstance(embedding, np.ndarray):
                embedding = embedding.tolist()
        except ImportError:
            pass

        # Handle string (JSON)
        if isinstance(embedding, str):
            try:
                embedding = json.loads(embedding)
            except json.JSONDecodeError:
                return None

        # Handle tuple
        if isinstance(embedding, tuple):
            embedding = list(embedding)

        # Handle Django objects with tolist method
        if hasattr(embedding, 'tolist'):
            try:
                embedding = embedding.tolist()
            except Exception:
                pass

        # Ensure it's a list
        if not isinstance(embedding, list):
            return None

        # Convert all values to float
        try:
            return [float(x) for x in embedding if x is not None]
        except (TypeError, ValueError):
            return None

    def _to_pgvector_string(self, embedding: List[float]) -> str:
        """
        Convert embedding list to PostgreSQL vector string format.
        Example: [1.0, 2.0, 3.0] -> '[1.0,2.0,3.0]'
        """
        if embedding is None:
            return None
        embedding = self._normalize_embedding(embedding)
        if embedding is None or len(embedding) == 0:
            return None
        return '[' + ','.join(str(x) for x in embedding) + ']'

    def calculate_semantic_similarity(self, embedding1: List[float], embedding2: List[float]) -> float:
        """
        Calculate semantic similarity using cosine similarity of embeddings.

        Args:
            embedding1: First embedding vector
            embedding2: Second embedding vector

        Returns:
            Semantic similarity score (0.0 to 1.0)
        """
        embedding1 = self._normalize_embedding(embedding1)
        embedding2 = self._normalize_embedding(embedding2)

        if embedding1 is None or embedding2 is None:
            return 0.0
        if len(embedding1) == 0 or len(embedding2) == 0:
            return 0.0

        try:
            return self.embedding_service.calculate_cosine_similarity(embedding1, embedding2)
        except Exception as e:
            logger.warning(f"Failed to calculate semantic similarity: {e}")
            return 0.0

    def calculate_lexical_similarity(self, text1: str, text2: str) -> float:
        """
        Calculate lexical similarity using PostgreSQL trigram similarity.

        Args:
            text1: First text string
            text2: Second text string

        Returns:
            Lexical similarity score (0.0 to 1.0)
        """
        if not text1 or not text2:
            return 0.0

        try:
            with connection.cursor() as cursor:
                # ====== FIXED: Check if pg_trgm extension exists ======
                cursor.execute("""
                    SELECT EXISTS (
                        SELECT 1 FROM pg_extension WHERE extname = 'pg_trgm'
                    )
                """)
                has_trgm = cursor.fetchone()[0]
                
                if not has_trgm:
                    logger.warning("pg_trgm extension not available, using fallback")
                    return self._fallback_lexical_similarity(text1, text2)
                
                cursor.execute("""
                    SELECT similarity(%s, %s)
                """, [text1, text2])
                result = cursor.fetchone()
                return float(result[0]) if result else 0.0
        except Exception as e:
            logger.warning(f"Failed to calculate lexical similarity: {e}")
            return self._fallback_lexical_similarity(text1, text2)

    def _fallback_lexical_similarity(self, text1: str, text2: str) -> float:
        """
        Fallback lexical similarity calculation using Jaccard similarity of word sets.

        Args:
            text1: First text string
            text2: Second text string

        Returns:
            Lexical similarity score (0.0 to 1.0)
        """
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())

        if not words1 and not words2:
            return 1.0
        if not words1 or not words2:
            return 0.0

        intersection = words1.intersection(words2)
        union = words1.union(words2)

        return len(intersection) / len(union) if union else 0.0

    def calculate_hybrid_similarity(self,
                                  embedding1: Optional[List[float]],
                                  embedding2: Optional[List[float]],
                                  text1: str = "",
                                  text2: str = "") -> float:
        """
        Calculate hybrid similarity combining semantic and lexical approaches.

        Args:
            embedding1: First embedding vector (optional)
            embedding2: Second embedding vector (optional)
            text1: First text for lexical comparison (fallback)
            text2: Second text for lexical comparison (fallback)

        Returns:
            Hybrid similarity score (0.0 to 1.0)
        """
        # Normalize embeddings
        emb1 = self._normalize_embedding(embedding1)
        emb2 = self._normalize_embedding(embedding2)

        # Calculate semantic similarity if embeddings are available
        semantic_score = 0.0
        if emb1 is not None and emb2 is not None and len(emb1) > 0 and len(emb2) > 0:
            try:
                semantic_score = self.calculate_semantic_similarity(emb1, emb2)
            except Exception as e:
                logger.warning(f"Failed to calculate semantic similarity: {e}")
                semantic_score = 0.0
        else:
            lexical_fallback = self.calculate_lexical_similarity(text1, text2)
            semantic_score = lexical_fallback
            logger.debug("Using lexical similarity as fallback for semantic score")

        # Calculate lexical similarity
        lexical_score = self.calculate_lexical_similarity(text1, text2)

        if self.algorithm == 'EMBEDDING':
            return semantic_score
        if self.algorithm == 'TFIDF':
            return lexical_score

        # Combine scores using weighted average
        hybrid_score = (self.semantic_weight * semantic_score) + (self.lexical_weight * lexical_score)

        logger.debug(f"Hybrid similarity: semantic={semantic_score:.3f}, lexical={lexical_score:.3f}, combined={hybrid_score:.3f}")

        return hybrid_score

    def find_similar_projects(self,
                            project_id: int,
                            title: str,
                            objectives: str,
                            title_embedding: Optional[List[float]] = None,
                            objectives_embedding: Optional[List[float]] = None,
                            combined_embedding: Optional[List[float]] = None,
                            limit: int = 10,
                            exclude_user_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Find projects similar to the given project using vector similarity search.

        ====== FIXED: Exclude same user's projects ======
        """
        try:
            min_year = timezone.now().year - max(self.search_years_back - 1, 0)
            
            # Normalize combined_embedding
            combined_emb = self._normalize_embedding(combined_embedding)
            
            # ====== Build query with user exclusion if needed ======
            user_exclusion_clause = ""
            if exclude_user_id:
                user_exclusion_clause = f" AND p.user_id != {exclude_user_id}"
            
            if combined_emb is not None and len(combined_emb) > 0:
                # Convert to pgvector string format
                embedding_str = self._to_pgvector_string(combined_emb)
                
                if embedding_str is None:
                    logger.warning("Failed to convert embedding to pgvector string")
                    return self._find_similar_projects_lexical(project_id, title, objectives, limit, exclude_user_id)
                
                with connection.cursor() as cursor:
                    # Vector similarity search using pgvector
                    cursor.execute(f"""
                        SELECT
                            p.id,
                            p.title,
                            p.main_objective,
                            p.specific_objectives,
                            p.combined_embedding,
                            CASE 
                                WHEN p.combined_embedding IS NOT NULL 
                                THEN 1 - (p.combined_embedding <=> %s::vector) 
                                ELSE 0 
                            END as vector_similarity
                        FROM projects_project p
                        WHERE p.id != %s 
                            AND p.combined_embedding IS NOT NULL 
                            AND p.year >= %s
                            {user_exclusion_clause}
                        ORDER BY 
                            CASE 
                                WHEN p.combined_embedding IS NOT NULL 
                                THEN p.combined_embedding <=> %s::vector 
                                ELSE 999 
                            END
                        LIMIT %s
                    """, [embedding_str, project_id, min_year, embedding_str, limit])

                    similar_projects = []
                    for row in cursor.fetchall():
                        proj_id, proj_title, proj_main_obj, proj_spec_obj, proj_combined_emb, vec_sim = row

                        # Convert JSON specific_objectives to string
                        proj_objectives = proj_main_obj or ""
                        if proj_spec_obj:
                            if isinstance(proj_spec_obj, list):
                                proj_objectives += " " + " ".join(str(obj) for obj in proj_spec_obj if obj)
                            elif isinstance(proj_spec_obj, str):
                                proj_objectives += " " + proj_spec_obj

                        # Normalize embedding values from raw SQL
                        proj_combined_emb_norm = self._normalize_embedding(proj_combined_emb)

                        # Calculate hybrid similarity
                        try:
                            hybrid_sim = self.calculate_hybrid_similarity(
                                combined_emb, proj_combined_emb_norm,
                                f"{title} {objectives}", f"{proj_title} {proj_objectives}"
                            )
                        except Exception as e:
                            logger.warning(f"Failed to calculate hybrid similarity: {e}")
                            hybrid_sim = float(vec_sim) if vec_sim is not None else 0.0

                        # ====== Auto-flag if similarity >= threshold ======
                        is_auto_flagged = hybrid_sim >= self.auto_flag_threshold

                        similar_projects.append({
                            'id': proj_id,
                            'title': proj_title,
                            'objectives': proj_objectives,
                            'vector_similarity': float(vec_sim) if vec_sim is not None else None,
                            'hybrid_similarity': hybrid_sim,
                            'is_potential_duplicate': hybrid_sim >= self.similarity_threshold,
                            'auto_flag': is_auto_flagged
                        })

                    # Sort by hybrid similarity descending
                    similar_projects.sort(key=lambda x: x['hybrid_similarity'], reverse=True)
                    return similar_projects[:limit]
            else:
                # Fallback: lexical similarity only
                logger.warning("No embeddings available, using lexical similarity fallback")
                return self._find_similar_projects_lexical(project_id, title, objectives, limit, exclude_user_id)

        except Exception as e:
            logger.error(f"Failed to find similar projects: {e}")
            import traceback
            traceback.print_exc()
            return self._find_similar_projects_lexical(project_id, title, objectives, limit, exclude_user_id)

    def _find_similar_projects_lexical(self,
                                     project_id: int,
                                     title: str,
                                     objectives: str,
                                     limit: int = 10,
                                     exclude_user_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Fallback method using lexical similarity when vector search is unavailable.

        ====== FIXED: Exclude same user's projects ======
        """
        try:
            combined_text = f"{title} {objectives}"
            min_year = timezone.now().year - max(self.search_years_back - 1, 0)

            user_exclusion_clause = ""
            if exclude_user_id:
                user_exclusion_clause = f" AND p.user_id != {exclude_user_id}"

            try:
                with connection.cursor() as cursor:
                    cursor.execute("""
                        SELECT EXISTS (
                            SELECT 1 FROM pg_extension WHERE extname = 'pg_trgm'
                        )
                    """)
                    has_trgm = cursor.fetchone()[0]
                    
                    if not has_trgm:
                        logger.warning("pg_trgm not available, using fallback lexical")
                        return self._fallback_lexical_search(project_id, combined_text, min_year, limit, exclude_user_id)
                    
                    cursor.execute(f"""
                        SELECT
                            p.id,
                            p.title,
                            p.main_objective,
                            p.specific_objectives,
                            similarity(%s, p.title || ' ' || COALESCE(p.main_objective, '') || ' ' || COALESCE(p.project_description, '')) as lexical_similarity
                        FROM projects_project p
                        WHERE p.id != %s AND p.year >= %s
                            {user_exclusion_clause}
                        ORDER BY similarity(%s, p.title || ' ' || COALESCE(p.main_objective, '') || ' ' || COALESCE(p.project_description, '')) DESC
                        LIMIT %s
                    """, [combined_text, project_id, min_year, combined_text, limit])

                    similar_projects = []
                    for row in cursor.fetchall():
                        proj_id, proj_title, proj_main_obj, proj_spec_obj, lex_sim = row

                        proj_objectives = proj_main_obj or ""
                        if proj_spec_obj:
                            if isinstance(proj_spec_obj, list):
                                proj_objectives += " " + " ".join(str(obj) for obj in proj_spec_obj if obj)
                            else:
                                proj_objectives += " " + str(proj_spec_obj)

                        hybrid_sim = float(lex_sim) if lex_sim is not None else 0.0

                        similar_projects.append({
                            'id': proj_id,
                            'title': proj_title,
                            'objectives': proj_objectives,
                            'vector_similarity': None,
                            'hybrid_similarity': hybrid_sim,
                            'is_potential_duplicate': hybrid_sim >= self.similarity_threshold,
                            'auto_flag': hybrid_sim >= self.auto_flag_threshold
                        })

                    return similar_projects
            except Exception as e:
                logger.warning(f"pg_trgm not available, using fallback lexical: {e}")
                return self._fallback_lexical_search(project_id, combined_text, min_year, limit, exclude_user_id)

        except Exception as e:
            logger.error(f"Failed to find similar projects with lexical search: {e}")
            return []

    def _fallback_lexical_search(self, 
                                 project_id: int, 
                                 text: str, 
                                 min_year: int, 
                                 limit: int,
                                 exclude_user_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Simple fallback lexical search using ILIKE when pg_trgm is not available.

        ====== FIXED: Exclude same user's projects ======
        """
        try:
            from projects.models import Project
            from django.db import models as django_models
            
            words = text.lower().split()
            if not words:
                return []

            query = Project.objects.exclude(id=project_id).filter(year__gte=min_year)
            
            # ====== FIX: Exclude same user ======
            if exclude_user_id:
                query = query.exclude(user_id=exclude_user_id)
            
            for word in words[:10]:
                if len(word) > 3:
                    query = query.filter(
                        django_models.Q(title__icontains=word) | 
                        django_models.Q(main_objective__icontains=word) |
                        django_models.Q(project_description__icontains=word)
                    )

            similar_projects = query[:limit]
            results = []
            for p in similar_projects:
                p_text = f"{p.title} {p.main_objective} {p.project_description or ''}".lower()
                p_words = set(p_text.split())
                query_words = set(text.lower().split())
                
                if p_words and query_words:
                    overlap = len(p_words.intersection(query_words))
                    union = len(p_words.union(query_words))
                    similarity = overlap / union if union > 0 else 0.0
                else:
                    similarity = 0.0

                results.append({
                    'id': p.id,
                    'title': p.title,
                    'objectives': p.main_objective or '',
                    'vector_similarity': None,
                    'hybrid_similarity': similarity,
                    'is_potential_duplicate': similarity >= self.similarity_threshold,
                    'auto_flag': similarity >= self.auto_flag_threshold
                })

            return results
        except Exception as e:
            logger.error(f"Fallback lexical search failed: {e}")
            return []

    def get_similarity_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the similarity configuration and thresholds.

        Returns:
            Dictionary with similarity configuration stats
        """
        return {
            'semantic_weight': self.semantic_weight,
            'lexical_weight': self.lexical_weight,
            'similarity_threshold': self.similarity_threshold,
            'auto_flag_threshold': self.auto_flag_threshold,
            'search_years_back': self.search_years_back,
            'algorithm': self.algorithm,
            'embedding_model': self.embedding_service.get_model_info() if self.embedding_service else 'Not loaded'
        }


# Global function to get a similarity scorer instance
_similarity_scorer = None

def get_similarity_scorer() -> SimilarityScorer:
    """
    Get or create the global similarity scorer instance.

    Returns:
        SimilarityScorer instance
    """
    global _similarity_scorer
    if _similarity_scorer is None:
        _similarity_scorer = SimilarityScorer()
    return _similarity_scorer