"""
Optical Character Recognition (OCR) Service.
Handles image preprocessing (rescaling, denoising, deskewing, thresholding)
via OpenCV & Pillow, and character recognition via Tesseract with confidence scores.
"""
import logging
import math
from typing import Dict, Tuple
import cv2
import numpy as np
from PIL import Image
from django.conf import settings

logger = logging.getLogger(__name__)


class OCRServiceError(Exception):
    """Custom exception raised when OCR processing fails."""
    pass


class OCRPipeline:
    """Production OCR preprocessing and text recognition pipeline."""

    def __init__(self):
        self.tesseract_cmd = getattr(settings, "TESSERACT_CMD", "")
        self.langs = getattr(settings, "TESSERACT_LANGS", "eng")
        self.min_confidence = getattr(settings, "OCR_MIN_CONFIDENCE", 45.0)

        # Configure pytesseract path if specified in settings
        if self.tesseract_cmd:
            try:
                import pytesseract
                pytesseract.pytesseract.tesseract_cmd = self.tesseract_cmd
            except Exception as e:
                logger.warning("Could not set pytesseract command path: %s", e)

    def preprocess_image(self, pil_image: Image.Image) -> np.ndarray:
        """
        Apply enterprise-grade preprocessing:
        1. Upscale if small (ensuring crisp glyphs)
        2. Convert to grayscale
        3. Denoise with edge-preserving bilateral filtering
        4. Detect deskew angle and deskew image
        5. Adaptive thresholding / Otsu binarization
        """
        # Convert PIL to OpenCV BGR format
        open_cv_image = np.array(pil_image.convert("RGB"))
        img_bgr = cv2.cvtColor(open_cv_image, cv2.COLOR_RGB2BGR)

        # 1. Upscale if image is low resolution (< 1200px on any dimension)
        h, w = img_bgr.shape[:2]
        if w < 1200 or h < 1200:
            scale_factor = max(1200 / max(w, 1), 1200 / max(h, 1))
            # Limit scale to at most 3x to avoid excessive memory usage
            scale_factor = min(scale_factor, 3.0)
            if scale_factor > 1.05:
                img_bgr = cv2.resize(
                    img_bgr,
                    (int(w * scale_factor), int(h * scale_factor)),
                    interpolation=cv2.INTER_CUBIC,
                )

        # 2. Grayscale conversion
        gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)

        # 3. Bilateral filter for edge-preserving denoising
        denoised = cv2.bilateralFilter(gray, d=9, sigmaColor=75, sigmaSpace=75)

        # 4. Deskewing
        deskewed = self._deskew(denoised)

        # 5. Otsu thresholding after subtle Gaussian blur
        blurred = cv2.GaussianBlur(deskewed, (3, 3), 0)
        _, thresh = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

        return thresh

    def _deskew(self, image: np.ndarray) -> np.ndarray:
        """Detect dominant text angle and rotate image to level text lines."""
        try:
            # Invert image (white text on black background for contour/component analysis)
            inv = cv2.bitwise_not(image)
            coords = np.column_stack(np.where(inv > 0))
            if coords.shape[0] < 50:
                return image

            angle = cv2.minAreaRect(coords)[-1]
            if angle < -45:
                angle = -(90 + angle)
            elif angle > 45:
                angle = 90 - angle

            # Only rotate if tilt is noticeable (between 0.5 and 45 degrees)
            if abs(angle) > 0.5 and abs(angle) <= 45.0:
                (h, w) = image.shape[:2]
                center = (w // 2, h // 2)
                m = cv2.getRotationMatrix2D(center, angle, 1.0)
                rotated = cv2.warpAffine(
                    image,
                    m,
                    (w, h),
                    flags=cv2.INTER_CUBIC,
                    borderMode=cv2.BORDER_REPLICATE,
                )
                return rotated
        except Exception as e:
            logger.debug("Deskew calculation skipped: %s", e)
        return image

    def extract_text(self, image_input) -> Tuple[str, float, Dict]:
        """
        Run OCR on image and return:
        - raw_text: string of recognized text
        - avg_confidence: float between 0.0 and 100.0
        - metadata: dict of detailed metrics
        """
        try:
            import pytesseract
        except ImportError:
            raise OCRServiceError(
                "pytesseract library is not installed. Please install requirements."
            )

        # Open PIL Image if file path or file-like object
        try:
            if isinstance(image_input, (str, bytes)):
                pil_image = Image.open(image_input)
            elif hasattr(image_input, "path"):
                pil_image = Image.open(image_input.path)
            elif hasattr(image_input, "read"):
                image_input.seek(0)
                pil_image = Image.open(image_input)
            elif isinstance(image_input, Image.Image):
                pil_image = image_input
            else:
                pil_image = Image.open(image_input)
        except Exception as e:
            logger.error("Failed to open image for OCR: %s", e)
            raise OCRServiceError(f"Invalid or corrupted image format: {e}")

        # Preprocess using OpenCV
        try:
            processed_cv_img = self.preprocess_image(pil_image)
            processed_pil = Image.fromarray(processed_cv_img)
        except Exception as e:
            logger.warning("Advanced preprocessing failed, falling back to original PIL: %s", e)
            processed_pil = pil_image.convert("L")

        # Run Tesseract OCR
        try:
            # Extract detailed word-level data dictionary
            ocr_data = pytesseract.image_to_data(
                processed_pil,
                lang=self.langs,
                output_type=pytesseract.Output.DICT,
                config="--psm 3",
            )
            raw_text = pytesseract.image_to_string(
                processed_pil,
                lang=self.langs,
                config="--psm 3",
            ).strip()

            # Calculate confidences
            confidences = []
            words = []
            for word, conf in zip(ocr_data.get("text", []), ocr_data.get("conf", [])):
                try:
                    c_val = float(conf)
                    if c_val >= 0 and word.strip():
                        confidences.append(c_val)
                        words.append(word.strip())
                except (ValueError, TypeError):
                    continue

            avg_conf = (
                float(sum(confidences) / len(confidences))
                if confidences
                else 0.0
            )

            metadata = {
                "word_count": len(words),
                "words_above_threshold": sum(1 for c in confidences if c >= self.min_confidence),
                "total_tokens_evaluated": len(confidences),
            }

            return raw_text, round(avg_conf, 2), metadata

        except pytesseract.TesseractNotFoundError:
            msg = (
                "Tesseract-OCR executable not found on host. "
                "Ensure Tesseract is installed and TESSERACT_CMD is properly set in your .env file."
            )
            logger.error(msg)
            # Graceful degradation: return empty text with 0.0 confidence and clear diagnostic note
            return "", 0.0, {"error": "TESSERACT_NOT_INSTALLED", "message": msg}
        except Exception as e:
            logger.error("Error during OCR execution: %s", e)
            return "", 0.0, {"error": "OCR_EXECUTION_FAILURE", "message": str(e)}
