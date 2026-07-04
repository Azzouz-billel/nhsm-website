from django import forms

from .models import Resource


class ResourceUploadForm(forms.ModelForm):
    # Keep student submissions short and scannable: 70 chars each. max_length
    # gives both server-side validation and the browser's maxlength attribute.
    title = forms.CharField(max_length=70)
    description = forms.CharField(
        max_length=70,
        required=False,
        widget=forms.Textarea(attrs={"rows": 3}),
    )

    class Meta:
        model = Resource
        fields = ("title", "subject", "resource_type", "drive_link", "description")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            existing = field.widget.attrs.get("class", "")
            field.widget.attrs["class"] = (existing + " field").strip()
