// Make (or remake) your recovery code. The code is shown once, right after it is made.

const statusBox = document.getElementById("recovery-status");
const form = document.getElementById("recovery-form");
const passwordInput = document.getElementById("recovery-password");
const makeButton = document.getElementById("recovery-make");
const resultBox = document.getElementById("recovery-result");
const replaceModal = bootstrap.Modal.getOrCreateInstance(document.getElementById("replace-modal"));
const replaceConfirm = document.getElementById("replace-confirm");
let hasCode = false; // whether the person already has a code (then replacing it needs a confirmation)

// formatDay("2026-10-26 08:00:00") -> "Oct 26, 2026" (UTC from SQLite, shown in the viewer's time)
function formatDay(utcText) {
  return new Date(utcText.replace(" ", "T") + "Z").toLocaleDateString(undefined, {
    month: "short", day: "numeric", year: "numeric",
  });
}

async function loadStatus() {
  hideError("recovery-error");
  try {
    const response = await apiFetch("/api/recovery-code");
    if (!response) return;
    const data = await response.json();
    if (!response.ok) {
      statusBox.replaceChildren();
      showError("recovery-error", data.error || "Could not load your recovery code.");
      return;
    }
    const line = document.createElement("div");
    line.className = "fw-semibold bi " + (data.has_code ? "bi-shield-check" : "bi-shield-exclamation");
    line.textContent = data.has_code
      ? ` You have a recovery code (made ${formatDay(data.created_at)}).`
      : " You don't have a recovery code yet.";
    statusBox.replaceChildren(line);
    hasCode = data.has_code;
    makeButton.textContent = data.has_code ? "Make a new code" : "Make a recovery code";
    document.getElementById("recovery-replace-note").classList.toggle("d-none", !data.has_code);
  } catch {
    statusBox.replaceChildren();
    showError("recovery-error", "Cannot reach the server. Check your connection.");
  }
}

// Makes the code (the password was checked to be filled in). button = the one that shows the spinner.
async function makeCode(button) {
  const stopLoading = startLoading(button);
  if (!stopLoading) return;
  try {
    const response = await apiFetch("/api/recovery-code", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ current_password: passwordInput.value, replace: hasCode }),
    });
    if (!response) return;
    const data = await response.json();
    replaceModal.hide();
    if (!response.ok) {
      showError("recovery-error", data.error || "Could not make the code.");
      return;
    }
    passwordInput.value = "";
    showRecoveryCode(resultBox, data.code, RECOVERY_USERNAME);
    confetti();
    loadStatus();
  } catch {
    replaceModal.hide();
    showError("recovery-error", "Cannot reach the server. Check your connection.");
  } finally {
    stopLoading();
  }
}

form.addEventListener("submit", (event) => {
  event.preventDefault();
  hideError("recovery-error");
  if (!passwordInput.value) {
    showError("recovery-error", "Enter your current password.");
    return;
  }
  // The first code needs no question; replacing one does.
  if (hasCode) replaceModal.show();
  else makeCode(makeButton);
});
replaceConfirm.addEventListener("click", () => makeCode(replaceConfirm));

if (new URLSearchParams(window.location.search).has("welcome")) {
  document.getElementById("welcome").classList.remove("d-none");
}
loadStatus();
