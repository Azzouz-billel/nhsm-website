from rest_framework import serializers

from apps.resources.models import Subject

from .models import StudySession


class StudySessionSerializer(serializers.ModelSerializer):
    subject = serializers.PrimaryKeyRelatedField(queryset=Subject.objects.all())

    class Meta:
        model = StudySession
        fields = ["id", "subject", "minutes"]

    def validate_minutes(self, value):
        if not 1 <= value <= 240:
            raise serializers.ValidationError("Minutes must be between 1 and 240.")
        return value
