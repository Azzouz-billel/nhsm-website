from django import forms

from .models import ProfessorRating


class RatingForm(forms.ModelForm):
    # Honeypot: hidden from humans; bots fill it and get rejected.
    hp_url = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={"tabindex": "-1", "autocomplete": "off"}),
    )
    # The user types the score (0–5) rather than picking from stars.
    score = forms.DecimalField(
        min_value=0,
        max_value=5,
        decimal_places=1,
        max_digits=3,
        widget=forms.NumberInput(attrs={"min": 0, "max": 5, "step": "0.1", "placeholder": "0–5 (e.g. 3.5)"}),
        label="Your score (0–5)",
    )

    class Meta:
        model = ProfessorRating
        fields = ("score", "comment")
        widgets = {
            "comment": forms.Textarea(
                attrs={
                    "rows": 3,
                    "maxlength": 280,
                    "placeholder": "Why? A short note — clarity, fairness, how they teach…",
                }
            )
        }

    def clean_hp_url(self):
        if self.cleaned_data.get("hp_url"):
            raise forms.ValidationError("Spam detected.")
        return ""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["comment"].required = False
        self.fields["score"].widget.attrs["class"] = "field score-field"
        self.fields["comment"].widget.attrs["class"] = "field"
