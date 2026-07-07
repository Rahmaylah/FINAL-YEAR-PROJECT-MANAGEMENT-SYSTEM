from django.db import models


class SystemSettings(models.Model):
    ALGORITHM_CHOICES = [
        ('HYBRID', 'Hybrid'),
        ('EMBEDDING', 'Embedding'),
        ('TFIDF', 'TF-IDF'),
    ]

    duplicate_search_years_back = models.PositiveIntegerField(default=3)
    duplicate_similarity_threshold = models.FloatField(default=0.6)
    duplicate_auto_flag_threshold = models.FloatField(default=0.8)
    duplicate_algorithm = models.CharField(max_length=20, choices=ALGORITHM_CHOICES, default='HYBRID')
    duplicate_semantic_weight = models.FloatField(default=0.7)
    duplicate_lexical_weight = models.FloatField(default=0.3)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        return

    @classmethod
    def get_solo(cls):
        defaults = {
            'duplicate_search_years_back': 3,
            'duplicate_similarity_threshold': 0.6,
            'duplicate_auto_flag_threshold': 0.8,
            'duplicate_algorithm': 'HYBRID',
            'duplicate_semantic_weight': 0.7,
            'duplicate_lexical_weight': 0.3,
        }
        return cls.objects.get_or_create(pk=1, defaults=defaults)[0]

    def __str__(self):
        return 'System Settings'
