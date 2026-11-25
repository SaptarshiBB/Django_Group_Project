# Legal Metrology Packaged Commodity Compliance Checker

An enterprise-grade Django web application designed for statutory compliance enforcement under the **Legal Metrology (Packaged Commodities) Rules, 2011** (Ministry of Consumer Affairs, Food & Public Distribution, Government of India).

The system scans specimen packaging/label photographs, preprocesses the imagery with OpenCV and Pillow, extracts text via Tesseract OCR, parses mandatory packaging declarations using rule-based regular expressions and NLP heuristics, evaluates compliance against statutory rules, and produces downloadable official A4 PDF verification reports via ReportLab.

---

## Key Features

1. **Enterprise Packaging OCR Pipeline**:
   - Automated image preprocessing: upscale small images (<1200px), grayscale conversion, bilateral edge-preserving denoising, orientation deskewing (via minAreaRect), and Otsu adaptive thresholding.
   - Pytesseract integration with per-word token confidence scoring and average panel confidence metrics.
   - Multi-panel label merging (e.g., front Principal Display Panel + back Information Panel).

2. **Statutory Field Extraction (`services/extractor.py`)**:
   - **Rule 6(1)(a)**: Name & complete postal address of manufacturer / packer / importer.
   - **Rule 6(1)(b)**: Common or generic name of the commodity.
   - **Rule 6(1)(c) & Rule 12**: Net quantity in standard SI metric units (g, kg, ml, L, N).
   - **Rule 12(1)**: Detection and flag of prohibited qualifiers (*approx*, *about*, *when packed*).
   - **Rule 6(1)(d)**: Month and year of manufacture, packing, or import (MM/YYYY or Month YYYY).
   - **Rule 6(1)(e)**: Maximum Retail Price (MRP) and explicit inclusive of all taxes wording.
   - **Rule 6(1)(n)**: Consumer grievance redressal details (name, postal address, helpline phone, email).
   - **Rule 6(1)(aa)**: Country of origin (mandatory for imported commodities).
   - **Rule 6(1)(f)**: Unit Sale Price (USP in Rs. per g/ml/kg/l/unit).
   - **Rule 6(1)(m)**: Best before / use by date.

3. **Configurable Compliance Engine (`services/rules.py`)**:
   - Database-backed `Rule` model with active flags, severity levels (*Critical*, *Major*, *Minor*), and category filtering (*Food*, *Cosmetics*, *Electronics*, *Imported*, *General*).
   - Evaluator functions registered through decorators returning `PASS`, `FAIL`, `WARNING`, or `NEEDS_REVIEW` with official statutory references and matched excerpts.
   - Evaluates Rule 7 / First Schedule numeral height standards with explicit guidance for manual physical scale verification.

4. **Interactive Verification & Inline Correction**:
   - Inspection detail view displays raw OCR text (collapsible) and an editable table of extracted fields.
   - Officers can correct OCR inaccuracies on curved or low-contrast packaging and trigger immediate compliance re-evaluation.

5. **Official A4 PDF Compliance Report (`services/reports.py`)**:
   - Printable government-formatted A4 report built with ReportLab.
   - Includes Inspection ID, date/time, officer username, product category, specimen photo thumbnail, verified declarations table, rule-by-rule evaluation findings, statutory disclaimer, and signature blocks with two-pass `Page X of Y` footers.

6. **Government / Enterprise UI Aesthetic**:
   - Pure CSS variables on `:root` and `[data-theme="dark"]` for Light and Dark themes.
   - Persistent theme selection via `localStorage` with zero-flash inline script.
   - Accessible data tables, badges, breadcrumbs, drag-and-drop dropzone, and plain loading overlays.
   - Free from AI tropes, neon glows, glassmorphism, or emojis.

7. **Security & User Isolation**:
   - Strict `.env` configuration via `django-environ` with zero fallback for secrets.
   - Regular users/officers access only their own scans; administrators have full oversight.
   - Pre-commit hook blocking `.env` and `db.sqlite3` commits.
   - Strict upload validation (file size, extension whitelist, and Pillow binary verification).

---

## Technology Stack

- **Language & Framework**: Python 3.11+, Django 5.x / 6.x
- **Configuration**: `django-environ` reading strictly from `.env`
- **Database**: SQLite (configured via `DATABASE_PATH`)
- **Computer Vision & OCR**: OpenCV (`opencv-python-headless`), Pillow, and `pytesseract`
- **PDF Generation**: ReportLab
- **Frontend**: Django Templates, Custom CSS (CSS variables), Vanilla JavaScript (No Node build required)

---

## Directory Structure

```text
django project/
├── manage.py
├── requirements.txt
├── .env.example
├── .env (NEVER COMMITTED)
├── .gitignore
├── .pre-commit-config.yaml
├── README.md
├── config/
│   ├── settings.py       # Single point of truth for environment variables
│   ├── urls.py
│   ├── wsgi.py
│   └── asgi.py
├── apps/
│   ├── accounts/         # User registration, authentication, password management
│   ├── compliance/       # Rule & RuleResult models, seed commands (seed_rules, seed_demo)
│   ├── scans/            # Scan, ScanImage, ExtractedField models, views, forms
│   └── reports/          # ReportLab PDF report download view
├── services/
│   ├── ocr.py            # OpenCV preprocessing pipeline & Tesseract execution
│   ├── extractor.py      # Statutory field regex & heuristic parser
│   ├── rules.py          # Rule evaluator registry & compliance engine
│   └── reports.py        # ReportLab PDF report builder
├── static/
│   ├── css/style.css     # Production Light/Dark CSS variables
│   └── js/app.js         # Theme toggle, drag-and-drop, and loading states
├── templates/
│   ├── base.html
│   ├── partials/         # navbar.html, messages.html, pagination.html
│   ├── accounts/         # login.html, register.html, password_change.html
│   └── scans/            # dashboard.html, scan_list.html, scan_create.html, scan_detail.html
└── tests/
    ├── test_settings_security.py
    ├── test_extractor.py
    ├── test_compliance_rules.py
    ├── test_user_isolation.py
    └── test_upload_validation.py
```

