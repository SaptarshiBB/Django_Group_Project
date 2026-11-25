"""
Tests for Upload Validation (file types, size limits, corrupted images).
"""
import io
from PIL import Image
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from apps.scans.forms import ScanUploadForm


class UploadValidationTestCase(TestCase):
    def _create_test_image(self, format_name="JPEG", size=(100, 100), color="blue"):
        file_obj = io.BytesIO()
        image = Image.new("RGB", size, color=color)
        image.save(file_obj, format=format_name)
        file_obj.seek(0)
        return file_obj

    def test_valid_image_upload_passes(self):
        img_io = self._create_test_image("JPEG")
        uploaded_file = SimpleUploadedFile("label_front.jpg", img_io.read(), content_type="image/jpeg")

        form = ScanUploadForm(
            data={"product_name": "Test Atta", "category": "food"},
            files={"images": [uploaded_file]},
        )
        self.assertTrue(form.is_valid(), form.errors)

    def test_invalid_extension_rejected(self):
        dummy_file = SimpleUploadedFile("malicious.exe", b"binarycontent", content_type="application/octet-stream")
        form = ScanUploadForm(
            data={"product_name": "Test Bad", "category": "general"},
            files={"images": [dummy_file]},
        )
        self.assertFalse(form.is_valid())
        self.assertIn("images", form.errors)

    def test_fake_image_file_rejected(self):
        # A file with .png extension but non-image content
        fake_img = SimpleUploadedFile("fake.png", b"NOT AN IMAGE", content_type="image/png")
        form = ScanUploadForm(
            data={"product_name": "Test Fake", "category": "general"},
            files={"images": [fake_img]},
        )
        self.assertFalse(form.is_valid())
        self.assertIn("images", form.errors)
