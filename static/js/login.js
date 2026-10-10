// Sends the username and password to /api/login, then opens the dashboard
// (or the change password page when the password is still temporary).

const form = document.getElementById("login-form");
const usernameInput = document.getElementById("username");
const passwordInput = document.getElementById("password");
const errorBox = document.getElementById("login-error");
const button = document.getElementById("login-button");

function showError(message) {
  errorBox.textContent = message;
  errorBox.classList.remove("d-none");
}

// Asks the browser to show its "Save password?" prompt (Chrome, Edge). Other browsers,
// or pages not on https/localhost, skip this and rely on their own detection.
async function offerToSavePassword(username, password) {
  if (!window.PasswordCredential) return;
  try {
    await navigator.credentials.store(new PasswordCredential({ id: username, password }));
  } catch {
    // Saving the password is only a convenience; never block the login.
  }
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  errorBox.classList.add("d-none");

  const username = usernameInput.value.trim();
  const password = passwordInput.value;
  if (!username || !password) {
    showError("Enter your username and password.");
    return;
  }

  button.disabled = true;
  try {
    const response = await fetch("/api/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password }),
    });
    const data = await response.json();

    if (response.ok) {
      // A temporary password isn't worth saving: it is replaced right away on the change password page.
      if (!data.must_change_password) await offerToSavePassword(username, password);
      window.location.href = data.must_change_password ? "/change-password" : "/dashboard";
      return;
    }
    // Only clear the password after a failed login: on success the browser
    // reads it from the field to offer "Save password?".
    passwordInput.value = "";
    passwordInput.focus();
    showError(data.error || "Login failed.");
  } catch {
    showError("Cannot reach the server. Check your connection.");
  } finally {
    button.disabled = false;
  }
});
