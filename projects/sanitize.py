"""
Data Sanitization Utilities

This module provides functions for sanitizing user inputs to prevent XSS,
SQL injection, and other security vulnerabilities.
"""

import re
import json
from typing import Any, Dict, List, Optional, Union
from django.utils.html import escape, strip_tags
from django.core.validators import validate_email
from django.core.exceptions import ValidationError


class Sanitizer:
    """
    Utility class for sanitizing various types of user inputs.
    """

    @staticmethod
    def sanitize_string(value: Optional[str], allow_empty: bool = False) -> str:
        """
        Sanitize a string by stripping HTML tags and escaping special characters.

        Args:
            value: The string to sanitize
            allow_empty: Whether to allow empty string

        Returns:
            Sanitized string
        """
        if value is None:
            return "" if allow_empty else ""

        if not isinstance(value, str):
            value = str(value)

        # Remove HTML tags
        value = strip_tags(value)
        # Escape HTML entities
        value = escape(value)
        # Remove extra whitespace
        value = re.sub(r'\s+', ' ', value).strip()

        if not allow_empty and not value:
            return ""

        return value

    @staticmethod
    def sanitize_text(value: Optional[str], allow_empty: bool = False) -> str:
        """
        Sanitize text while preserving line breaks and basic formatting.

        Args:
            value: The text to sanitize
            allow_empty: Whether to allow empty string

        Returns:
            Sanitized text
        """
        if value is None:
            return "" if allow_empty else ""

        if not isinstance(value, str):
            value = str(value)

        # Remove script tags and dangerous attributes
        value = re.sub(r'<script.*?>.*?</script>', '', value, flags=re.DOTALL)
        value = re.sub(r'<iframe.*?>.*?</iframe>', '', value, flags=re.DOTALL)
        value = re.sub(r'on\w+="[^"]*"', '', value)
        value = re.sub(r'on\w+=\'[^\']*\'', '', value)
        value = re.sub(r'javascript:', '', value)

        # Escape HTML entities
        value = escape(value)
        # Remove extra whitespace
        value = re.sub(r'[ \t]+', ' ', value)

        if not allow_empty and not value:
            return ""

        return value

    @staticmethod
    def sanitize_email(email: Optional[str]) -> Optional[str]:
        """
        Validate and sanitize an email address.

        Args:
            email: The email address to sanitize

        Returns:
            Sanitized email or None if invalid
        """
        if not email:
            return None

        email = email.strip().lower()
        try:
            validate_email(email)
            return email
        except ValidationError:
            return None

    @staticmethod
    def sanitize_username(username: Optional[str]) -> Optional[str]:
        """
        Sanitize a username by allowing only alphanumeric characters, underscores, and dots.

        Args:
            username: The username to sanitize

        Returns:
            Sanitized username or None if invalid
        """
        if not username:
            return None

        username = username.strip()
        # Allow only alphanumeric, underscore, dot, and hyphen
        username = re.sub(r'[^a-zA-Z0-9_.-]', '', username)

        if len(username) < 3:
            return None

        return username

    @staticmethod
    def sanitize_number(value: Any, min_val: Optional[float] = None, max_val: Optional[float] = None) -> Optional[float]:
        """
        Sanitize a number with optional range validation.

        Args:
            value: The number to sanitize
            min_val: Minimum allowed value
            max_val: Maximum allowed value

        Returns:
            Sanitized number or None if invalid
        """
        if value is None:
            return None

        try:
            num = float(value)
        except (TypeError, ValueError):
            return None

        if min_val is not None and num < min_val:
            return None
        if max_val is not None and num > max_val:
            return None

        return num

    @staticmethod
    def sanitize_integer(value: Any, min_val: Optional[int] = None, max_val: Optional[int] = None) -> Optional[int]:
        """
        Sanitize an integer with optional range validation.

        Args:
            value: The integer to sanitize
            min_val: Minimum allowed value
            max_val: Maximum allowed value

        Returns:
            Sanitized integer or None if invalid
        """
        if value is None:
            return None

        try:
            num = int(value)
        except (TypeError, ValueError):
            return None

        if min_val is not None and num < min_val:
            return None
        if max_val is not None and num > max_val:
            return None

        return num

    @staticmethod
    def sanitize_json(data: Any) -> Any:
        """
        Sanitize JSON data by recursively sanitizing strings and validating structure.

        Args:
            data: The JSON data to sanitize

        Returns:
            Sanitized JSON data
        """
        if data is None:
            return None

        if isinstance(data, str):
            return Sanitizer.sanitize_string(data)

        if isinstance(data, dict):
            return {Sanitizer.sanitize_string(k): Sanitizer.sanitize_json(v) for k, v in data.items()}

        if isinstance(data, list):
            return [Sanitizer.sanitize_json(item) for item in data]

        if isinstance(data, (int, float, bool)):
            return data

        return data

    @staticmethod
    def sanitize_filename(filename: Optional[str]) -> Optional[str]:
        """
        Sanitize a filename by removing dangerous characters.

        Args:
            filename: The filename to sanitize

        Returns:
            Sanitized filename or None if invalid
        """
        if not filename:
            return None

        # Remove path separators and dangerous characters
        filename = re.sub(r'[/\\:*?"<>|]', '', filename)
        filename = filename.strip()
        filename = re.sub(r'\s+', '_', filename)

        if not filename:
            return None

        return filename

    @staticmethod
    def sanitize_slug(slug: Optional[str]) -> Optional[str]:
        """
        Sanitize a slug by allowing only lowercase letters, numbers, and hyphens.

        Args:
            slug: The slug to sanitize

        Returns:
            Sanitized slug or None if invalid
        """
        if not slug:
            return None

        slug = slug.lower().strip()
        slug = re.sub(r'[^a-z0-9-]', '-', slug)
        slug = re.sub(r'-+', '-', slug)
        slug = slug.strip('-')

        if not slug:
            return None

        return slug

    @staticmethod
    def sanitize_options(options: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Sanitize options for presentation criteria.

        Args:
            options: List of option dictionaries with 'label' and 'value' keys

        Returns:
            Sanitized options list
        """
        if not options or not isinstance(options, list):
            return []

        sanitized = []
        for option in options:
            if not isinstance(option, dict):
                continue

            label = Sanitizer.sanitize_string(option.get('label', ''))
            value = Sanitizer.sanitize_number(option.get('value'), min_val=0)

            if label and value is not None:
                sanitized.append({
                    'label': label,
                    'value': value
                })

        return sanitized

    @staticmethod
    def sanitize_comment(comment: Optional[str]) -> str:
        """
        Sanitize a comment by allowing basic formatting but removing dangerous content.

        Args:
            comment: The comment to sanitize

        Returns:
            Sanitized comment
        """
        if not comment:
            return ""

        # Remove script tags
        comment = re.sub(r'<script.*?>.*?</script>', '', comment, flags=re.DOTALL)
        # Remove iframe tags
        comment = re.sub(r'<iframe.*?>.*?</iframe>', '', comment, flags=re.DOTALL)
        # Remove event handlers
        comment = re.sub(r'on\w+="[^"]*"', '', comment)
        comment = re.sub(r'on\w+=\'[^\']*\'', '', comment)
        # Remove javascript: protocol
        comment = re.sub(r'javascript:', '', comment)

        # Escape HTML
        comment = escape(comment)

        # Allow basic line breaks
        comment = comment.replace('\n', '<br>')

        return comment


def sanitize_string(value: Optional[str], allow_empty: bool = False) -> str:
    """Wrapper for Sanitizer.sanitize_string"""
    return Sanitizer.sanitize_string(value, allow_empty)


def sanitize_text(value: Optional[str], allow_empty: bool = False) -> str:
    """Wrapper for Sanitizer.sanitize_text"""
    return Sanitizer.sanitize_text(value, allow_empty)


def sanitize_email(email: Optional[str]) -> Optional[str]:
    """Wrapper for Sanitizer.sanitize_email"""
    return Sanitizer.sanitize_email(email)


def sanitize_username(username: Optional[str]) -> Optional[str]:
    """Wrapper for Sanitizer.sanitize_username"""
    return Sanitizer.sanitize_username(username)


def sanitize_number(value: Any, min_val: Optional[float] = None, max_val: Optional[float] = None) -> Optional[float]:
    """Wrapper for Sanitizer.sanitize_number"""
    return Sanitizer.sanitize_number(value, min_val, max_val)


def sanitize_integer(value: Any, min_val: Optional[int] = None, max_val: Optional[int] = None) -> Optional[int]:
    """Wrapper for Sanitizer.sanitize_integer"""
    return Sanitizer.sanitize_integer(value, min_val, max_val)


def sanitize_json(data: Any) -> Any:
    """Wrapper for Sanitizer.sanitize_json"""
    return Sanitizer.sanitize_json(data)


def sanitize_filename(filename: Optional[str]) -> Optional[str]:
    """Wrapper for Sanitizer.sanitize_filename"""
    return Sanitizer.sanitize_filename(filename)


def sanitize_slug(slug: Optional[str]) -> Optional[str]:
    """Wrapper for Sanitizer.sanitize_slug"""
    return Sanitizer.sanitize_slug(slug)


def sanitize_options(options: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Wrapper for Sanitizer.sanitize_options"""
    return Sanitizer.sanitize_options(options)


def sanitize_comment(comment: Optional[str]) -> str:
    """Wrapper for Sanitizer.sanitize_comment"""
    return Sanitizer.sanitize_comment(comment)


def validate_and_sanitize_presentation_criteria_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate and sanitize presentation criteria data.

    Args:
        data: Raw presentation criteria data

    Returns:
        Sanitized and validated data
    """
    sanitized = {}

    # Sanitize name
    if 'name' in data:
        sanitized['name'] = sanitize_string(data['name'])

    # Sanitize description
    if 'description' in data:
        sanitized['description'] = sanitize_text(data['description'], allow_empty=True)

    # Sanitize max_score
    if 'max_score' in data:
        sanitized['max_score'] = sanitize_number(data['max_score'], min_val=0)
    else:
        sanitized['max_score'] = 10.0

    # Sanitize weight
    if 'weight' in data:
        sanitized['weight'] = sanitize_number(data['weight'], min_val=0)
    else:
        sanitized['weight'] = 1.0

    # Sanitize order
    if 'order' in data:
        sanitized['order'] = sanitize_integer(data['order'], min_val=0)
    else:
        sanitized['order'] = 0

    # Sanitize is_required
    if 'is_required' in data:
        sanitized['is_required'] = bool(data['is_required'])
    else:
        sanitized['is_required'] = True

    # Sanitize options
    if 'options' in data:
        sanitized['options'] = sanitize_options(data['options'])
    else:
        sanitized['options'] = []

    # Sanitize presentation_id
    if 'presentation' in data:
        sanitized['presentation'] = sanitize_integer(data['presentation'])

    return sanitized


def validate_and_sanitize_criteria_score_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate and sanitize presentation result criteria score data.

    Args:
        data: Raw criteria score data

    Returns:
        Sanitized and validated data
    """
    sanitized = {}

    # Sanitize score
    if 'score' in data:
        sanitized['score'] = sanitize_number(data['score'], min_val=0)

    # Sanitize selected_option
    if 'selected_option' in data:
        sanitized['selected_option'] = sanitize_string(data['selected_option'], allow_empty=True)

    # Sanitize comment
    if 'comment' in data:
        sanitized['comment'] = sanitize_comment(data['comment'])

    # Sanitize result_id
    if 'result' in data:
        sanitized['result'] = sanitize_integer(data['result'])

    # Sanitize criteria_id
    if 'criteria' in data:
        sanitized['criteria'] = sanitize_integer(data['criteria'])

    return sanitized

# Add these to your serializers.py

class PresentationCriteriaSerializer(serializers.ModelSerializer):
    class Meta:
        model = PresentationCriteria
        fields = [
            'id', 'presentation', 'name', 'description', 
            'max_score', 'weight', 'order', 'is_required', 
            'options', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']


class PresentationResultCriteriaSerializer(serializers.ModelSerializer):
    criteria_name = serializers.CharField(source='criteria.name', read_only=True)
    criteria_max_score = serializers.FloatField(source='criteria.max_score', read_only=True)
    criteria_weight = serializers.FloatField(source='criteria.weight', read_only=True)

    class Meta:
        model = PresentationResultCriteria
        fields = [
            'id', 'result', 'criteria', 'criteria_name', 
            'criteria_max_score', 'criteria_weight', 
            'score', 'selected_option', 'comment', 
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']


# Update PresentationResultSerializer
class PresentationResultSerializer(serializers.ModelSerializer):
    presentation_name = serializers.CharField(source='presentation.name', read_only=True)
    presentation_date = serializers.DateField(source='presentation.presentation_date', read_only=True)
    presentation_total_marks = serializers.FloatField(source='presentation.total_marks', read_only=True)
    presentation_pass_marks = serializers.FloatField(source='presentation.pass_marks', read_only=True)
    student_name = serializers.SerializerMethodField()
    project_title = serializers.CharField(source='project.title', read_only=True)
    reviewer_name = serializers.SerializerMethodField()
    criteria_scores = PresentationResultCriteriaSerializer(many=True, read_only=True)
    weighted_total = serializers.SerializerMethodField()
    
    class Meta:
        model = PresentationResult
        fields = [
            'id', 'presentation', 'presentation_name', 'presentation_date', 
            'presentation_total_marks', 'presentation_pass_marks', 
            'student', 'student_name', 'project', 'project_title', 
            'reviewer', 'reviewer_name', 'comment', 'marks', 
            'criteria_total', 'is_graded_by_criteria',
            'criteria_scores', 'weighted_total',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'presentation_name', 'presentation_date', 'presentation_total_marks', 
            'presentation_pass_marks', 'student_name', 'project_title', 
            'reviewer_name', 'created_at', 'updated_at',
            'criteria_scores', 'weighted_total', 'criteria_total'
        ]

    def get_student_name(self, obj):
        if obj.student:
            return f"{obj.student.first_name} {obj.student.middle_name} {obj.student.last_name}".strip()
        return None

    def get_reviewer_name(self, obj):
        if obj.reviewer:
            return f"{obj.reviewer.first_name} {obj.reviewer.middle_name} {obj.reviewer.last_name}".strip()
        return None

    def get_weighted_total(self, obj):
        """Calculate weighted total score from criteria scores"""
        if obj.is_graded_by_criteria:
            return obj.criteria_total
        return None