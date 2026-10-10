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
      window.location.href = data.must_change_password ? "/change-password" : "/dashboard";
      return;
    }
    showError(data.error || "Login failed.");
  } catch {
    showError("Cannot reach the server. Check your connection.");
  } finally {
    button.disabled = false;
    passwordInput.value = "";
    passwordInput.focus();
  }
});
