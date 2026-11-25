"""
Forms for Scan creation, multi-image upload validation, and field editing.
"""
from PIL import Image as PILImage
from django import forms
from django.conf import settings
from .models import ExtractedField, Scan


class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class MultipleFileField(forms.FileField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("widget", MultipleFileInput())
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        single_file_clean = super().clean
        if isinstance(data, (list, tuple)):
            result = [single_file_clean(d, initial) for d in data]
        else:
            result = [single_file_clean(data, initial)] if data else []
        return result


class ScanUploadForm(forms.ModelForm):
    images = MultipleFileField(
        label="Packaging & Label Images",
        required=True,
        help_text="Upload one or more panel images (Front, Back, Side). Supported formats: JPG, PNG, WEBP.",
    )

    class Meta:
        model = Scan
        fields = ("product_name", "category", "pre_packed_type", "notes")
        widgets = {
            "product_name": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "e.g., Organic Whole Wheat Atta"}
            ),
            "category": forms.Select(attrs={"class": "form-control"}),
            "pre_packed_type": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "e.g., Standard Retail Pouch, Rigid Bottle"}
            ),
            "notes": forms.Textarea(
                attrs={"class": "form-control", "rows": 3, "placeholder": "Inspector notes or observations"}
            ),
        }

    def clean_images(self):
        uploaded_files = self.cleaned_data.get("images", [])
        if not uploaded_files:
            raise forms.ValidationError("Please select at least one packaging image.")

        max_mb = getattr(settings, "MAX_UPLOAD_SIZE_MB", 10)
        max_bytes = max_mb * 1024 * 1024
        allowed_types = [t.lower().strip() for t in getattr(settings, "ALLOWED_IMAGE_TYPES", ["jpg", "jpeg", "png", "webp"])]

        for f in uploaded_files:
            # 1. Size verification
            if f.size > max_bytes:
                raise forms.ValidationError(
                    f"File '{f.name}' exceeds the maximum allowed size of {max_mb} MB."
                )

            # 2. Extension verification
            ext = f.name.split(".")[-1].lower() if "." in f.name else ""
            if ext not in allowed_types:
                raise forms.ValidationError(
                    f"File '{f.name}' has invalid extension .{ext}. Allowed extensions: {', '.join(allowed_types)}."
                )

            # 3. Content verification via Pillow
            try:
                img = PILImage.open(f)
                img.verify()
                # Reset file pointer after verify
                f.seek(0)
            except Exception:
                raise forms.ValidationError(
                    f"File '{f.name}' is not a valid or readable image file."
                )

        return uploaded_files
