from rest_framework import serializers

from apps.resources.models import Subject

from .models import StudySession


class StudySessionSerializer(serializers.ModelSerializer):
    subject = serializers.PrimaryKeyRelatedField(
        queryset=Subject.objects.all(), required=False, allow_null=True
    )
    label = serializers.CharField(
        max_length=60, required=False, allow_blank=True, default=""
    )

    class Meta:
        model = StudySession
        fields = ["id", "subject", "label", "minutes"]

    def validate_minutes(self, value):
        if not 1 <= value <= 240:
            raise serializers.ValidationError("Minutes must be between 1 and 240.")
        return value

    def validate(self, data):
        subject = data.get("subject")
        label = (data.get("label") or "").strip()
        if not subject and not label:
            raise serializers.ValidationError(
                "Either a module or custom label is required."
            )
        if subject:
            data["label"] = ""
        else:
            data["label"] = label
        return data

