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

// "2026-10-10 07:17:40" (UTC, from SQLite) -> "Oct 10, 3:17 PM" in the viewer's time zone
function formatDateTime(utcText) {
  return new Date(utcText.replace(" ", "T") + "Z").toLocaleString(undefined, {
    month: "short", day: "numeric", hour: "numeric", minute: "2-digit",
  });
}

// durationText("2026-10-10 07:00:00", "2026-10-10 07:27:10") -> "27 min"; 65 minutes -> "1 h 5 min"
function durationText(startUtc, endUtc) {
  const minutes = Math.round((new Date(endUtc.replace(" ", "T") + "Z") - new Date(startUtc.replace(" ", "T") + "Z")) / 60000);
  if (minutes < 1) return "less than 1 min";
  return minutes < 60 ? `${minutes} min` : `${Math.floor(minutes / 60)} h ${minutes % 60} min`;
}

// The teacher's earlier subjects, fetched once per page: ["Math", "Science"]
let subjectsPromise = null;
function loadSubjects() {
  if (!subjectsPromise) {
    subjectsPromise = apiFetch("/api/subjects")
      .then((response) => (response && response.ok ? response.json() : { subjects: [] }))
      .then((data) => data.subjects)
      .catch(() => []);
  }
  return subjectsPromise;
}

// subjectPicker(input) puts a dropdown of the teacher's earlier subjects before a text box. Choosing
// "Other..." shows the box so a new subject can be typed. The box stays the one place the page reads
// the subject from; after setting input.value in code, call picker.sync() so the dropdown follows.
function subjectPicker(input) {
  const OTHER = "__other";
  const select = document.createElement("select");
  select.className = "form-select";
  select.setAttribute("aria-label", "Subject");
  input.before(select);

  const fill = (subjects) => {
    select.replaceChildren(
      new Option("Choose a subject", ""),
      ...subjects.map((subject) => new Option(subject, subject)),
      new Option("Other...", OTHER),
    );
    sync();
  };

  // Show the dropdown choice that matches what is in the box
  function sync() {
    const value = input.value.trim().toLowerCase();
    const match = [...select.options].find((option) => option.value && option.value !== OTHER
      && option.value.toLowerCase() === value);
    select.value = match ? match.value : value ? OTHER : "";
    showBox(select.value === OTHER);
  }

  // The box sits under the dropdown, with a gap between them only while it is shown
  function showBox(visible) {
    input.classList.toggle("d-none", !visible);
    select.classList.toggle("mb-2", visible);
  }

  select.addEventListener("change", () => {
    if (select.value === OTHER) {
      // An empty box would make sync() pick "Choose a subject" again, so show the box here instead
      input.value = "";
      showBox(true);
      input.focus();
    } else {
      input.value = select.value;
      sync();
    }
    // The page reacts to typing in the box (unsaved changes, saving a locked sheet), so tell it
    input.dispatchEvent(new Event("input", { bubbles: true }));
    input.dispatchEvent(new Event("change", { bubbles: true }));
  });

  fill([]);
  loadSubjects().then(fill);
  return { sync };
}

// plural(1, "student") -> "1 student", plural(2, "activity", "activities") -> "2 activities"
function plural(count, one, many = `${one}s`) {
  return `${count} ${count === 1 ? one : many}`;
}

// fetch() that sends the user to the login page when the session has ended,
// or to the change password page while they still have a temporary password.
// Returns null in those cases, so callers can simply stop: if (!response) return;
// --- Grouping by subject (Activities page and My activities) ---

// "Science", " science ", "SCIENCE" are one subject.
function subjectKey(subject) {
  return (subject || "").trim().replace(/\s+/g, " ").toLowerCase();
}

// Items grouped by subject: [{key, label, items}], A to Z, "No subject" last. The label is the
// way the subject was first written.
function groupBySubject(items) {
  const groups = new Map();
  for (const item of items) {
    const key = subjectKey(item.subject);
    if (!groups.has(key)) {
      groups.set(key, { key, label: key ? item.subject.trim().replace(/\s+/g, " ") : "No subject", items: [] });
    }
    groups.get(key).items.push(item);
  }
  return [...groups.values()].sort((a, b) =>
    (a.key === "") - (b.key === "") || a.label.localeCompare(b.label));
}

// The subject in the address (?subject=science), or null when the page shows the list of subjects.
// An empty one (?subject=) is the "No subject" group.
function chosenSubject() {
  const value = new URLSearchParams(window.location.search).get("subject");
  return value === null ? null : subjectKey(value);
}

// The list of subjects: one row each with how many items it has. Tapping a row opens this same
// page for that subject (?subject=...). extraQuery keeps other choices, e.g. "&show=done".
//   subjectListElement(groupBySubject(items), "") -> <div class="list-group">...</div>
function subjectListElement(groups, extraQuery = "") {
  const box = document.createElement("div");
  box.className = "list-group";
  groups.forEach((group) => {
    const row = document.createElement("a");
    row.href = `?subject=${encodeURIComponent(group.key)}${extraQuery}`;
    row.className = "list-group-item list-group-item-action d-flex justify-content-between align-items-center gap-2";
    const name = document.createElement("span");
    name.className = "fw-semibold";
    name.textContent = group.label;
    const right = document.createElement("span");
    right.className = "text-body-secondary text-nowrap";
    right.textContent = `${group.items.length} `;
    const arrow = document.createElement("i");
    arrow.className = "bi bi-chevron-right";
    arrow.setAttribute("aria-hidden", "true");
    right.append(arrow);
    row.append(name, right);
    box.append(row);
  });
  return box;
}

