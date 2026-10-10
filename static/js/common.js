// Helpers shared by the logged-in pages.

function showError(elementId, message) {
  const box = document.getElementById(elementId);
  box.textContent = message;
  box.classList.remove("d-none");
}

function hideError(elementId) {
  document.getElementById(elementId).classList.add("d-none");
}

// fetch() that sends the user to the login page when the session has ended,
// or to the change password page while they still have a temporary password.
// Returns null in those cases, so callers can simply stop: if (!response) return;
async function apiFetch(url, options) {
  const response = await fetch(url, options);
  if (response.status === 401) {
    window.location.href = "/login";
    return null;
  }
  if (response.status === 403) {
    const data = await response.clone().json().catch(() => ({}));
    if (data.must_change_password) {
      window.location.href = "/change-password";
      return null;
    }
  }
  return response;
}

const logoutButton = document.getElementById("logout-button");
if (logoutButton) {
  logoutButton.addEventListener("click", async () => {
    await fetch("/api/logout", { method: "POST" });
    window.location.href = "/login";
  });
}
