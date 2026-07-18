# projects/models.py - Complete updated file with working auto-duplicate detection
# ====== FIXED: First project NEVER flagged ======
# ====== FIXED: duplicate_check_score = None for first project ======
# ====== FIXED: ALWAYS CREATE DuplicateFlag for flagged projects ======
# ====== FIXED: COMPLETELY SKIP DUPLICATE CHECK FOR MENTOR UPDATES ======
# ====== FIXED: Presentation marks save properly ======
# ====== FIXED: Verify flag exists after creation ======
# Inafanya kazi kwa CREATE na UPDATE (EDIT)

from django.db import models
from django.core.validators import MaxValueValidator, MinValueValidator
from pgvector.django import VectorField
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone
from django.db.models import Q
from accounts.models import User
import logging
import json
import re
import threading

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

    # ====== Mentor Comment Field ======
    mentor_comment = models.TextField(blank=True, null=True, help_text="Mentor's feedback on the project")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.title} ({self.year}) ({self.status})"

    def force_duplicate_check(self):
        """
        Force duplicate check manually (useful after editing)
        ====== FIXED: First project never flagged ======
        ====== FIXED: duplicate_check_score = None for first project ======
        ====== FIXED: Auto-create missing flag ======
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
        
        # Find similar projects - EXCLUDE SAME USER
        similar = Project.objects.exclude(id=self.id).exclude(
            combined_embedding__isnull=True
        ).exclude(
            user=self.user  # ← EXCLUDE SAME USER
        ).annotate(
            distance=CosineDistance('combined_embedding', self.combined_embedding)
        ).filter(
            distance__lt=1 - threshold
        ).order_by('distance')[:5]
        
        # ====== FIX: Check if this is the FIRST project ======
        older_projects = Project.objects.filter(
            Q(user=self.user) | Q(project_users__user=self.user)
        ).exclude(id=self.id).filter(created_at__lt=self.created_at).exists()
        
        # Check duplicates
        for proj in similar:
            similarity = 1 - proj.distance
            if similarity >= auto_flag_threshold and older_projects:
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
            elif similarity >= auto_flag_threshold and not older_projects:
                # ====== FIRST PROJECT - NEVER FLAGGED ======
                # ====== FIXED: duplicate_check_score = None ======
                self.is_flagged_duplicate = False
                self.duplicate_check_score = None
                Project.objects.filter(id=self.id).update(
                    is_flagged_duplicate=False,
                    duplicate_check_score=None
                )
                logger.info(f"✅ FIRST Project {self.id} - NOT FLAGGED (similarity: {similarity:.3f})")
                return False
        
        # No duplicates found
        self.is_flagged_duplicate = False
        self.duplicate_check_score = None
        Project.objects.filter(id=self.id).update(
            is_flagged_duplicate=False,
            duplicate_check_score=None
        )
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


# ============================================================
# ====== FIXED: PresentationResult Model with marks ======
# ============================================================

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


# ================================================================
# ====== THREAD-LOCAL FLAG FOR MENTOR UPDATES ======
# ================================================================

# Thread-local storage for mentor update flag
_mentor_update_local = threading.local()

def is_mentor_update():
    """Check if current operation is a mentor update"""
    return getattr(_mentor_update_local, 'active', False)

def set_mentor_update_active():
    """Set mentor update flag to active"""
    _mentor_update_local.active = True
    logger.info("🔒 MENTOR UPDATE FLAG SET")

def set_mentor_update_inactive():
    """Set mentor update flag to inactive"""
    _mentor_update_local.active = False
    logger.info("🔓 MENTOR UPDATE FLAG CLEARED")


# ================================================================
# ====== POST_SAVE SIGNAL - SKIP FOR MENTOR UPDATES ======
# ================================================================

@receiver(post_save, sender=Project)
def check_duplicates_after_save(sender, instance, created, **kwargs):
    """
    Check for duplicate projects AFTER saving.
    ====== FIXED: COMPLETELY SKIP FOR MENTOR UPDATES ======
    ====== FIXED: ALWAYS CREATE DUPLICATEFLAG ======
    ====== FIXED: VERIFY FLAG EXISTS ======
    """
    try:
        # ============================================================
        # ====== CRITICAL: SKIP IF MENTOR UPDATE IS ACTIVE ======
        # ============================================================
        if is_mentor_update():
            logger.info(f"✅ MENTOR UPDATE ACTIVE - COMPLETELY SKIPPING duplicate check for project {instance.id}")
            return
        
        # ============================================================
        # ====== SKIP IF ONLY MENTOR FIELDS CHANGED ======
        # ============================================================
        if not created:
            try:
                old_instance = Project.objects.get(id=instance.id)
                
                # Check what changed
                mentor_fields = ['mentor_comment', 'status']
                content_fields = ['title', 'main_objective', 'project_description', 'specific_objectives']
                
                mentor_changed = False
                content_changed = False
                
                for field in mentor_fields:
                    if getattr(old_instance, field) != getattr(instance, field):
                        mentor_changed = True
                        break
                
                for field in content_fields:
                    if getattr(old_instance, field) != getattr(instance, field):
                        content_changed = True
                        break
                
                # ====== IF ONLY MENTOR FIELDS CHANGED, SKIP ======
                if mentor_changed and not content_changed:
                    logger.info(f"✅ Mentor update (comment/status only) - SKIPPING duplicate check for project {instance.id}")
                    
                    # ====== FORCE RESET TO ORIGINAL STATE ======
                    original_flagged = old_instance.is_flagged_duplicate
                    original_score = old_instance.duplicate_check_score
                    
                    if not original_flagged:
                        Project.objects.filter(id=instance.id).update(
                            is_flagged_duplicate=False,
                            duplicate_check_score=None,
                            duplicate_keywords_matched=[]
                        )
                        DuplicateFlag.objects.filter(project=instance).delete()
                        DuplicateFlag.objects.filter(similar_project=instance).delete()
                        logger.info(f"✅ FORCED project {instance.id} to remain UNFLAGGED")
                    else:
                        Project.objects.filter(id=instance.id).update(
                            is_flagged_duplicate=True,
                            duplicate_check_score=original_score
                        )
                        logger.info(f"✅ FORCED project {instance.id} to remain FLAGGED")
                    
                    instance.is_flagged_duplicate = original_flagged
                    instance.duplicate_check_score = original_score
                    
                    return
                    
            except Project.DoesNotExist:
                pass
        
        # ============================================================
        # ====== CONTINUE WITH NORMAL DUPLICATE CHECK ======
        # ============================================================
        
        # Skip duplicate check if no combined embedding
        if instance.combined_embedding is None:
            logger.info(f"⏭️ Skipping duplicate check for project {instance.id} (no embedding)")
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
                    return check_duplicates_after_save(sender, instance, created, **kwargs)
            return
        
        from core.models import SystemSettings
        
        # Get settings
        settings = SystemSettings.get_solo()
        auto_flag_threshold = settings.duplicate_auto_flag_threshold or 0.5
        
        # ====== EXCLUDE SAME USER'S PROJECTS ======
        other_projects = Project.objects.exclude(id=instance.id).exclude(user=instance.user)
        
        if not other_projects.exists():
            logger.info(f"✅ No other projects to compare for project {instance.id}")
            instance.is_flagged_duplicate = False
            instance.duplicate_check_score = None
            Project.objects.filter(id=instance.id).update(
                is_flagged_duplicate=False,
                duplicate_check_score=None,
                last_similarity_check=timezone.now()
            )
            return
        
        # ====== EMBEDDING SIMILARITY (pgvector) ======
        try:
            from pgvector.django import CosineDistance
            
            embedding_matches = Project.objects.exclude(id=instance.id).exclude(
                combined_embedding__isnull=True
            ).exclude(
                user=instance.user
            ).annotate(
                distance=CosineDistance('combined_embedding', instance.combined_embedding)
            ).filter(
                distance__lt=1 - 0.3
            ).order_by('distance')[:5]
            
        except Exception as e:
            logger.error(f"pgvector error: {e}")
            embedding_matches = []
        
        # ====== CHECK FOR SIMILAR PROJECTS ======
        max_similarity = 0.0
        best_match = None
        
        for match in embedding_matches:
            similarity = 1 - match.distance
            if similarity > max_similarity:
                max_similarity = similarity
                best_match = match
        
        # ====== CHECK IF THIS IS THE FIRST PROJECT ======
        older_projects = Project.objects.filter(
            Q(user=instance.user) | Q(project_users__user=instance.user)
        ).exclude(id=instance.id).filter(created_at__lt=instance.created_at).exists()
        
        # ====== DECISION ======
        should_flag = False
        
        if best_match and max_similarity >= auto_flag_threshold:
            if older_projects:
                should_flag = True
                logger.info(f"📌 Project {instance.id} has older projects - FLAGGING")
            else:
                logger.info(f"✅ Project {instance.id} is FIRST - NOT FLAGGING")
        
        # ============================================================
        # ====== FIX: ALWAYS CREATE DUPLICATEFLAG ======
        # ============================================================
        
        if best_match and max_similarity >= auto_flag_threshold:
            # ====== FLAG 1: Current project → Similar project ======
            flag1, created1 = DuplicateFlag.objects.get_or_create(
                project=instance,
                similar_project=best_match,
                defaults={'similarity_score': max_similarity}
            )
            
            if not created1:
                flag1.similarity_score = max_similarity
                flag1.save()
                logger.info(f"✅ Updated flag1: {instance.id} → {best_match.id}")
            else:
                logger.info(f"✅ Created flag1: {instance.id} → {best_match.id}")
            
            # ====== FLAG 2: Similar project → Current project (BOTH SIDES) ======
            flag2, created2 = DuplicateFlag.objects.get_or_create(
                project=best_match,
                similar_project=instance,
                defaults={'similarity_score': max_similarity}
            )
            
            if not created2:
                flag2.similarity_score = max_similarity
                flag2.save()
                logger.info(f"✅ Updated flag2: {best_match.id} → {instance.id}")
            else:
                logger.info(f"✅ Created flag2: {best_match.id} → {instance.id}")
        
        # ============================================================
        # ====== APPLY FLAG BASED ON should_flag ======
        # ============================================================
        
        if best_match and max_similarity >= auto_flag_threshold and should_flag:
            # ====== SECOND+ PROJECT - FLAG IT ======
            instance.is_flagged_duplicate = True
            instance.duplicate_check_score = max_similarity
            
            Project.objects.filter(id=instance.id).update(
                is_flagged_duplicate=True,
                duplicate_check_score=max_similarity,
                last_similarity_check=timezone.now()
            )
            
            # Also flag the other project for mentor
            if not best_match.is_flagged_duplicate:
                best_match.is_flagged_duplicate = True
                best_match.duplicate_check_score = max_similarity
                best_match.save(update_fields=['is_flagged_duplicate', 'duplicate_check_score'])
                logger.info(f"🔍 Also flagged other project {best_match.id} for mentor")
            
            logger.info(f"🚨 SECOND+ Project {instance.id} FLAGGED! Score: {max_similarity:.3f}")
            
        elif best_match and max_similarity >= auto_flag_threshold and not should_flag:
            # ====== FIRST PROJECT - NEVER FLAGGED ======
            instance.is_flagged_duplicate = False
            instance.duplicate_check_score = None
            
            Project.objects.filter(id=instance.id).update(
                is_flagged_duplicate=False,
                duplicate_check_score=None,
                last_similarity_check=timezone.now()
            )
            
            logger.info(f"✅ FIRST Project {instance.id} - NOT FLAGGED (flag record exists)")
            
        else:
            # ====== NO DUPLICATE FOUND - RESET ======
            instance.is_flagged_duplicate = False
            instance.duplicate_check_score = None
            
            Project.objects.filter(id=instance.id).update(
                is_flagged_duplicate=False,
                duplicate_check_score=None,
                last_similarity_check=timezone.now()
            )
            
            # Delete existing flags
            DuplicateFlag.objects.filter(project=instance).delete()
            DuplicateFlag.objects.filter(similar_project=instance).delete()
            
            logger.info(f"✅ Project {instance.id} - no duplicates")
        
        # ============================================================
        # ====== FIX: VERIFY FLAG EXISTS ======
        # ============================================================
        
        if instance.is_flagged_duplicate:
            flag_exists = DuplicateFlag.objects.filter(
                Q(project=instance) | Q(similar_project=instance)
            ).exists()
            
            if not flag_exists:
                logger.error(f"❌ Project {instance.id} is flagged but NO DuplicateFlag exists!")
                
                # ====== FORCE CREATE THE FLAG ======
                if best_match:
                    DuplicateFlag.objects.create(
                        project=instance,
                        similar_project=best_match,
                        similarity_score=instance.duplicate_check_score or max_similarity
                    )
                    DuplicateFlag.objects.create(
                        project=best_match,
                        similar_project=instance,
                        similarity_score=instance.duplicate_check_score or max_similarity
                    )
                    logger.info(f"✅ FORCE CREATED flags for {instance.id} ↔ {best_match.id}")
                else:
                    # Try to find any similar project
                    try:
                        from pgvector.django import CosineDistance
                        similar = Project.objects.exclude(id=instance.id).exclude(
                            combined_embedding__isnull=True
                        ).exclude(
                            user=instance.user
                        ).annotate(
                            distance=CosineDistance('combined_embedding', instance.combined_embedding)
                        ).filter(
                            distance__lt=1 - 0.3
                        ).order_by('distance')[:1]
                        
                        if similar.exists():
                            match = similar.first()
                            similarity = 1 - match.distance
                            DuplicateFlag.objects.create(
                                project=instance,
                                similar_project=match,
                                similarity_score=similarity
                            )
                            DuplicateFlag.objects.create(
                                project=match,
                                similar_project=instance,
                                similarity_score=similarity
                            )
                            logger.info(f"✅ FORCE CREATED flags for {instance.id} ↔ {match.id}")
                    except Exception as e:
                        logger.error(f"Error force creating flag: {e}")
        
    except Exception as e:
        logger.error(f"Error in duplicate check for project {instance.id}: {e}")
        import traceback
        traceback.print_exc()
    
    if created:
        ProjectUser.objects.get_or_create(
            project=instance,
            user=instance.user,
            defaults={'role': 'lead'}
        )


# ================================================================
# ====== DISABLE/ENABLE SIGNAL FUNCTIONS ======
# ================================================================

_duplicate_check_receiver = None

def disable_duplicate_check():
    """Disable the duplicate check signal"""
    global _duplicate_check_receiver
    if _duplicate_check_receiver is None:
        _duplicate_check_receiver = check_duplicates_after_save
    post_save.disconnect(_duplicate_check_receiver, sender=Project)
    logger.info("🔒 DUPLICATE CHECK SIGNAL DISABLED")

def enable_duplicate_check():
    """Enable the duplicate check signal"""
    global _duplicate_check_receiver
    if _duplicate_check_receiver is not None:
        post_save.connect(_duplicate_check_receiver, sender=Project)
        logger.info("🔓 DUPLICATE CHECK SIGNAL ENABLED")