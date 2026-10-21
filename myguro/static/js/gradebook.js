// Class gradebook (teacher): a row per student, a column per activity given to the class, the
// score that counts in each cell and the student's average. Tapping a score opens the checking
// page; tapping an activity name opens its results.

const classId = document.querySelector("main").dataset.classId;
let book = null; // from /api/classes/<id>/gradebook

const head = document.getElementById("gradebook-head");
const body = document.getElementById("gradebook-body");
const foot = document.getElementById("gradebook-foot");
const searchInput = document.getElementById("search");

function el(tag, className = "", text = "") {
  const element = document.createElement(tag);
  if (className) element.className = className;
  if (text !== "") element.textContent = text;
  return element;
}

// One score cell: "8 / 10" with the percent, a status word, or nothing when the activity was not
// given to this student.
function scoreCell(student, cell, activity) {
  const td = el("td", "text-nowrap text-center");
  if (cell === null) {
    td.append(el("span", "text-body-secondary", "·"));
    return td;
  }
  if (cell.status === "excluded") {
    td.append(el("span", "badge text-bg-secondary", "Excluded"));
    return td;
  }
  if (cell.status === "not_started") {
    td.append(el("span", "text-body-secondary", "–"));
    return td;
  }
  const link = el("a", "text-decoration-none text-reset");
  link.href = `/results/${activity.assignment_id}/students/${student.id}`;
  if (cell.earned === null) {
    link.append(el("span", "badge text-bg-info", "Answering"));
  } else {
    link.append(el("span", "fw-semibold", `${cell.earned} / ${cell.possible}${cell.pending ? "*" : ""}`));
    if (cell.percent !== null) link.append(el("div", "small text-body-secondary", `${cell.percent}%`));
    if (cell.late) link.append(el("span", "badge text-bg-warning ms-1", "Late"));
  }
  td.append(link);
  return td;
}

function render() {
  const query = searchInput.value.trim().toLowerCase();
  const students = book.students.filter((student) =>
    [student.name, student.username, student.grade, student.section].some((text) => text.toLowerCase().includes(query)));

  head.replaceChildren(el("th", "", "Student"));
  book.activities.forEach((activity) => {
    const th = el("th", "text-center");
    const link = el("a", "text-decoration-none", activity.title);
    link.href = `/results/${activity.assignment_id}`;
    th.append(link, el("div", "small fw-normal text-body-secondary", `${activity.total_points} pts`));
    head.append(th);
  });
  head.append(el("th", "text-center", "Done"), el("th", "text-center", "Average"));

  if (!book.activities.length) {
    body.replaceChildren(rowMessage("No activity has been given to this class yet.", 1));
    foot.replaceChildren();
    return;
  }
  if (!students.length) {
    body.replaceChildren(rowMessage(book.students.length ? "No student matches your search." : "No students in this class yet.",
      book.activities.length + 3));
    foot.replaceChildren();
    return;
  }

  body.replaceChildren(...students.map((student) => {
    const row = el("tr");
    const name = el("td", "text-nowrap");
    name.append(el("div", "fw-semibold", student.name),
      el("div", "small text-body-secondary", [student.grade, student.section].filter(Boolean).join(" - ")));
    row.append(name);
    student.cells.forEach((cell, index) => row.append(scoreCell(student, cell, book.activities[index])));
    const given = student.cells.filter((cell) => cell !== null).length;
    row.append(el("td", "text-center", `${student.submitted}/${given}`),
      el("td", "text-center fw-semibold", student.average === null ? "–" : `${student.average}%`));
    return row;
  }));

  const total = el("tr", "fw-semibold");
  total.append(el("td", "", "Class average"));
  book.activities.forEach((activity) =>
    total.append(el("td", "text-center", activity.average === null ? "–" : `${activity.average}%`)));
  total.append(el("td"), el("td"));
  foot.replaceChildren(total);
}

function rowMessage(text, columns) {
  const row = el("tr");
  const cell = el("td", "text-body-secondary", text);
  cell.colSpan = columns;
  row.append(cell);
  return row;
}

async function loadGradebook() {
  try {
    const response = await apiFetch(`/api/classes/${classId}/gradebook`);
    if (!response) return;
    if (!response.ok) {
      showError("gradebook-error", "Could not load the gradebook.");
      return;
    }
    hideError("gradebook-error");
    book = await response.json();
    document.getElementById("gradebook-details").textContent = [
      book.class.name, book.class.subject,
      plural(book.students.length, "student"), plural(book.activities.length, "activity", "activities"),
    ].filter(Boolean).join(" · ");
    render();
  } catch {
    showError("gradebook-error", "Cannot reach the server. Check your connection.");
  }
}

searchInput.addEventListener("input", render);
loadGradebook();
