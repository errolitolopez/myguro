// Saves a new password, then opens the dashboard.

const form = document.getElementById("password-form");
const currentInput = document.getElementById("current-password");
const newInput = document.getElementById("new-password");
const confirmInput = document.getElementById("confirm-password");
const errorBox = document.getElementById("password-error");
const button = document.getElementById("password-button");

function showError(message) {
  errorBox.textContent = message;
  errorBox.classList.remove("d-none");
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  errorBox.classList.add("d-none");

  if (!currentInput.value) {
    showError("Enter your current password.");
    return;
  }
  if (newInput.value.length < 8) {
    showError("New password must be at least 8 characters.");
    return;
  }
  if (newInput.value !== confirmInput.value) {
    showError("The two new passwords don't match.");
    return;
  }

  button.disabled = true;
  try {
    const response = await fetch("/api/change-password", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        current_password: currentInput.value,
        new_password: newInput.value,
      }),
    });
    if (response.status === 401) {
      window.location.href = "/login";
      return;
    }
    if (response.ok) {
      window.location.href = "/dashboard";
      return;
    }
    const data = await response.json();
    showError(data.error || "Could not save the password.");
  } catch {
    showError("Cannot reach the server. Check your connection.");
  } finally {
    button.disabled = false;
  }
});

document.getElementById("logout-button").addEventListener("click", async () => {
  await fetch("/api/logout", { method: "POST" });
  window.location.href = "/login";
});
