from django import forms
from django.contrib.auth.forms import UserCreationForm

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
        required=False,
    )
    display_name = forms.CharField(max_length=60, required=False)

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "email")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
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
