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
    td.append(el("span", "badge text-bg-secondary", t("Excluded")));
    return td;
  }
  if (cell.status === "not_started") {
    td.append(el("span", "text-body-secondary", "–"));
    return td;
  }
  const link = el("a", "text-decoration-none text-reset");
  link.href = `/results/${activity.assignment_id}/students/${student.id}`;
  if (cell.earned === null) {
    const answering = el("span", "badge text-bg-info", "…");
    answering.title = t("Answering");
    answering.setAttribute("aria-label", t("Answering"));
    link.append(answering);
  } else {
    // One line: "8/10" (the percent beside it from a tablet up, to keep phone columns narrow)
    link.append(el("span", "fw-semibold", `${cell.earned}/${cell.possible}${cell.pending ? "*" : ""}`));
    if (cell.percent !== null) link.append(el("span", "d-none d-sm-inline small text-body-secondary ms-1", `${cell.percent}%`));
    if (cell.late) {
      const late = el("span", "badge text-bg-warning ms-1", "L");
      late.title = t("Late");
      late.setAttribute("aria-label", t("Late"));
      link.append(late);
    }
  }
  td.append(link);
  return td;
}

function render() {
  const query = searchInput.value.trim().toLowerCase();
  const students = book.students.filter((student) =>
    [student.name, student.username, student.grade, student.section].some((text) => text.toLowerCase().includes(query)));

  head.replaceChildren(el("th", "", t("Student")));
  book.activities.forEach((activity) => {
    const th = el("th", "text-center");
    const link = el("a", "text-decoration-none d-inline-block gb-title", activity.title);
    link.href = `/results/${activity.assignment_id}`;
    th.append(link, el("div", "fw-normal text-body-secondary", `${activity.total_points} pts`));
    head.append(th);
  });
  // "Done" is left out on a phone: the average is what the teacher looks for
  head.append(el("th", "text-center d-none d-sm-table-cell", t("Done")), el("th", "text-center", t("Avg")));

  if (!book.activities.length) {
    body.replaceChildren(rowMessage(t("No activity has been given to this class yet."), 1));
    foot.replaceChildren();
    return;
  }
  if (!students.length) {
    body.replaceChildren(rowMessage(book.students.length ? t("No student matches your search.") : t("No students in this class yet."),
      book.activities.length + 3));
    foot.replaceChildren();
    return;
  }

  body.replaceChildren(...students.map((student) => {
    const row = el("tr");
    const name = el("td", "text-nowrap");
    const nameText = el("div", "fw-semibold text-truncate gb-name", student.name);
    nameText.title = student.name;
    name.append(nameText);
    const place = [student.grade, student.section].filter(Boolean).join(" - ");
    if (place) name.append(el("div", "d-none d-sm-block text-body-secondary", place));
    row.append(name);
    student.cells.forEach((cell, index) => row.append(scoreCell(student, cell, book.activities[index])));
    const given = student.cells.filter((cell) => cell !== null).length;
    row.append(el("td", "text-center d-none d-sm-table-cell", `${student.submitted}/${given}`),
      el("td", "text-center fw-semibold", student.average === null ? "–" : `${student.average}%`));
    return row;
  }));

  const total = el("tr", "fw-semibold");
  total.append(el("td", "", t("Class avg")));
  book.activities.forEach((activity) =>
    total.append(el("td", "text-center", activity.average === null ? "–" : `${activity.average}%`)));
  total.append(el("td", "d-none d-sm-table-cell"), el("td"));
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
      showError("gradebook-error", t("Could not load the gradebook."));
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
    showError("gradebook-error", t("Cannot reach the server. Check your connection."));
  }
}

searchInput.addEventListener("input", render);
loadGradebook();
