// Sends the username and password to /api/login, then opens the dashboard
// (or the change password page when the password is still temporary).

const form = document.getElementById("login-form");
const usernameInput = document.getElementById("username");
const passwordInput = document.getElementById("password");
const errorBox = document.getElementById("login-error");
const button = document.getElementById("login-button");
const rememberBox = document.getElementById("remember");

// The username is kept in this browser only, and only when the person ticks the box (a school computer is often
// shared, so it starts unticked). The password is never kept by this page.
const REMEMBER_KEY = "myguro-username";

// savedUsername() -> "abautista", or "" when nothing is saved or the browser blocks storage
function savedUsername() {
  try {
    return localStorage.getItem(REMEMBER_KEY) || "";
  } catch {
    return "";
  }
}

// rememberUsername("abautista") saves it; rememberUsername("") forgets it
function rememberUsername(username) {
  try {
    if (username) localStorage.setItem(REMEMBER_KEY, username);
    else localStorage.removeItem(REMEMBER_KEY);
  } catch {
    // Remembering is only a convenience; never block the login.
  }
}

// A remembered username is filled in and the cursor goes straight to the password.
if (savedUsername()) {
  usernameInput.value = savedUsername();
  rememberBox.checked = true;
  passwordInput.focus();
}

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

// A shared calendar link sends a logged-out person here with ?next=/calendar/2026/09. Only that exact shape is
// followed: anything else in the address could send them to another website after they type their password.
function pageAfterLogin() {
  const next = new URLSearchParams(window.location.search).get("next") || "";
  return /^\/calendar(\/\d+){0,3}$/.test(next) ? next : "/dashboard";
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  errorBox.classList.add("d-none");

  const username = usernameInput.value.trim();
  const password = passwordInput.value;
  if (!username || !password) {
    showError(t("Enter your username and password."));
    return;
  }

  // Take the cursor out of the field, so the phone keyboard closes while the login is checked.
  // (A failed login puts it back in the password box below.)
  if (document.activeElement instanceof HTMLElement) document.activeElement.blur();
  button.disabled = true;
  try {
    const response = await fetch("/api/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password }),
    });
    const data = await response.json();

    if (response.ok) {
      // Only after a successful login, so a mistyped name is never saved. Unticked forgets the old one.
      rememberUsername(rememberBox.checked ? username : "");
      // A temporary password isn't worth saving: it is replaced right away on the change password page.
      if (!data.must_change_password) await offerToSavePassword(username, password);
      window.location.href = data.must_change_password ? "/change-password" : pageAfterLogin();
      return;
    }
    // Only clear the password after a failed login: on success the browser
    // reads it from the field to offer "Save password?".
    passwordInput.value = "";
    passwordInput.focus();
    showError(data.error || t("Login failed."));
  } catch {
    showError(t("Cannot reach the server. Check your connection."));
  } finally {
    button.disabled = false;
  }
});
