/**
 * Legal Metrology Packaged Commodity Compliance Portal JS
 * Vanilla JavaScript: Theme management, drag & drop image handling,
 * loading overlay during OCR processing, and collapsible panel interactions.
 */

document.addEventListener("DOMContentLoaded", function () {
  initThemeToggle();
  initDragAndDrop();
  initFormSubmissions();
  initCollapsibles();
});

/**
 * Initialize Light/Dark theme toggle with localStorage persistence.
 */
function initThemeToggle() {
  const toggleBtn = document.getElementById("themeToggleBtn");
  if (!toggleBtn) return;

  function updateButtonLabel(theme) {
    toggleBtn.textContent = theme === "dark" ? "Theme: Dark" : "Theme: Light";
  }

  const currentTheme = document.documentElement.getAttribute("data-theme") || "light";
  updateButtonLabel(currentTheme);

  toggleBtn.addEventListener("click", function () {
    const activeTheme = document.documentElement.getAttribute("data-theme") || "light";
    const newTheme = activeTheme === "dark" ? "light" : "dark";

    document.documentElement.setAttribute("data-theme", newTheme);
    localStorage.setItem("theme", newTheme);
    updateButtonLabel(newTheme);
  });
}

/**
 * Multi-file drag & drop file upload with live client-side thumbnail preview.
 */
function initDragAndDrop() {
  const dropzone = document.getElementById("uploadDropzone");
  const fileInput = document.getElementById("id_images");
  const previewGrid = document.getElementById("previewGrid");

  if (!dropzone || !fileInput) return;

  ["dragenter", "dragover"].forEach((eventName) => {
    dropzone.addEventListener(eventName, function (e) {
      e.preventDefault();
      e.stopPropagation();
      dropzone.classList.add("dragover");
    });
  });

  ["dragleave", "drop"].forEach((eventName) => {
    dropzone.addEventListener(eventName, function (e) {
      e.preventDefault();
      e.stopPropagation();
      dropzone.classList.remove("dragover");
    });
  });

  dropzone.addEventListener("drop", function (e) {
    if (e.dataTransfer && e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      fileInput.files = e.dataTransfer.files;
      renderPreviews(fileInput.files);
    }
  });

  fileInput.addEventListener("change", function () {
    renderPreviews(fileInput.files);
  });

  function renderPreviews(files) {
    if (!previewGrid) return;
    previewGrid.innerHTML = "";

    Array.from(files).forEach((file) => {
      if (!file.type.startsWith("image/")) return;

      const reader = new FileReader();
      reader.onload = function (e) {
        const card = document.createElement("div");
        card.className = "preview-thumb-card";

        const img = document.createElement("img");
        img.src = e.target.result;
        img.alt = file.name;

        const nameSpan = document.createElement("div");
        nameSpan.className = "preview-thumb-name";
        nameSpan.textContent = file.name;

        card.appendChild(img);
        card.appendChild(nameSpan);
        previewGrid.appendChild(card);
      };
      reader.readAsDataURL(file);
    });
  }
}

/**
 * Shows accessible loading overlay when submitting scan upload or recalculate forms.
 */
function initFormSubmissions() {
  const uploadForm = document.getElementById("scanUploadForm");
  const loadingOverlay = document.getElementById("loadingOverlay");

  if (uploadForm && loadingOverlay) {
    uploadForm.addEventListener("submit", function (e) {
      // Basic check that files are selected
      const fileInput = document.getElementById("id_images");
      if (fileInput && fileInput.files.length === 0) {
        return; // Allow standard form validation error to show
      }
      loadingOverlay.style.display = "flex";
    });
  }
}

/**
 * Accessible Collapsible Sections (e.g. Raw OCR Text Box).
 */
function initCollapsibles() {
  document.querySelectorAll("[data-collapse-target]").forEach((button) => {
    button.addEventListener("click", function () {
      const targetId = button.getAttribute("data-collapse-target");
      const targetEl = document.getElementById(targetId);
      if (targetEl) {
        const isHidden = targetEl.style.display === "none";
        targetEl.style.display = isHidden ? "block" : "none";
        button.setAttribute("aria-expanded", isHidden ? "true" : "false");
      }
    });
  });
}
