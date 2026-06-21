from django import forms

from .models import Resource


class ResourceUploadForm(forms.ModelForm):
    class Meta:
        model = Resource
        fields = ("title", "subject", "resource_type", "drive_link", "description")
        widgets = {"description": forms.Textarea(attrs={"rows": 3})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            existing = field.widget.attrs.get("class", "")
            field.widget.attrs["class"] = (existing + " field").strip()
