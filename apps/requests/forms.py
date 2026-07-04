from django import forms
from django.core.validators import MaxLengthValidator

from .models import ResourceRequest

# Keep titles and descriptions short and scannable across the whole site.
MAX_TEXT = 70


def cap_text(fields, names, maximum=MAX_TEXT):
    """Enforce a character limit (server-side validator + browser maxlength)."""
    for name in names:
        field = fields.get(name)
        if field is None:
            continue
        field.max_length = maximum
        field.validators.append(MaxLengthValidator(maximum))
        field.widget.attrs["maxlength"] = str(maximum)


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
        cap_text(self.fields, ("title", "description"))
        for field in self.fields.values():
            existing = field.widget.attrs.get("class", "")
            field.widget.attrs["class"] = (existing + " field").strip()
