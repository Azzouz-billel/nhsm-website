from django import forms
from django.core.validators import MaxLengthValidator

from apps.accounts.models import Role, User
from apps.professors.models import Professor
from apps.resources.models import ExamPaper, Resource, Subject

from .models import Bulletin

MAX_TEXT = 70


def _cap(fields, names):
    """Cap the named text fields at MAX_TEXT (server validator + browser maxlength)."""
    for name in names:
        field = fields.get(name)
        if field is None:
            continue
        field.max_length = MAX_TEXT
        field.validators.append(MaxLengthValidator(MAX_TEXT))
        field.widget.attrs["maxlength"] = str(MAX_TEXT)


def _style(form):
    """Add the .field CSS class to every non-checkbox widget."""
    for field in form.fields.values():
        if isinstance(field.widget, forms.CheckboxInput):
            continue
        existing = field.widget.attrs.get("class", "")
        field.widget.attrs["class"] = (existing + " field").strip()


class SubjectAdminForm(forms.ModelForm):
    class Meta:
        model = Subject
        fields = ("name", "semester", "speciality", "description")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _cap(self.fields, ("name", "description"))
        _style(self)


class ResourceAdminForm(forms.ModelForm):
    class Meta:
        model = Resource
        fields = ("title", "subject", "resource_type", "drive_link", "description", "status")
        widgets = {"description": forms.Textarea(attrs={"rows": 3})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _cap(self.fields, ("title", "description"))
        _style(self)


class ExamAdminForm(forms.ModelForm):
    class Meta:
        model = ExamPaper
        fields = ("title", "subject", "year", "exam_type", "drive_link", "has_solution", "solution_link")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _cap(self.fields, ("title",))
        _style(self)


class UserRoleForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ("role", "academic_group", "is_active")

    def __init__(self, *args, editor=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.editor = editor
        # Only the owner (superuser) may grant the Admin role.
        if editor is not None and not editor.is_superuser:
            self.fields["role"].choices = [
                (value, label)
                for value, label in self.fields["role"].choices
                if value != Role.ADMIN
            ]
        _style(self)

    def clean_role(self):
        role = self.cleaned_data["role"]
        if role == Role.ADMIN and not (self.editor and self.editor.is_superuser):
            raise forms.ValidationError("Only the owner can assign the Admin role.")
        return role


class BulletinAdminForm(forms.ModelForm):
    class Meta:
        model = Bulletin
        fields = ("text_en", "text_ar", "link", "is_active", "order")
        widgets = {"text_ar": forms.TextInput(attrs={"dir": "rtl", "lang": "ar"})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _style(self)


class ProfessorAdminForm(forms.ModelForm):
    class Meta:
        model = Professor
        fields = ("name", "title", "photo_url", "is_active")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _style(self)
