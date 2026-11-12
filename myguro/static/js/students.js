// Teacher: the Students tab. Everyone in the teacher's classes (and the individual students group) for the
// school year being viewed, searched in the browser; tapping a student opens their record.

const list = document.getElementById("students-list");
const search = document.getElementById("search");
const count = document.getElementById("students-count");
let students = [];

// messageRow("No students yet.") -> a grey row in the list
function messageRow(text) {
  const row = document.createElement("div");
  row.className = "list-group-item text-body-secondary";
  row.textContent = text;
  return row;
}

// One student: name, username · grade - section, and the teacher's classes they are in.
function studentRow(student) {
  const row = document.createElement("a");
  row.href = `/my-students/${student.id}`;
  row.className = "list-group-item list-group-item-action d-flex justify-content-between align-items-center gap-2";

  const left = document.createElement("div");
  left.className = "min-w-0";
  const name = document.createElement("div");
  name.className = "fw-semibold";
  name.textContent = student.name;
  const details = document.createElement("div");
  details.className = "small text-body-secondary";
  const username = document.createElement("span");
  username.className = "font-monospace";
  username.textContent = student.username;
  const place = gradeSection(student);
  details.append(username, place ? ` · ${place}` : "");
  const classes = document.createElement("div");
  classes.className = "small text-body-secondary";
  classes.textContent = student.classes.join(", ");
  left.append(name, details, classes);
  row.append(left);

  if (!student.active) {
    const badge = document.createElement("span");
    badge.className = "badge text-bg-secondary";
    badge.textContent = t("Deactivated");
    row.append(badge);
  }
  return row;
}

// matches(student, "rizal") -> true when the name, username, grade, section or a class has the text
function matches(student, query) {
  return [student.name, student.username, student.grade || "", student.section || "", ...student.classes]
    .some((text) => text.toLowerCase().includes(query));
}

function render() {
  const query = search.value.trim().toLowerCase();
  const shown = query ? students.filter((student) => matches(student, query)) : students;
  count.textContent = String(shown.length);
  count.classList.remove("d-none");
  if (shown.length === 0) {
    list.replaceChildren(messageRow(students.length
      ? t("No student matches your search.")
      : t("No students yet. Add students to a class first.")));
    return;
  }
  list.replaceChildren(...shown.map(studentRow));
}

async function loadStudents() {
  try {
    const response = await apiFetch("/api/my-students");
    if (!response) return;
    if (!response.ok) {
      showError("students-error", t("Could not load your students."));
      list.replaceChildren();
      return;
    }
    hideError("students-error");
    students = (await response.json()).students;
    render();
  } catch {
    showError("students-error", t("Cannot reach the server. Check your connection."));
    list.replaceChildren();
  }
}

search.addEventListener("input", render);
loadStudents();
