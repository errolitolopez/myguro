// One class (teacher only): edit its name/subject, add students from the school's
// student list (the admin makes the accounts), remove students from the class.

const classId = document.querySelector("main").dataset.classId;
let students = []; // students in this class; the search filters them here
let selected = null; // the student open in the student popup

const list = document.getElementById("student-list");
const searchInput = document.getElementById("search");

// --- Class name and subject ----------------------------------------------------

const classModalElement = document.getElementById("class-modal");
const classModal = bootstrap.Modal.getOrCreateInstance(classModalElement);
const classForm = document.getElementById("class-form");
const classNameInput = document.getElementById("class-name");
const classSubjectInput = document.getElementById("class-subject");
const classSaveButton = document.getElementById("class-save-button");
let currentClass = null;

function showClass(item) {
  currentClass = item;
  document.title = `${classTitle(item)} · myguro`;
  document.getElementById("class-name-heading").textContent = item.name;
  document.getElementById("class-subject-heading").textContent = item.subject;
}

classModalElement.addEventListener("show.bs.modal", () => {
  document.getElementById("class-modal-title").textContent = "Edit class";
  classNameInput.value = currentClass ? currentClass.name : "";
  classSubjectInput.value = currentClass ? currentClass.subject : "";
  hideError("class-form-error");
});
classModalElement.addEventListener("shown.bs.modal", () => classNameInput.focus());

classForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  hideError("class-form-error");
  const name = classNameInput.value.trim();
  if (!name) {
    showError("class-form-error", "Class name is required.");
    return;
  }
  classSaveButton.disabled = true;
  try {
    const response = await apiFetch(`/api/classes/${classId}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name, subject: classSubjectInput.value.trim() }),
    });
    if (!response) return;
    const data = await response.json();
    if (!response.ok) {
      showError("class-form-error", data.error || "Could not save the class.");
      return;
    }
    showClass(data.class);
    classModal.hide();
  } catch {
    showError("class-form-error", "Cannot reach the server. Check your connection.");
  } finally {
    classSaveButton.disabled = false;
  }
});

// "jdelacruz · Grade 6 - Rizal" (only the username in monospace)
function studentDetails(student) {
  const details = document.createElement("div");
  details.className = "small text-body-secondary";
  const username = document.createElement("span");
  username.className = "font-monospace";
  username.textContent = student.username;
  const place = gradeSection(student);
  details.append(username, place ? ` · ${place}` : "");
  return details;
}

// --- Student list --------------------------------------------------------------

// One row: name and username on the left, status on the right. Tapping it opens the edit popup.
// textContent is used (not innerHTML) so names can't inject HTML.
function studentItem(student) {
  const row = document.createElement("button");
  row.type = "button";
  row.className =
    "list-group-item list-group-item-action d-flex justify-content-between align-items-center";

  const left = document.createElement("div");
  const name = document.createElement("div");
  name.textContent = student.name;
  left.append(name, studentDetails(student));
  row.append(left);

  if (!student.active) {
    const badge = document.createElement("span");
    badge.className = "badge text-bg-secondary";
    badge.textContent = "Deactivated";
    row.append(badge);
  } else if (student.must_change_password) {
    const badge = document.createElement("span");
    badge.className = "badge text-bg-warning";
    badge.textContent = "Not logged in yet";
    badge.title = "Still using the temporary password";
    row.append(badge);
  }

  row.addEventListener("click", () => openStudent(student));
  return row;
}

function messageItem(text) {
  const div = document.createElement("div");
  div.className = "list-group-item text-body-secondary";
  div.textContent = text;
  return div;
}

function render() {
  const query = searchInput.value.trim().toLowerCase();
  const shown = students.filter(
    (student) =>
      student.name.toLowerCase().includes(query) ||
      student.username.includes(query) ||
      student.section.toLowerCase().includes(query),
  );

  if (students.length === 0) {
    list.replaceChildren(messageItem("No students yet. Tap + Add students to pick them from the school list."));
  } else if (shown.length === 0) {
    list.replaceChildren(messageItem("No student matches your search."));
  } else {
    list.replaceChildren(...shown.map(studentItem));
  }

  document.getElementById("student-summary").textContent = query
    ? `${shown.length} found`
    : plural(students.length, "student");
}

async function loadClass() {
  try {
    const response = await apiFetch(`/api/classes/${classId}`);
    if (!response) return;
    if (response.status === 404) {
      window.location.href = "/classes";
      return;
    }
    if (!response.ok) {
      showError("class-error", "Could not load the class.");
      return;
    }
    hideError("class-error");
    const data = await response.json();
    showClass(data.class);
    students = data.students;
    render();
  } catch {
    showError("class-error", "Cannot reach the server. Check your connection.");
  }
}

searchInput.addEventListener("input", render);

// --- Add students --------------------------------------------------------------

const addModalElement = document.getElementById("add-student-modal");
const studentSearch = document.getElementById("student-search");
const results = document.getElementById("search-results");
let searchNumber = 0; // only the newest search updates the results (typing fast sends several)

// One search result: name and username, with an Add button (or "In class").
function resultItem(student) {
  const row = document.createElement("div");
  row.className = "list-group-item d-flex justify-content-between align-items-center gap-2";

  const left = document.createElement("div");
  const name = document.createElement("div");
  name.textContent = student.name;
  left.append(name, studentDetails(student));

  const button = document.createElement("button");
  button.type = "button";
  if (student.in_class) {
    button.className = "btn btn-sm btn-outline-secondary";
    button.textContent = "In class";
    button.disabled = true;
  } else {
    button.className = "btn btn-sm btn-success";
    button.textContent = "Add";
    button.addEventListener("click", () => addStudent(student, button));
  }

  row.append(left, button);
  return row;
}

const gradeFilter = document.getElementById("grade-filter");
const sectionFilter = document.getElementById("section-filter");
const addAllButton = document.getElementById("add-all-button");
let sections = []; // grade + section pairs that exist, for the section dropdown
let addable = []; // search results not in the class yet (for "Add all")

// Section dropdown: the sections of the chosen grade (or of all grades), plus "No section".
function fillSectionFilter() {
  const chosen = sectionFilter.value;
  const names = [...new Set(
    sections
      .filter((item) => item.section && (!gradeFilter.value || item.grade === gradeFilter.value))
      .map((item) => item.section),
  )].sort((a, b) => a.localeCompare(b));

  const options = [new Option("All sections", "*")];
  for (const name of names) options.push(new Option(name, name));
  options.push(new Option("No section", ""));
  sectionFilter.replaceChildren(...options);
  sectionFilter.value = [...sectionFilter.options].some((o) => o.value === chosen) ? chosen : "*";
}

async function searchStudents() {
  const thisSearch = ++searchNumber;
  const params = new URLSearchParams({ q: studentSearch.value.trim() });
  if (gradeFilter.value) params.set("grade", gradeFilter.value);
  if (sectionFilter.value !== "*") params.set("section", sectionFilter.value);
  try {
    const response = await apiFetch(`/api/classes/${classId}/student-search?${params}`);
    if (!response || thisSearch !== searchNumber) return;
    if (!response.ok) {
      showError("add-student-error", "Could not search the students.");
      return;
    }
    hideError("add-student-error");
    const data = await response.json();
    sections = data.sections;
    fillSectionFilter();

    const filtered = studentSearch.value.trim() || gradeFilter.value || sectionFilter.value !== "*";
    if (data.students.length === 0) {
      results.replaceChildren(messageItem(
        filtered ? "No student matches." : "There are no student accounts yet.",
      ));
    } else {
      results.replaceChildren(...data.students.map(resultItem));
    }

    addable = data.students.filter((student) => !student.in_class);
    document.getElementById("result-summary").textContent = data.students.length
      ? `${data.students.length}${data.more ? "+" : ""} shown · ${addable.length} not in class`
      : "";
    addAllButton.textContent = `Add all ${addable.length}`;
    addAllButton.classList.toggle("d-none", addable.length < 2);
  } catch {
    showError("add-student-error", "Cannot reach the server. Check your connection.");
  }
}

// Sends students to add. Returns true when it worked.
async function sendAdd(studentIds) {
  hideError("add-student-error");
  try {
    const response = await apiFetch(`/api/classes/${classId}/students`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ student_ids: studentIds }),
    });
    if (!response) return false;
    if (!response.ok) {
      const data = await response.json();
      showError("add-student-error", data.error || "Could not add the students.");
      return false;
    }
    loadClass();
    return true;
  } catch {
    showError("add-student-error", "Cannot reach the server. Check your connection.");
    return false;
  }
}

// Adds one student; the popup stays open so several can be added in a row.
async function addStudent(student, button) {
  button.disabled = true;
  if (await sendAdd([student.id])) {
    button.className = "btn btn-sm btn-outline-secondary";
    button.textContent = "Added";
    addable = addable.filter((item) => item.id !== student.id);
    addAllButton.textContent = `Add all ${addable.length}`;
    addAllButton.classList.toggle("d-none", addable.length < 2);
  } else {
    button.disabled = false;
  }
}

// Adds everyone shown who isn't in the class yet, e.g. a whole section.
addAllButton.addEventListener("click", async () => {
  addAllButton.disabled = true;
  if (await sendAdd(addable.map((student) => student.id))) await searchStudents();
  addAllButton.disabled = false;
});

// Search after a short pause in typing; filters search right away.
let searchTimer = null;
studentSearch.addEventListener("input", () => {
  clearTimeout(searchTimer);
  searchTimer = setTimeout(searchStudents, 250);
});
gradeFilter.addEventListener("change", () => {
  fillSectionFilter();
  searchStudents();
});
sectionFilter.addEventListener("change", searchStudents);

addModalElement.addEventListener("show.bs.modal", () => {
  studentSearch.value = "";
  gradeFilter.value = "";
  sectionFilter.value = "*";
  hideError("add-student-error");
  results.replaceChildren(messageItem("Loading..."));
  searchStudents();
});
addModalElement.addEventListener("shown.bs.modal", () => studentSearch.focus());

// --- A student in this class -----------------------------------------------------

const studentModal = bootstrap.Modal.getOrCreateInstance(document.getElementById("student-modal"));
const removeButtons = document.getElementById("confirm-box");
const confirmRemove = document.getElementById("confirm-remove");

function openStudent(student) {
  selected = student;
  document.getElementById("student-modal-title").textContent = student.name;
  document.getElementById("student-username").textContent = student.username;
  document.getElementById("student-grade-section").textContent =
    gradeSection(student) || "No grade or section (irregular)";
  removeButtons.classList.remove("d-none");
  confirmRemove.classList.add("d-none");
  hideError("student-error");
  studentModal.show();
}

document.getElementById("remove-button").addEventListener("click", () => {
  document.getElementById("confirm-text").textContent =
    `Remove ${selected.name} from this class? Their account is kept.`;
  removeButtons.classList.add("d-none");
  confirmRemove.classList.remove("d-none");
});

document.getElementById("confirm-no").addEventListener("click", () => {
  removeButtons.classList.remove("d-none");
  confirmRemove.classList.add("d-none");
});

document.getElementById("confirm-yes").addEventListener("click", async (event) => {
  event.target.disabled = true;
  hideError("student-error");
  try {
    const response = await apiFetch(`/api/classes/${classId}/students/${selected.id}`, { method: "DELETE" });
    if (!response) return;
    if (!response.ok) {
      const data = await response.json();
      showError("student-error", data.error || "Could not remove the student.");
      return;
    }
    studentModal.hide();
    await loadClass();
  } catch {
    showError("student-error", "Cannot reach the server. Check your connection.");
  } finally {
    event.target.disabled = false;
  }
});

loadClass();
