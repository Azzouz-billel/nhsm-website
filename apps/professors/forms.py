from django import forms

from .models import ProfessorRating

SCORE_CHOICES = [(i, str(i)) for i in range(0, 6)]


class RatingForm(forms.ModelForm):
    # Honeypot: hidden from humans; bots fill it and get rejected.
    hp_url = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={"tabindex": "-1", "autocomplete": "off"}),
    )
    score = forms.TypedChoiceField(
        choices=SCORE_CHOICES,
        coerce=int,
        widget=forms.RadioSelect,
        label="Your rating",
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
        # The score renders as a custom star widget, so keep it class-free.
        self.fields["comment"].widget.attrs["class"] = "field"
