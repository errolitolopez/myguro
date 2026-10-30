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
    showError("forgot-error", t("Enter your username and your recovery code."));
    return;
  }
  if (newInput.value.length < MIN_PASSWORD_LENGTH) {
    showError("forgot-error", t("New password must be at least {min} characters.", { min: MIN_PASSWORD_LENGTH }));
    return;
  }
  if (newInput.value !== confirmInput.value) {
    showError("forgot-error", t("The two new passwords don't match."));
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
      showError("forgot-error", data.error || t("Could not change the password."));
      return;
    }
    form.classList.add("d-none");
    document.getElementById("forgot-intro").classList.add("d-none");
    document.getElementById("forgot-done").classList.remove("d-none");
    document.getElementById("forgot-done-text").textContent = data.uses_left > 0
      ? (data.uses_left === 1
        ? t("Your password was changed. Your recovery code can be used 1 more time.")
        : t("Your password was changed. Your recovery code can be used {count} more times.", { count: data.uses_left }))
      : t("Your password was changed. Your recovery code is used up now: log in and make a new one.");
    confetti();
  } catch {
    showError("forgot-error", t("Cannot reach the server. Check your connection."));
  } finally {
    stopLoading();
  }
});
