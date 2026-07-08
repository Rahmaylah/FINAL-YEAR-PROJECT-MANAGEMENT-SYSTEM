# projects/models.py - Complete updated file with working auto-duplicate detection
# Inafanya kazi kwa CREATE na UPDATE (EDIT)

from django.db import models
from django.core.validators import MaxValueValidator, MinValueValidator
from pgvector.django import VectorField
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone
from accounts.models import User
import logging
import json
import re

logger = logging.getLogger(__name__)


class ProjectType(models.Model):
    name = models.CharField(max_length=150, unique=True)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name


class Project(models.Model):
    STATUS_CHOICES = [
        ('proposed', 'Proposed'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('completed', 'Completed'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=500)
    project_type = models.ForeignKey('ProjectType', on_delete=models.SET_NULL, null=True, blank=True)
    main_objective = models.TextField(blank=True)
    specific_objectives = models.JSONField(default=list, blank=True)
    project_description = models.TextField(blank=True)
    implementation_details = models.TextField(blank=True)
    year = models.IntegerField()
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='proposed')

    # Embeddings
    title_embedding = VectorField(dimensions=768, null=True, blank=True)
    objectives_embedding = VectorField(dimensions=768, null=True, blank=True)
    combined_embedding = VectorField(dimensions=768, null=True, blank=True)

    # Duplicate detection
    last_similarity_check = models.DateTimeField(null=True, blank=True)
    is_flagged_duplicate = models.BooleanField(default=False)
    duplicate_check_score = models.FloatField(null=True, blank=True)
    duplicate_keywords_matched = models.JSONField(default=list, blank=True)

    # ====== NEW: Mentor Comment Field ======
    mentor_comment = models.TextField(blank=True, null=True, help_text="Mentor's feedback on the project")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.title} ({self.year}) ({self.status})"

    def force_duplicate_check(self):
        """
        Force duplicate check manually (useful after editing)
        """
        from .similarity import get_similarity_scorer
        from core.models import SystemSettings
        from pgvector.django import CosineDistance
        
        settings = SystemSettings.get_solo()
        threshold = settings.duplicate_similarity_threshold or 0.5
        auto_flag_threshold = settings.duplicate_auto_flag_threshold or 0.6
        
        # Generate embeddings first
        from .utils import generate_project_embeddings
        embeddings = generate_project_embeddings(
            title=self.title,
            objectives=self.main_objective,
            description=self.project_description
        )
        
        if embeddings:
            self.title_embedding = embeddings['title_embedding']
            self.objectives_embedding = embeddings['objectives_embedding']
            self.combined_embedding = embeddings['combined_embedding']
            self.last_similarity_check = timezone.now()
            Project.objects.filter(id=self.id).update(
                title_embedding=self.title_embedding,
                objectives_embedding=self.objectives_embedding,
                combined_embedding=self.combined_embedding,
                last_similarity_check=self.last_similarity_check
            )
        
        # Find similar projects
        similar = Project.objects.exclude(id=self.id).exclude(
            combined_embedding__isnull=True
        ).annotate(
            distance=CosineDistance('combined_embedding', self.combined_embedding)
        ).filter(
            distance__lt=1 - threshold
        ).order_by('distance')[:5]
        
        # Check duplicates
        for proj in similar:
            similarity = 1 - proj.distance
            if similarity >= auto_flag_threshold:
                flag, created = DuplicateFlag.objects.get_or_create(
                    project=self,
                    similar_project=proj,
                    defaults={'similarity_score': similarity}
                )
                if not created:
                    flag.similarity_score = similarity
                    flag.save()
                
                # Update project status
                self.is_flagged_duplicate = True
                self.duplicate_check_score = similarity
                Project.objects.filter(id=self.id).update(
                    is_flagged_duplicate=True,
                    duplicate_check_score=similarity
                )
                logger.info(f"🚨 Project {self.id} flagged as duplicate after edit! Score: {similarity:.3f}")
                return True
        
        return False


