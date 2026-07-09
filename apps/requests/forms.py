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
    # Honeypot: hidden from humans; bots fill it and get rejected.
    hp_url = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={"tabindex": "-1", "autocomplete": "off"}),
    )

    class Meta:
        model = ResourceRequest
        fields = ("title", "subject", "description")
        widgets = {
            "description": forms.Textarea(
                attrs={"rows": 3, "placeholder": "What exactly do you need? e.g. TD 3 corrigé for Analyse 2"}
            )
        }

    def clean_hp_url(self):
        if self.cleaned_data.get("hp_url"):
            raise forms.ValidationError("Spam detected.")
        return ""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        cap_text(self.fields, ("title", "description"))
        for field in self.fields.values():
            existing = field.widget.attrs.get("class", "")
            field.widget.attrs["class"] = (existing + " field").strip()
