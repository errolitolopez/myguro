// A teacher's own settings on the Settings page (Teaching): shuffled questions and choices. Each switch is saved
// as soon as it is changed, in the database, so it follows the teacher to any device.

const shuffleSwitches = {
  shuffle_questions: document.getElementById("shuffle-questions"),
  shuffle_choices: document.getElementById("shuffle-choices"),
};

// showTeacherSettings({shuffle_questions: true, ...}) -> sets each switch and lets the teacher use it
function showTeacherSettings(settings) {
  for (const [key, input] of Object.entries(shuffleSwitches)) {
    input.checked = settings[key];
    input.disabled = false;
  }
}

async function loadTeacherSettings() {
  try {
    const response = await apiFetch("/api/teacher-settings");
    if (!response) return;
    const data = await response.json();
    if (!response.ok) {
      showError("teacher-settings-error", data.error || t("Could not load your settings."));
      return;
    }
    hideError("teacher-settings-error");
    showTeacherSettings(data.settings);
  } catch {
    showError("teacher-settings-error", t("Cannot reach the server. Check your connection."));
  }
}

// Saves one switch. The switches stay off-limits while it runs, and show what is really saved afterwards.
async function saveTeacherSetting(key, value) {
  const inputs = Object.values(shuffleSwitches);
  inputs.forEach((input) => (input.disabled = true));
  try {
    const response = await apiFetch("/api/teacher-settings", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ [key]: value }),
    });
    if (!response) return;
    const data = await response.json();
    if (!response.ok) {
      showError("teacher-settings-error", data.error || t("Could not save."));
      await loadTeacherSettings();
      return;
    }
    hideError("teacher-settings-error");
    showTeacherSettings(data.settings);
  } catch {
    showError("teacher-settings-error", t("Cannot reach the server. Check your connection."));
    await loadTeacherSettings();
  }
}

for (const [key, input] of Object.entries(shuffleSwitches)) {
  input.addEventListener("change", () => saveTeacherSetting(key, input.checked));
}

loadTeacherSettings();
