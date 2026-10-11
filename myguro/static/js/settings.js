// Admin settings: each switch is saved as soon as it is changed.

const gradesSwitch = document.getElementById("grades-high-to-low");
const gradeList = document.getElementById("grade-list");
const status = document.getElementById("settings-status");

function showSettings(settings) {
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

loadSettings();
