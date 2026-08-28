import html
import re
from django import forms

from .models import GuestbookComment


class GuestbookCommentForm(forms.ModelForm):
    class Meta:
        model = GuestbookComment
        fields = ["text"]
        widgets = {
            "text": forms.Textarea(
                attrs={
                    "rows": 3,
                    "maxlength": 280,
                    "placeholder": "Share an encouraging message for fellow students or describe how NHSM Hub helped you with your studies!",
                }
            )
        }

    def clean_text(self):
        text = self.cleaned_data.get("text", "").strip()

        # 1. Strip raw HTML tags to prevent XSS injection attacks
        clean_text = re.sub(r"<[^>]*>", "", text)

        # 2. Escape any special HTML character entities
        clean_text = html.escape(clean_text)

        # 3. Collapse multiple blank lines/newlines
        clean_text = re.sub(r"\n{3,}", "\n\n", clean_text).strip()

        # 4. Enforce strict character limits
        if len(clean_text) < 3:
            raise forms.ValidationError("Comments must be at least 3 characters long.")

        if len(clean_text) > 280:
            raise forms.ValidationError("Comments cannot exceed 280 characters.")

        return clean_text
