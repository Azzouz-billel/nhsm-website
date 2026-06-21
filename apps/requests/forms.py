from django import forms

from .models import ResourceRequest


class RequestForm(forms.ModelForm):
    class Meta:
        model = ResourceRequest
        fields = ("title", "subject", "description")
        widgets = {
            "description": forms.Textarea(
                attrs={"rows": 3, "placeholder": "What exactly do you need? e.g. TD 3 corrigé for Analyse 2"}
            )
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            existing = field.widget.attrs.get("class", "")
            field.widget.attrs["class"] = (existing + " field").strip()
