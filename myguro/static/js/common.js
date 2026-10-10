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

// Class name from the grade select and section input: "Grade 6 - Rizal" or "Grade 6"
function joinClassName(grade, section) {
  return [grade, section.trim()].filter(Boolean).join(" - ");
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

// "Rian Joshua" + "Altamerano" -> "raltamerano" (first letter of the first name + the last name).
function suggestUsername(firstName, lastName) {
  const plain = (text) => text
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "") // ñ -> n, é -> e
    .toLowerCase()
    .replace(/[^a-z0-9]/g, "");
  const first = plain(firstName);
  return ((first.slice(0, 1) + plain(lastName)) || first).slice(0, 30);
}

// The name boxes of templates/_person_name_fields.html (ids <prefix>-last, -first, -middle).
function personNameValues(prefix) {
  return {
    last_name: document.getElementById(`${prefix}-last`).value.trim(),
    first_name: document.getElementById(`${prefix}-first`).value.trim(),
    middle_initial: document.getElementById(`${prefix}-middle`).value.trim(),
  };
}

function setPersonName(prefix, person) {
  document.getElementById(`${prefix}-last`).value = person.last_name;
  document.getElementById(`${prefix}-first`).value = person.first_name;
  document.getElementById(`${prefix}-middle`).value = person.middle_initial;
}

// The message for a missing last or first name, or "" when both are there.
function personNameProblem(values) {
  if (!values.last_name) return "Last name is required.";
  if (!values.first_name) return "First name is required.";
  return "";
}

// The login details popup (templates/_login_details_modal.html): shows a new account's
// or a reset password once, so the teacher/admin can give it to the person.
function showLoginDetails(user, password) {
  document.getElementById("details-name").textContent = user.name;
  document.getElementById("details-username").textContent = user.username;
  document.getElementById("details-password").textContent = password;
  // A new student is disabled: they cannot log in until the admin enables the account.
  document.getElementById("details-disabled").classList.toggle("d-none", user.active !== false);
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

// Formatted text (bold, italic, lists) of a section. The server already cleans it; this keeps
// only the same few tags again before it goes into the page.
const RICH_TAGS = new Set(["P", "DIV", "BR", "B", "STRONG", "I", "EM", "U", "UL", "OL", "LI"]);

function richTextNodes(html) {
  const copy = (node) => {
    if (node.nodeType === Node.TEXT_NODE) return [document.createTextNode(node.textContent)];
    if (node.nodeType !== Node.ELEMENT_NODE) return [];
    const inner = Array.from(node.childNodes).flatMap(copy);
    if (!RICH_TAGS.has(node.tagName)) {
      return ["SCRIPT", "STYLE", "TEMPLATE", "IFRAME", "OBJECT", "NOSCRIPT"].includes(node.tagName) ? [] : inner;
    }
    const clean = document.createElement(node.tagName.toLowerCase());
    clean.append(...inner);
    return [clean];
  };
  const parsed = new DOMParser().parseFromString(html, "text/html");
  return Array.from(parsed.body.childNodes).flatMap(copy);
}

// Show a section's description in an element: formatted when the section is "rich", else as typed.
function showDescription(element, section) {
  if (section.description_format === "rich") {
    element.classList.remove("preserve-lines");
    element.replaceChildren(...richTextNodes(section.description));
  } else {
    element.textContent = section.description;
  }
}