---

## Installation & Setup

### 1. Prerequisites
- Python 3.11+
- Tesseract OCR (Optional for local testing; required for live OCR recognition):
  - **Windows**: Download the Windows installer from [UB-Mannheim/tesseract/wiki](https://github.com/UB-Mannheim/tesseract/wiki).
    Default install path: `C:\Program Files\Tesseract-OCR\tesseract.exe`.
  - **Linux / Ubuntu**: `sudo apt update && sudo apt install -y tesseract-ocr`
  - **macOS**: `brew install tesseract`

### 2. Environment Setup & Dependencies
Clone or open the workspace and install requirements:
```bash
pip install -r requirements.txt
```

### 3. Configuration (`.env`)
Copy the sample environment file to `.env`:
```bash
cp .env.example .env
```
Generate a cryptographically secure `SECRET_KEY` and set it in `.env`:
```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

#### Environment Variables Reference
| Variable | Description | Default / Example |
| :--- | :--- | :--- |
| `SECRET_KEY` | Cryptographic secret key for session and CSRF security. | *Mandatory (No fallback)* |
| `DEBUG` | Enable/disable debug mode. Set `False` in production. | `False` |
| `ALLOWED_HOSTS` | Comma-separated domain names or hostnames. | `localhost,127.0.0.1` |
| `CSRF_TRUSTED_ORIGINS` | Trusted origins for CSRF POST requests. | `http://localhost:8000` |
| `DATABASE_PATH` | Path to the SQLite database file. | `db.sqlite3` |
| `TESSERACT_CMD` | Full path to Tesseract binary (leave empty if on PATH). | `C:\Program Files\Tesseract-OCR\tesseract.exe` |
| `TESSERACT_LANGS` | Tesseract language codes separated by plus sign. | `eng` |
| `OCR_MIN_CONFIDENCE` | Minimum word token confidence percentage threshold. | `45.0` |
| `MAX_UPLOAD_SIZE_MB` | Maximum permitted upload file size in megabytes. | `10` |
| `ALLOWED_IMAGE_TYPES`| Permitted packaging image extensions. | `jpg,jpeg,png,webp` |
| `SESSION_COOKIE_SECURE`| Transmit session cookies only over HTTPS when `DEBUG=False`. | `False` (dev) / `True` (prod) |
| `CSRF_COOKIE_SECURE` | Transmit CSRF cookies only over HTTPS when `DEBUG=False`. | `False` (dev) / `True` (prod) |
| `DJANGO_SUPERUSER_*`| Default superuser credentials used by `seed_demo`. | Defined in `.env` |
| `DEMO_USER_PASSWORD` | Password for the demonstration officer account (`demo_officer`). | Defined in `.env` |

---

## Database Migrations & Seeding

1. **Apply Migrations**:
   ```bash
   python manage.py makemigrations
   python manage.py migrate
   ```

2. **Seed Compliance Rules**:
   Populates statutory rules from Legal Metrology (Packaged Commodities) Rules, 2011:
   ```bash
   python manage.py seed_rules
   ```

3. **Seed Demo Accounts & Realistic Packaging Samples**:
   Creates administrative superuser, demonstration officer (`demo_officer`), and 3 realistic sample commodity scans with rule evaluation data:
   ```bash
   python manage.py seed_demo
   ```

---

## Running the Application

Start the development server:
```bash
python manage.py runserver
```

Access the portal:
- **Compliance Dashboard & Web Portal**: [http://localhost:8000](http://localhost:8000)
- **Django Admin Console**: [http://localhost:8000/admin/](http://localhost:8000/admin/)
- **Default Demo Credentials**:
  - Username: `demo_officer`
  - Password: As configured in `.env` (`DEMO_USER_PASSWORD` e.g. `OfficerDemo2026!`)
  - Superuser Username: As configured in `.env` (`DJANGO_SUPERUSER_USERNAME` e.g. `admin`)

---

## Running the Automated Test Suite

Execute the full suite of unit and integration tests:
```bash
python manage.py test
```

The test suite validates:
- Insecure `SECRET_KEY` rejection and production cookie safety.
- Statutory regex & heuristic field extraction across all Rule 6 declarations.
- Individual compliance rule evaluators (Pass, Fail, Warning, Needs Review).
- User isolation permissions (preventing cross-user scan or report access).
- Multi-image upload validation and malicious/corrupted file rejection.

---

## Pre-commit Hooks & Secret Hygiene

Install and verify git hooks:
```bash
pre-commit install
```
The included pre-commit hook automatically blocks attempts to commit `.env`, `.env.*`, or `db.sqlite3` files.

---

## Known Operational Limitations

1. **Physical Scale and Numeral Font Height (Rule 7)**:
   - Digital camera photographs taken without calibrated metric scale bars cannot ascertain absolute millimeter font heights on specimen packaging. Consequently, `RULE_NUMERAL_HEIGHT` flags `NEEDS REVIEW` with precise First Schedule Table 1 measurement guidance for manual caliper verification.
2. **Curved & Glossy Packaging Reflections**:
   - Highly reflective pouches, foil packets, and cylindrical containers may cause specular glare that degrades OCR character confidence. The application addresses this by providing multi-panel image merging and an editable inline declarations table on the results page to allow inspectors to verify and correct parsed values.