// The top of a subject's page: a link back to all subjects, then the subject's name.
//   subjectHeaderElement("Science", "") -> "‹ All subjects" + "Science"
function subjectHeaderElement(label, extraQuery = "") {
  const header = document.createElement("div");
  header.className = "mb-2";
  const back = document.createElement("a");
  back.href = extraQuery ? `?${extraQuery.slice(1)}` : window.location.pathname;
  back.className = "small bi bi-chevron-left text-decoration-none";
  back.textContent = "All subjects";
  const title = document.createElement("h2");
  title.className = "h5 mt-1 mb-0";
  title.textContent = label;
  header.append(back, title);
  return header;
}

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

// Marks a button as busy while its request runs: disabled, with a spinner in front of the label.
// Returns a function that puts the button back, or null when the button is already busy, so a
// double click or a repeated Enter sends only one request:
//   const stopLoading = startLoading(button);
//   if (!stopLoading) return;
//   try { ... } finally { stopLoading(); }
const busyButtons = new WeakSet();

function startLoading(button) {
  if (busyButtons.has(button)) return null;
  busyButtons.add(button);
  const spinner = document.createElement("span");
  spinner.className = "spinner-border spinner-border-sm me-1";
  spinner.setAttribute("aria-hidden", "true");
  button.prepend(spinner);
  button.disabled = true;
  return () => {
    spinner.remove();
    button.disabled = false;
    busyButtons.delete(button);
  };
}

const logoutButton = document.getElementById("logout-button");
if (logoutButton) {
  logoutButton.addEventListener("click", async () => {
    await fetch("/api/logout", { method: "POST" });
    window.location.href = "/login";
  });
}

// The school year picker in the account menu: remember the choice, then reload so every list
// shows that year.
const yearSelect = document.getElementById("year-select");
if (yearSelect) {
  yearSelect.addEventListener("change", async () => {
    yearSelect.disabled = true;
    try {
      const response = await apiFetch("/api/school-year", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ id: Number(yearSelect.value) }),
      });
      if (!response) return;
    } catch {
      yearSelect.disabled = false;
      return;
    }
    // A page about one class or one assignment may not exist in the other year: go to its list.
    window.location.href = window.location.pathname.split("/").length > 2 ? "/" : window.location.pathname;
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
      `MyGuro login\n` +
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

// Download students' login details as an Excel file. The server makes it from the list sent here,
// because the passwords are only known right after they are made. Each student has name, username,
// password, grade and section. The button shows a spinner meanwhile; a problem goes in the error box.
// downloadLoginDetails([{ name: "Cruz, Ana", username: "acruz", password: "x7", grade: "Grade 7", section: "Rizal" }],
//   button, "import-error")
async function downloadLoginDetails(students, button, errorId) {
  const stopLoading = startLoading(button);
  if (!stopLoading) return;
  hideError(errorId);
  try {
    const response = await apiFetch("/api/users/login-details", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ students }),
    });
    if (!response) return;
    if (!response.ok) {
      showError(errorId, (await response.json()).error || "Could not make the file.");
      return;
    }
    const link = document.createElement("a");
    link.href = URL.createObjectURL(await response.blob());
    link.download = `MyGuro login details ${new Date().toISOString().slice(0, 10)}.xlsx`;
    document.body.append(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(link.href);
  } catch {
    showError(errorId, "Cannot reach the server. Check your connection.");
  } finally {
    stopLoading();
  }
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

// An assignment is Not started, Open or Closed. What the teacher's button does next, and how the status looks.
// STATUS_ACTIONS.open -> { next: "closed", label: "Close", ... }
const STATUS_ACTIONS = {
  not_started: { next: "open", label: "Open", className: "btn-success", icon: "bi-door-open" },
  open: { next: "closed", label: "Close", className: "btn-outline-secondary", icon: "bi-door-closed" },
  closed: { next: "open", label: "Re-open", className: "btn-primary", icon: "bi-arrow-counterclockwise" },
};
const STATUS_BADGES = {
  not_started: ["text-bg-secondary", "Not started"],
  open: ["text-bg-success", "Open"],
  closed: ["text-bg-dark", "Closed"],
};

// Open, close or re-open an assignment. A close asks first: it submits everyone's unfinished work.
// putStatus(12, "closed", "Grade 9 - Rizal") -> the response, or null when cancelled or signed out
async function putStatus(assignmentId, next, name) {
  if (next === "closed" && !window.confirm(
    `Close this activity for ${name}? Work not submitted yet is submitted as it is, and students can only ` +
    "read the questions. You can re-open it later.")) return null;
  return apiFetch(`/api/assignments/${assignmentId}/status`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ status: next }),
  });
}
