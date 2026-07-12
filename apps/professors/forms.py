from django import forms

from .models import RATING_TAGS, ProfessorRating


class RatingForm(forms.ModelForm):
    # Honeypot: hidden from humans; bots fill it and get rejected.
    hp_url = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={"tabindex": "-1", "autocomplete": "off"}),
    )
    # The user types the score (0–5).
    score = forms.DecimalField(
        min_value=0,
        max_value=5,
        decimal_places=1,
        max_digits=3,
        widget=forms.NumberInput(attrs={"min": 0, "max": 5, "step": "0.1"}),
        label="Your score (0–5)",
    )
    # No free text — pick from a safe, fixed vocabulary of teaching descriptors.
    tags = forms.MultipleChoiceField(
        choices=RATING_TAGS,
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label="What describes this teaching? (choose up to 3)",
    )
    agree = forms.BooleanField(
        required=True,
        label="I confirm this is my honest, respectful opinion about teaching — with "
        "no accusations, insults, or private information.",
    )

    class Meta:
        model = ProfessorRating
        fields = ("score", "tags")

    def clean_hp_url(self):
        if self.cleaned_data.get("hp_url"):
            raise forms.ValidationError("Spam detected.")
        return ""

    def clean_tags(self):
        tags = self.cleaned_data.get("tags", [])
        if len(tags) > 3:
            raise forms.ValidationError("Please choose at most 3 tags.")
        return tags

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["score"].widget.attrs["class"] = "field score-field"
