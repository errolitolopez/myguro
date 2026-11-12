// Teacher: the Students tab. Everyone in the teacher's classes (and the individual students group) for the
// school year being viewed, searched by name and filtered in the browser; tapping a student opens their record.

const list = document.getElementById("students-list");
const search = document.getElementById("search");
const count = document.getElementById("students-count");
const classFilter = document.getElementById("class-filter");
const gradeFilter = document.getElementById("grade-filter");
const sectionFilter = document.getElementById("section-filter");
const statusFilter = document.getElementById("status-filter");
const filters = [classFilter, gradeFilter, sectionFilter, statusFilter];
// The value of each filter that means "no filter" (grade and section use "*", because "" means none set).
const NO_FILTER = new Map([[classFilter, ""], [gradeFilter, "*"], [sectionFilter, "*"], [statusFilter, ""]]);
let students = [];
// One page at a time, all in the browser: search and filters still look at every student.
const PAGE_SIZE = 20;
let page = 1; // the page shown
const pager = document.getElementById("pager");
const pageInfo = document.getElementById("page-info");
const prevPage = document.getElementById("prev-page");
const nextPage = document.getElementById("next-page");

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

// matches(student, "cruz") -> true when the name has the text (class, grade and section are the filters)
function matches(student, query) {
  return student.name.toLowerCase().includes(query);
}

// option("Rizal") -> <option value="Rizal">Rizal</option>
function option(value, label = value) {
  const element = document.createElement("option");
  element.value = value;
  element.textContent = label;
  return element;
}

// Fill the Class and Section filters from the teacher's own students, A to Z, keeping the first choice.
function fillFilters() {
  const byName = (a, b) => a.localeCompare(b, undefined, { sensitivity: "base", numeric: true });
  const classes = [...new Set(students.flatMap((student) => student.classes))].sort(byName);
  classFilter.replaceChildren(classFilter.options[0], ...classes.map((title) => option(title)));
  const sections = [...new Set(students.map((student) => student.section).filter(Boolean))].sort(byName);
  sectionFilter.replaceChildren(sectionFilter.options[0], ...sections.map((section) => option(section)));
  if (students.some((student) => !student.section)) sectionFilter.append(option("", t("No section")));
}

// passesFilters(student) -> true when the student fits every filter that is set
function passesFilters(student) {
  if (classFilter.value && !student.classes.includes(classFilter.value)) return false;
  if (gradeFilter.value !== "*" && (student.grade || "") !== gradeFilter.value) return false;
  if (sectionFilter.value !== "*" && (student.section || "") !== sectionFilter.value) return false;
  if (statusFilter.value === "active" && !student.active) return false;
  if (statusFilter.value === "deactivated" && student.active) return false;
  return true;
}

// The badge on the Filters button: how many filters are set.
function showFilterCount() {
  const inUse = filters.filter((select) => select.value !== NO_FILTER.get(select)).length;
  const badge = document.getElementById("filter-count");
  badge.textContent = inUse;
  badge.classList.toggle("d-none", inUse === 0);
}

function render() {
  const query = search.value.trim().toLowerCase();
  const shown = students.filter((student) => passesFilters(student) && (!query || matches(student, query)));
  showFilterCount();
  count.textContent = String(shown.length);
  count.classList.remove("d-none");
  // ‹ Prev · Page 2 of 3 · Next ›; a shorter list after a search can have fewer pages than the page shown
  const pages = Math.max(1, Math.ceil(shown.length / PAGE_SIZE));
  page = Math.min(page, pages);
  pager.classList.toggle("d-none", pages <= 1);
  pageInfo.textContent = t("Page {page} of {pages}", { page, pages });
  prevPage.disabled = page <= 1;
  nextPage.disabled = page >= pages;
  if (shown.length === 0) {
    list.replaceChildren(messageRow(students.length
      ? t("No student matches your search or filters.")
      : t("No students yet. Add students to a class first.")));
    return;
  }
  list.replaceChildren(...shown.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE).map(studentRow));
}

// goToPage(2) -> shows students 21 to 40, from the top of the page
function goToPage(newPage) {
  page = newPage;
  render();
  window.scrollTo({ top: 0 });
}

// A new search or filter starts again from page 1.
function renderFromStart() {
  page = 1;
  render();
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
    fillFilters();
    render();
  } catch {
    showError("students-error", t("Cannot reach the server. Check your connection."));
    list.replaceChildren();
  }
}

search.addEventListener("input", renderFromStart);
filters.forEach((select) => select.addEventListener("change", renderFromStart));
prevPage.addEventListener("click", () => goToPage(page - 1));
nextPage.addEventListener("click", () => goToPage(page + 1));
document.getElementById("filter-clear").addEventListener("click", () => {
  filters.forEach((select) => { select.value = NO_FILTER.get(select); });
  renderFromStart();
});
loadStudents();
