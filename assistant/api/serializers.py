from rest_framework import serializers

from assistant.views import QUESTION_MAX_LENGTH, QUESTION_MIN_LENGTH


class AskRequestSerializer(serializers.Serializer):
    q = serializers.CharField(
        min_length=QUESTION_MIN_LENGTH,
        max_length=QUESTION_MAX_LENGTH,
        trim_whitespace=True,
    )
    language = serializers.CharField(required=False, max_length=10)
