// Forgot password: username + recovery code + a new password. Each use takes one of the code's uses.

const form = document.getElementById("forgot-form");
const usernameInput = document.getElementById("forgot-username");
const codeInput = document.getElementById("forgot-code");
const newInput = document.getElementById("forgot-new");
const confirmInput = document.getElementById("forgot-confirm");
const button = document.getElementById("forgot-button");
const MIN_PASSWORD_LENGTH = 6;

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  hideError("forgot-error");
  if (!usernameInput.value.trim() || !codeInput.value.trim()) {
    showError("forgot-error", "Enter your username and your recovery code.");
    return;
  }
  if (newInput.value.length < MIN_PASSWORD_LENGTH) {
    showError("forgot-error", `New password must be at least ${MIN_PASSWORD_LENGTH} characters.`);
    return;
  }
  if (newInput.value !== confirmInput.value) {
    showError("forgot-error", "The two new passwords don't match.");
    return;
  }
  const stopLoading = startLoading(button);
  if (!stopLoading) return;
  try {
    // fetch, not apiFetch: a 401 here means a wrong code, not "please log in".
    const response = await fetch("/api/recover", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username: usernameInput.value.trim(), code: codeInput.value, new_password: newInput.value }),
    });
    const data = await response.json();
    if (!response.ok) {
      showError("forgot-error", data.error || "Could not change the password.");
      return;
    }
    form.classList.add("d-none");
    document.getElementById("forgot-intro").classList.add("d-none");
    document.getElementById("forgot-done").classList.remove("d-none");
    document.getElementById("forgot-done-text").textContent = data.uses_left > 0
      ? `Your password was changed. Your recovery code can be used ${plural(data.uses_left, "more time")}.`
      : "Your password was changed. Your recovery code is used up now: log in and make a new one.";
    confetti();
  } catch {
    showError("forgot-error", "Cannot reach the server. Check your connection.");
  } finally {
    stopLoading();
  }
});
