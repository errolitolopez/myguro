// Admin settings: each switch is saved as soon as it is changed.

const gradesSwitch = document.getElementById("grades-high-to-low");
const gradeList = document.getElementById("grade-list");
const status = document.getElementById("settings-status");

const supportForm = document.getElementById("support-form");
const supportEnabled = document.getElementById("support-enabled");
const supportUrl = document.getElementById("support-url");
const supportMessage = document.getElementById("support-message");
const supportLabel = document.getElementById("support-label");
const supportGcashNumber = document.getElementById("support-gcash-number");
const supportGcashName = document.getElementById("support-gcash-name");
const supportPopup = document.getElementById("support-popup");
const supportSave = document.getElementById("support-save");
const supportStatus = document.getElementById("support-status");

function showSupport(support) {
  supportEnabled.checked = support.enabled;
  supportUrl.value = support.url;
  supportMessage.value = support.message;
  supportLabel.value = support.label;
  supportGcashNumber.value = support.gcash_display;
  supportGcashName.value = support.gcash_name;
  supportPopup.value = support.popup;
}

supportForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  hideError("support-error");
  const stopLoading = startLoading(supportSave);
  if (!stopLoading) return;
  supportStatus.textContent = "";
  try {
    const response = await apiFetch("/api/settings", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ support: {
        enabled: supportEnabled.checked, url: supportUrl.value, message: supportMessage.value,
        label: supportLabel.value, gcash_number: supportGcashNumber.value, gcash_name: supportGcashName.value,
        popup: supportPopup.value,
      } }),
    });
    if (!response) return;
    const data = await response.json();
    if (!response.ok) {
      showError("support-error", data.error || "Could not save.");
      return;
    }
    showSupport(data.settings.support);
    supportStatus.textContent = "Saved. Shown from the next page you open.";
  } catch {
    showError("support-error", "Cannot reach the server. Check your connection.");
  } finally {
    stopLoading();
  }
});

function showSettings(settings) {
  showSupport(settings.support);
  gradesSwitch.checked = settings.grades_high_to_low;
  gradesSwitch.disabled = false;
  gradeList.replaceChildren(...settings.grades.map((grade, index) => {
    const column = document.createElement("div");
    column.className = "col";
    const row = document.createElement("div");
    row.className = "form-check form-switch";
    const input = document.createElement("input");
    input.type = "checkbox";
    input.role = "switch";
    input.className = "form-check-input";
    input.id = `grade-${index}`;
    input.value = grade.name;
    input.checked = grade.enabled;
    input.addEventListener("change", saveGrades);
    const label = document.createElement("label");
    label.className = "form-check-label";
    label.htmlFor = input.id;
    label.textContent = grade.name;
    row.append(input, label);
    column.append(row);
    return column;
  }));
}

// Sends the change and shows what the server saved (or puts the switches back on an error).
async function save(body) {
  status.textContent = "Saving...";
  const fields = [gradesSwitch, ...gradeList.querySelectorAll("input")];
  fields.forEach((field) => (field.disabled = true));
  try {
    const response = await apiFetch("/api/settings", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    if (!response) return;
    const data = await response.json();
    if (!response.ok) {
      status.textContent = data.error || "Could not save.";
      await loadSettings(false);
      return;
    }
    showSettings(data.settings);
    status.textContent = "Saved";
  } catch {
    status.textContent = "Cannot reach the server.";
    await loadSettings(false);
  } finally {
    fields.forEach((field) => (field.disabled = false));
  }
}

function saveGrades() {
  const off = [...gradeList.querySelectorAll("input")].filter((input) => !input.checked).map((input) => input.value);
  save({ disabled_grades: off });
}

gradesSwitch.addEventListener("change", () => save({ grades_high_to_low: gradesSwitch.checked }));

async function loadSettings(clearStatus = true) {
  try {
    const response = await apiFetch("/api/settings");
    if (!response) return;
    if (!response.ok) {
      showError("settings-error", "Could not load the settings.");
      return;
    }
    hideError("settings-error");
    showSettings((await response.json()).settings);
    if (clearStatus) status.textContent = "";
  } catch {
    showError("settings-error", "Cannot reach the server. Check your connection.");
  }
}

// Lists the tips from tips.js, so the admin can read what teachers and students will see.
function showTips() {
  for (const role of ["teacher", "student"]) {
    const tips = (window.myguroTips && window.myguroTips[role]) || [];
    document.getElementById(`tips-${role}`).replaceChildren(...tips.map((tip) => {
      const item = document.createElement("li");
      item.className = "list-group-item small";
      item.textContent = tip;
      return item;
    }));
  }
}

// The tip box as a teacher sees it, one tip further each click. Closing it only hides the preview.
let previewIndex = 0;
document.getElementById("tip-preview").addEventListener("click", () => {
  const all = window.myguroTips || {};
  const tips = [...(all.teacher || []), ...(all.student || [])];
  if (!tips.length) return;
  const strong = document.createElement("strong");
  strong.textContent = "Tip: ";
  const text = document.createElement("span");
  text.textContent = tips[previewIndex % tips.length];
  previewIndex += 1;
  const close = document.createElement("button");
  close.type = "button";
  close.className = "btn-close";
  close.setAttribute("aria-label", "Close tip");
  const box = document.createElement("div");
  box.className = "alert alert-info alert-dismissible mb-0 small";
  box.setAttribute("role", "status");
  box.append(strong, text, close);
  close.addEventListener("click", () => box.remove());
  document.getElementById("tip-preview-box").replaceChildren(box);
});

showTips();
loadSettings();
