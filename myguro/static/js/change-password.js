// Saves a new password, then opens the dashboard.

const form = document.getElementById("password-form");
const currentInput = document.getElementById("current-password");
const newInput = document.getElementById("new-password");
const confirmInput = document.getElementById("confirm-password");
const usernameInput = document.querySelector('input[name="username"]');
const errorBox = document.getElementById("password-error");
const button = document.getElementById("password-button");

function showError(message) {
  errorBox.textContent = message;
  errorBox.classList.remove("d-none");
}

// Asks the browser to save (or update) the password for this username. See login.js.
async function offerToSavePassword(username, password) {
  if (!window.PasswordCredential) return;
  try {
    await navigator.credentials.store(new PasswordCredential({ id: username, password }));
  } catch {
    // Saving the password is only a convenience; never block going to the dashboard.
  }
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  errorBox.classList.add("d-none");

  if (!currentInput.value) {
    showError(t("Enter your current password."));
    return;
  }
  if (newInput.value.length < 6) {
    showError(t("New password must be at least {min} characters.", { min: 6 }));
    return;
  }
  if (newInput.value !== confirmInput.value) {
    showError(t("The two new passwords don't match."));
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
      await offerToSavePassword(usernameInput.value, newInput.value);
      // The first password change is followed by making a recovery code.
      window.location.href = form.dataset.firstTime === "1" ? "/recovery-code?welcome=1" : "/dashboard";
      return;
    }
    const data = await response.json();
    showError(data.error || t("Could not save the password."));
  } catch {
    showError(t("Cannot reach the server. Check your connection."));
  } finally {
    button.disabled = false;
  }
});

document.getElementById("logout-button").addEventListener("click", async () => {
  await fetch("/api/logout", { method: "POST" });
  window.location.href = "/login";
});