class ProjectDocument(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='documents')
    uploaded_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='project_documents'
    )
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    file = models.FileField(upload_to='project_documents/')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-uploaded_at']

    def __str__(self):
        return f"{self.name} ({self.project.title})"


class Presentation(models.Model):
    name = models.CharField(max_length=255, blank=True)
    presentation_date = models.DateField(null=True, blank=True)
    total_marks = models.FloatField(default=15.0, validators=[MinValueValidator(0.0)])
    pass_marks = models.FloatField(default=8.0, validators=[MinValueValidator(0.0)])
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-presentation_date', '-created_at']

    def __str__(self):
        label = self.name or f"Presentation {self.id}"
        return label


class PresentationCriteria(models.Model):
    """
    Model for defining grading criteria for presentations.
    Each presentation can have multiple criteria.
    """
    CRITERIA_TYPES = [
        ('numeric', 'Numeric Score'),
        ('dropdown', 'Dropdown Selection'),
        ('text', 'Text Feedback'),
    ]

    presentation = models.ForeignKey(
        'Presentation',
        on_delete=models.CASCADE,
        related_name='criteria'
    )
    name = models.CharField(max_length=200, help_text="Name of the criteria (e.g., 'Comment Implementation', 'Type')")
    description = models.TextField(blank=True, null=True, help_text="Detailed description of the criteria")
    criteria_type = models.CharField(max_length=20, choices=CRITERIA_TYPES, default='numeric')
    max_score = models.FloatField(default=10.0, help_text="Maximum score for this criteria")
    weight = models.FloatField(default=1.0, help_text="Weight of this criteria in total score")
    order = models.IntegerField(default=0, help_text="Display order")
    is_required = models.BooleanField(default=True, help_text="Whether this criteria is required for grading")
    
    # For dropdown/select options (like Type, Practical Progress)
    options = models.JSONField(
        default=list,
        blank=True,
        help_text="Options for dropdown: [{'label': 'Embedded', 'value': 2.5}, {'label': 'Web App', 'value': 1.5}]"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['order', 'name']
        verbose_name_plural = "Presentation Criteria"
        unique_together = ['presentation', 'name']

    def __str__(self):
        return f"{self.name} ({self.max_score} pts)"

    def get_options_display(self):
        """Get options as list of dicts for display"""
        if not self.options:
            return []
        return self.options


class PresentationResult(models.Model):
    presentation = models.ForeignKey(Presentation, on_delete=models.CASCADE, related_name='results')
    student = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='presentation_results',
        limit_choices_to={'role': 'student'}
    )
    project = models.ForeignKey(
        Project,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='presentation_results'
    )
    reviewer = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='presentation_evaluations'
    )
    comment = models.TextField(blank=True)
    marks = models.FloatField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0.0)]
    )
    
    # Auto-calculated from criteria
    criteria_total = models.FloatField(
        null=True, 
        blank=True, 
        help_text="Auto-calculated total from criteria scores"
    )
    is_graded_by_criteria = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('presentation', 'student')
        ordering = ['-presentation__presentation_date', '-created_at']

    def __str__(self):
        student_name = self.student.get_full_name() or self.student.username
        return f"{student_name} - {self.presentation.name or f'Presentation {self.presentation.id}'}"

    def calculate_criteria_total(self):
        """Calculate total score from criteria scores"""
        criteria_scores = self.criteria_scores.all()
        if not criteria_scores.exists():
            return None
        
        total_weighted_score = 0
        total_weight = 0
        
        for cs in criteria_scores:
            if cs.score is not None:
                # Normalize score to percentage
                if cs.criteria.max_score > 0:
                    normalized_score = (cs.score / cs.criteria.max_score) * 100
                    weighted_score = normalized_score * cs.criteria.weight
                    total_weighted_score += weighted_score
                    total_weight += cs.criteria.weight
        
        if total_weight > 0:
            return round(total_weighted_score / total_weight, 2)
        return None

    def save(self, *args, **kwargs):
        # Auto-calculate criteria total
        if self.is_graded_by_criteria:
            self.criteria_total = self.calculate_criteria_total()
            if self.criteria_total is not None:
                self.marks = self.criteria_total
        super().save(*args, **kwargs)


