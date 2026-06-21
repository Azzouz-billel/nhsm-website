from rest_framework import serializers

from .models import ExamPaper, Resource


class ResourceSerializer(serializers.ModelSerializer):
    subject_name = serializers.CharField(source="subject.name", read_only=True)
    subject_slug = serializers.CharField(source="subject.slug", read_only=True)
    semester = serializers.IntegerField(source="subject.semester", read_only=True)
    type_label = serializers.CharField(source="get_resource_type_display", read_only=True)

    class Meta:
        model = Resource
        fields = [
            "id",
            "title",
            "subject_name",
            "subject_slug",
            "semester",
            "resource_type",
            "type_label",
            "drive_link",
            "description",
            "created_at",
        ]


class ExamPaperSerializer(serializers.ModelSerializer):
    subject_name = serializers.CharField(source="subject.name", read_only=True)
    subject_slug = serializers.CharField(source="subject.slug", read_only=True)
    semester = serializers.IntegerField(source="subject.semester", read_only=True)
    type_label = serializers.CharField(source="get_exam_type_display", read_only=True)

    class Meta:
        model = ExamPaper
        fields = [
            "id",
            "title",
            "subject_name",
            "subject_slug",
            "semester",
            "year",
            "exam_type",
            "type_label",
            "drive_link",
            "has_solution",
            "solution_link",
        ]
