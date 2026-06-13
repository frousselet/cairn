from rest_framework import serializers

from assistant.models import AssistantFeedback
from assistant.views import QUESTION_MAX_LENGTH, QUESTION_MIN_LENGTH


class AskRequestSerializer(serializers.Serializer):
    q = serializers.CharField(
        min_length=QUESTION_MIN_LENGTH,
        max_length=QUESTION_MAX_LENGTH,
        trim_whitespace=True,
    )
    language = serializers.CharField(required=False, max_length=10)


class AssistantFeedbackSerializer(serializers.ModelSerializer):
    user_email = serializers.CharField(source="user.email", read_only=True, default=None)
    rating_display = serializers.CharField(source="get_rating_display", read_only=True)

    class Meta:
        model = AssistantFeedback
        fields = [
            "id", "created_at", "user", "user_email", "question", "language",
            "rating", "rating_display", "comment", "summary", "results",
            "degraded", "refused_tools", "provider", "model_name",
            "is_resolved", "resolved_at", "resolved_by",
        ]
        read_only_fields = [
            "id", "created_at", "user", "user_email", "rating_display",
            "is_resolved", "resolved_at", "resolved_by",
        ]
