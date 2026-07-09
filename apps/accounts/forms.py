from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.core.validators import MaxLengthValidator

from .models import AcademicGroup, User


def _style_fields(fields):
    """Add the .field CSS class to text-like widgets (checkboxes keep their own)."""
    for field in fields.values():
        widget = field.widget
        if isinstance(widget, forms.CheckboxInput):
            continue
        existing = widget.attrs.get("class", "")
        widget.attrs["class"] = (existing + " field").strip()


class RegistrationForm(UserCreationForm):
    email = forms.EmailField(required=False)
    academic_group = forms.ChoiceField(
        choices=[("", "— Select your group —")] + list(AcademicGroup.choices),
        required=True,
    )
    display_name = forms.CharField(max_length=60, required=False)
    # Honeypot: hidden from humans; bots fill it and get rejected.
    hp_url = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={"tabindex": "-1", "autocomplete": "off"}),
    )

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "email")

    def clean_hp_url(self):
        if self.cleaned_data.get("hp_url"):
            raise forms.ValidationError("Spam detected.")
        return ""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        username = self.fields["username"]
        username.max_length = 30
        username.validators.append(MaxLengthValidator(30))
        username.widget.attrs["maxlength"] = "30"
        _style_fields(self.fields)

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data.get("email", "")
        user.academic_group = self.cleaned_data.get("academic_group", "")
        user.display_name = self.cleaned_data.get("display_name", "")
        if commit:
            user.save()
        return user


class ProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = (
            "display_name",
            "email",
            "academic_group",
            "is_anonymous_on_board",
            "theme_preference",
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _style_fields(self.fields)