class PresentationResultCriteria(models.Model):
    """
    Model for storing scores for each criteria per student presentation.
    """
    result = models.ForeignKey(
        'PresentationResult',
        on_delete=models.CASCADE,
        related_name='criteria_scores'
    )
    criteria = models.ForeignKey(
        PresentationCriteria,
        on_delete=models.CASCADE,
        related_name='scores'
    )
    score = models.FloatField(
        null=True, 
        blank=True, 
        help_text="Score given for this criteria",
        validators=[MinValueValidator(0)]
    )
    selected_option = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Selected option from dropdown (e.g., 'Embedded', 'Good progress')"
    )
    comment = models.TextField(blank=True, null=True, help_text="Feedback for this specific criteria")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['result', 'criteria']
        verbose_name_plural = "Presentation Criteria Scores"

    def __str__(self):
        return f"{self.result} - {self.criteria.name}: {self.score or self.selected_option or 'N/A'}"

    def get_score_display(self):
        """Get display value for score"""
        if self.score is not None:
            return f"{self.score}"
        if self.selected_option:
            return self.selected_option
        return "N/A"


class DuplicateFlag(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='duplicate_flags')
    similar_project = models.ForeignKey(Project, on_delete=models.CASCADE)
    similarity_score = models.FloatField()
    reviewed = models.BooleanField(default=False)
    reviewed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Flag: {self.project.title} ~ {self.similar_project.title}"


class ProjectUser(models.Model):
    ROLE_CHOICES = [
        ('lead', 'Lead'),
        ('member', 'Member'),
    ]

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='project_users')
    user = models.ForeignKey(User, on_delete=models.CASCADE,
                            related_name='project_users',
                            limit_choices_to={'role': 'student'})
    role = models.CharField(max_length=50, choices=ROLE_CHOICES, default='lead')
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('project', 'user')

    def __str__(self):
        return f"{self.user.get_full_name()} - {self.project.title} ({self.role})"


# ================================================================
# ====== AUTO-DUPLICATE DETECTION WITH KEYWORD MATCHING ======
# ================================================================

def extract_keywords(text):
    """
    Extract keywords from text for duplicate detection.
    Removes stop words and common words.
    """
    # Common stop words
    stop_words = {
        'the', 'a', 'an', 'of', 'for', 'on', 'at', 'to', 'in', 'with', 'by', 'from',
        'up', 'off', 'out', 'over', 'under', 'about', 'after', 'before', 'between',
        'among', 'through', 'during', 'without', 'against', 'within', 'upon', 'into',
        'and', 'or', 'but', 'nor', 'for', 'so', 'yet', 'as', 'than', 'that', 'these',
        'those', 'this', 'that', 'these', 'those', 'is', 'am', 'are', 'was', 'were',
        'be', 'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will',
        'would', 'shall', 'should', 'may', 'might', 'must', 'can', 'could'
    }
    
    # Split and clean
    words = text.lower().split()
    keywords = []
    
    for word in words:
        # Remove punctuation
        word = ''.join(c for c in word if c.isalnum())
        if len(word) > 3 and word not in stop_words:
            keywords.append(word)
    
    return keywords


def check_keyword_similarity(project1, project2):
    """
    Check similarity between two projects using keywords.
    Returns similarity score between 0 and 1.
    """
    # Extract keywords from both projects
    text1 = f"{project1.title} {project1.main_objective} {project1.project_description or ''}"
    text2 = f"{project2.title} {project2.main_objective} {project2.project_description or ''}"
    
    keywords1 = set(extract_keywords(text1))
    keywords2 = set(extract_keywords(text2))
    
    if not keywords1 or not keywords2:
        return 0.0
    
    # Calculate Jaccard similarity
    intersection = len(keywords1.intersection(keywords2))
    union = len(keywords1.union(keywords2))
    
    if union == 0:
        return 0.0
    
    return intersection / union


