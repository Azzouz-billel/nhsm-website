import secrets

from django import forms
from django.contrib.auth.forms import PasswordChangeForm, UserCreationForm
from django.contrib.auth.password_validation import validate_password
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
        username.help_text = (
            "Pick a username you won't forget — you need it (with your "
            "recovery code) to reset your password."
        )
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


class StyledPasswordChangeForm(PasswordChangeForm):
    """Django's password-change form with the site's .field widget styling."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _style_fields(self.fields)


class RecoveryForm(forms.Form):
    """Self-service password reset: username + personal recovery code.

    The username and code are checked together so the error message never
    reveals which of the two was wrong (no account enumeration).
    """

    username = forms.CharField(max_length=30)
    recovery_code = forms.CharField(
        max_length=20,
        help_text="The code shown after sign-up and on your profile, e.g. A1B2-C3D4-E5F6.",
    )
    new_password1 = forms.CharField(label="New password", widget=forms.PasswordInput)
    new_password2 = forms.CharField(
        label="New password (again)", widget=forms.PasswordInput
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = None
        _style_fields(self.fields)

    def clean(self):
        cleaned = super().clean()
        password1 = cleaned.get("new_password1")
        password2 = cleaned.get("new_password2")
        if password1 and password2:
            if password1 != password2:
                self.add_error("new_password2", "The two passwords don't match.")
            else:
                validate_password(password1)

        username = cleaned.get("username")
        code = cleaned.get("recovery_code")
        if username and code:
            user = User.objects.filter(username__iexact=username).first()
            normalized = code.strip().upper()
            if user is None or not secrets.compare_digest(
                user.recovery_code, normalized
            ):
                raise forms.ValidationError("Wrong username or recovery code.")
            self.user = user
        return cleaned
