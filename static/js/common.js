// Helpers shared by the logged-in pages.

function showError(elementId, message) {
  const box = document.getElementById(elementId);
  box.textContent = message;
  box.classList.remove("d-none");
}

function hideError(elementId) {
  document.getElementById(elementId).classList.add("d-none");
}

// "Grade 6 - Rizal" + "Science" -> "Grade 6 - Rizal · Science"
function classTitle(item) {
  return item.subject ? `${item.name} · ${item.subject}` : item.name;
}

// "Grade 6 - Rizal", "Grade 7", "Rizal", or "" (irregular / not set)
function gradeSection(student) {
  return [student.grade, student.section].filter(Boolean).join(" - ");
}

// "2026-10-15" -> "Oct 15, 2026". Read as a calendar day, so no time zone can shift it.
function formatDay(isoDate) {
  const [year, month, day] = isoDate.split("-").map(Number);
  return new Date(year, month - 1, day).toLocaleDateString(undefined, {
    month: "short", day: "numeric", year: "numeric",
  });
}

// plural(1, "student") -> "1 student", plural(2, "activity", "activities") -> "2 activities"
function plural(count, one, many = `${one}s`) {
  return `${count} ${count === 1 ? one : many}`;
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

// "Maria Santos" -> "msantos" (first letter of the first name + the last name).
function suggestUsername(name) {
  const words = name
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "") // ñ -> n, é -> e
    .toLowerCase()
    .replace(/[^a-z0-9 ]/g, "")
    .split(" ")
    .filter(Boolean);
  if (words.length === 0) return "";
  if (words.length === 1) return words[0];
  return words[0][0] + words[words.length - 1];
}

// The login details popup (templates/_login_details_modal.html): shows a new account's
// or a reset password once, so the teacher/admin can give it to the person.
function showLoginDetails(user, password) {
  document.getElementById("details-name").textContent = user.name;
  document.getElementById("details-username").textContent = user.username;
  document.getElementById("details-password").textContent = password;
  bootstrap.Modal.getOrCreateInstance(document.getElementById("login-details-modal")).show();
}

const copyDetailsButton = document.getElementById("copy-details-button");
if (copyDetailsButton) {
  copyDetailsButton.addEventListener("click", async () => {
    const text =
      `myguro login\n` +
      `Username: ${document.getElementById("details-username").textContent}\n` +
      `Password: ${document.getElementById("details-password").textContent}`;
    try {
      await navigator.clipboard.writeText(text);
      copyDetailsButton.textContent = "Copied!";
    } catch {
      copyDetailsButton.textContent = "Can't copy";
    }
    setTimeout(() => (copyDetailsButton.textContent = "Copy"), 1500);
  });
}