@receiver(pre_save, sender=Project)
def generate_embeddings_before_save(sender, instance, **kwargs):
    """
    Generate embeddings BEFORE saving the project.
    This ensures embeddings are always available.
    """
    try:
        # Check if combined_embedding already exists
        if instance.combined_embedding is not None:
            logger.info(f"⏭️ Skipping embedding generation for project {instance.id} (embeddings already exist)")
            return
        
        from .utils import generate_project_embeddings
        
        # Generate embeddings if they don't exist
        if instance.combined_embedding is None:
            embeddings = generate_project_embeddings(
                title=instance.title,
                objectives=instance.main_objective,
                description=instance.project_description
            )
            
            if embeddings:
                instance.title_embedding = embeddings.get('title_embedding')
                instance.objectives_embedding = embeddings.get('objectives_embedding')
                instance.combined_embedding = embeddings.get('combined_embedding')
                instance.last_similarity_check = timezone.now()
                logger.info(f"✅ Generated embeddings for project: {instance.title}")
            else:
                logger.warning(f"❌ Failed to generate embeddings for project: {instance.title}")
                
    except Exception as e:
        logger.error(f"Error generating embeddings for {instance.id}: {e}")


@receiver(post_save, sender=Project)
def check_duplicates_after_save(sender, instance, created, **kwargs):
    """
    Check for duplicate projects AFTER saving.
    Uses both keyword matching and embedding similarity.
    Inafanya kazi kwa CREATE na UPDATE (EDIT)
    """
    try:
        # Skip duplicate check if no combined embedding
        if instance.combined_embedding is None:
            logger.info(f"⏭️ Skipping duplicate check for project {instance.id} (no embedding)")
            # Try to generate embeddings if this is a new project
            if created:
                from .utils import generate_project_embeddings
                embeddings = generate_project_embeddings(
                    title=instance.title,
                    objectives=instance.main_objective,
                    description=instance.project_description
                )
                if embeddings:
                    instance.title_embedding = embeddings.get('title_embedding')
                    instance.objectives_embedding = embeddings.get('objectives_embedding')
                    instance.combined_embedding = embeddings.get('combined_embedding')
                    instance.last_similarity_check = timezone.now()
                    instance.save(update_fields=['title_embedding', 'objectives_embedding', 'combined_embedding', 'last_similarity_check'])
                    logger.info(f"✅ Generated embeddings for new project {instance.id} via post_save")
                    # Re-run duplicate check now that we have embeddings
                    return check_duplicates_after_save(sender, instance, created, **kwargs)
            return
        
        from .similarity import get_similarity_scorer
        from core.models import SystemSettings
        
        # Get settings
        settings = SystemSettings.get_solo()
        threshold = settings.duplicate_similarity_threshold or 0.5
        auto_flag_threshold = settings.duplicate_auto_flag_threshold or 0.6
        
        # Get all other projects
        other_projects = Project.objects.exclude(id=instance.id)
        
        if not other_projects.exists():
            return
        
        # ====== KEYWORD SIMILARITY ======
        keyword_matches = []
        for other in other_projects:
            keyword_score = check_keyword_similarity(instance, other)
            if keyword_score > 0.3:  # Minimum threshold for keyword match
                keyword_matches.append({
                    'project': other,
                    'keyword_score': keyword_score
                })
        
        # ====== EMBEDDING SIMILARITY (pgvector) ======
        try:
            from pgvector.django import CosineDistance
            
            # Find similar projects using pgvector
            embedding_matches = Project.objects.exclude(id=instance.id).exclude(
                combined_embedding__isnull=True
            ).annotate(
                distance=CosineDistance('combined_embedding', instance.combined_embedding)
            ).filter(
                distance__lt=1 - threshold
            ).order_by('distance')[:5]
            
        except Exception as e:
            logger.error(f"pgvector error: {e}")
            embedding_matches = []
        
        # ====== COMBINE RESULTS ======
        combined_scores = {}
        matched_keywords = []
        max_similarity = 0.0
        best_match = None
        
        # Process embedding matches
        for match in embedding_matches:
            similarity = 1 - match.distance
            combined_scores[match.id] = {
                'project': match,
                'similarity': similarity,
                'keyword_score': 0.0,
                'combined_score': similarity
            }
            if similarity > max_similarity:
                max_similarity = similarity
                best_match = match
        
        # Process keyword matches
        for match in keyword_matches:
            proj = match['project']
            keyword_score = match['keyword_score']
            
            if proj.id in combined_scores:
                # Combine with embedding score
                current = combined_scores[proj.id]
                # Average of both scores
                combined_score = (current['similarity'] + keyword_score) / 2
                combined_scores[proj.id]['combined_score'] = combined_score
                combined_scores[proj.id]['keyword_score'] = keyword_score
            else:
                combined_scores[proj.id] = {
                    'project': proj,
                    'similarity': 0.0,
                    'keyword_score': keyword_score,
                    'combined_score': keyword_score
                }
            
            # Track matched keywords
            text1 = f"{instance.title} {instance.main_objective}"
            text2 = f"{proj.title} {proj.main_objective}"
            keywords1 = set(extract_keywords(text1))
            keywords2 = set(extract_keywords(text2))
            common = keywords1.intersection(keywords2)
            matched_keywords.extend(list(common)[:5])
        
        # ====== FIND BEST MATCH ======
        best_score = 0.0
        best_project = None
        
        for proj_id, data in combined_scores.items():
            score = data.get('combined_score', data.get('similarity', data.get('keyword_score', 0)))
            if score > best_score:
                best_score = score
                best_project = data['project']
        
        # ====== FLAG IF DUPLICATE FOUND ======
        flagged = False
        if best_project and best_score >= auto_flag_threshold:
            # Create or update duplicate flag
            flag, created = DuplicateFlag.objects.get_or_create(
                project=instance,
                similar_project=best_project,
                defaults={
                    'similarity_score': best_score,
                }
            )
            
            if not created:
                flag.similarity_score = best_score
                flag.save()
            
            # Update project status
            instance.is_flagged_duplicate = True
            instance.duplicate_check_score = best_score
            instance.duplicate_keywords_matched = matched_keywords[:10]
            
            # Save without triggering signals
            Project.objects.filter(id=instance.id).update(
                is_flagged_duplicate=True,
                duplicate_check_score=best_score,
                duplicate_keywords_matched=matched_keywords[:10]
            )
            
            flagged = True
            action = "updated" if not created else "created"
            logger.info(f"🚨 Project {instance.id} flagged as duplicate! Score: {best_score:.3f}")
            logger.info(f"   Matched keywords: {matched_keywords[:5]}")
        
        elif best_project and best_score > 0:
            # Not flagged but similar - update score
            instance.duplicate_check_score = best_score
            instance.duplicate_keywords_matched = matched_keywords[:10]
            Project.objects.filter(id=instance.id).update(
                duplicate_check_score=best_score,
                duplicate_keywords_matched=matched_keywords[:10]
            )
            logger.info(f"📊 Project {instance.id} similarity score: {best_score:.3f} (below flag threshold)")
        
        # Update last check time
        instance.last_similarity_check = timezone.now()
        Project.objects.filter(id=instance.id).update(
            last_similarity_check=timezone.now()
        )
        
        # Log action
        if created:
            logger.info(f"✅ New project {instance.id} saved and checked for duplicates")
        else:
            logger.info(f"🔄 Project {instance.id} updated and re-checked for duplicates")
        
    except Exception as e:
        logger.error(f"Error in duplicate check for project {instance.id}: {e}")
    
    # Create ProjectUser if new
    if created:
        ProjectUser.objects.get_or_create(
            project=instance,
            user=instance.user,
            defaults={'role': 'lead'}
        )