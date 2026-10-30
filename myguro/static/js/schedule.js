// Schedule generator (admin): enter the sections, teachers and subjects, set the rules, build the
// timetable, swap two periods by hand, then publish it to the teachers.

let data = null; // from /api/schedule
let editingSection = null; // the section open in the form, or null when adding
let editingTeacher = null;
let picked = null; // the first period tapped for a swap: {day, period}

const byId = (id) => document.getElementById(id);

function el(tag, className = "", text = "") {
  const element = document.createElement(tag);
  if (className) element.className = className;
  if (text !== "") element.textContent = text;
  return element;
}

// send("/api/schedule/sections", "POST", {...}, "section-form-error") -> the answer as an object, or null
// after showing the problem in the error box.
async function send(url, method, body, errorId) {
  try {
    const response = await apiFetch(url, {
      method,
      headers: { "Content-Type": "application/json" },
      body: body === undefined ? undefined : JSON.stringify(body),
    });
    if (!response) return null;
    const answer = await response.json();
    if (!response.ok) {
      showError(errorId, answer.error || t("Something went wrong."));
      return null;
    }
    hideError(errorId);
    return answer;
  } catch {
    showError(errorId, t("Cannot reach the server. Check your connection."));
    return null;
  }
}

// run(button, task) disables the button with a spinner while the task runs
async function run(button, task) {
  const stop = startLoading(button);
  if (!stop) return;
  try {
    await task();
  } finally {
    stop();
  }
}

const teacherName = (id) => (data.teachers.find((teacher) => teacher.id === id) || {}).name || "";
const periodsOf = (sectionId) => data.assignments.filter((a) => a.section_id === sectionId)
  .reduce((sum, a) => sum + a.per_week, 0);
const SLOTS_A_WEEK = () => data.days.length * data.periods.length;

// --- loading and the top of the page -----------------------------------------------------

async function load() {
  try {
    const response = await apiFetch("/api/schedule");
    if (!response) return;
    if (!response.ok) {
      showError("schedule-error", t("Could not load the schedule."));
      return;
    }
    hideError("schedule-error");
    data = await response.json();
    renderAll();
  } catch {
    showError("schedule-error", t("Cannot reach the server. Check your connection."));
  }
}

function renderAll() {
  const state = !data.built ? "not built yet" : data.published ? "published to teachers" : "built, not published";
  byId("schedule-status").textContent =
    `${plural(data.sections.length, "section")} · ${plural(data.teachers.length, "teacher")} · ${state}`;
  byId("publish-button").disabled = !data.built;
  byId("publish-button").lastChild.textContent = data.published ? t("Take back from teachers") : t("Publish to teachers");
  if (data.problems.length) showResult(t("The timetable breaks these rules:"), data.problems);
  renderSections();
  renderTeachers();
  renderAssignmentSection();
  renderAssignments();
  byId("rule-gap").value = data.rules.max_gap;
  byId("rule-day").value = data.rules.max_per_day === null ? "" : data.rules.max_per_day;
  renderViewSelect();
}

// showResult("Built", ["line", ...]) puts a message with an optional list in the blue box
function showResult(title, lines = []) {
  const box = byId("schedule-result");
  const list = el("ul", "mb-0");
  list.append(...lines.map((line) => el("li", "", line)));
  box.replaceChildren(el("div", lines.length ? "fw-semibold" : "", title), ...(lines.length ? [list] : []));
  box.classList.remove("d-none");
}

function emptyRow(text) {
  return el("div", "list-group-item text-body-secondary", text);
}

// --- sections ----------------------------------------------------------------------------

function renderSections() {
  if (!data.sections.length) {
    byId("section-list").replaceChildren(emptyRow(t("No sections yet. Tap Add section.")));
    return;
  }
  byId("section-list").replaceChildren(...data.sections.map((section) => {
    const row = el("button", "list-group-item list-group-item-action d-flex justify-content-between align-items-start gap-2");
    row.type = "button";
    const left = el("div");
    left.append(el("div", "fw-semibold", section.name),
      el("div", "small text-body-secondary", [section.grade && t("Grade {grade}", { grade: section.grade }), section.room && t("Room {room}", { room: section.room }),
        section.adviser].filter(Boolean).join(" · ")));
    const total = periodsOf(section.id);
    const badge = el("span", `badge ${total > SLOTS_A_WEEK() ? "text-bg-danger" : "text-bg-secondary"}`,
      `${total} / ${SLOTS_A_WEEK()} periods`);
    row.append(left, badge);
    row.addEventListener("click", () => openSectionForm(section));
    return row;
  }));
}

const sectionModal = () => bootstrap.Modal.getOrCreateInstance(byId("section-modal"));

function openSectionForm(section) {
  editingSection = section;
  byId("section-modal-title").textContent = section ? t("Edit section") : t("Add section");
  byId("section-name").value = section ? section.name : "";
  byId("section-grade").value = section ? section.grade : "";
  byId("section-room").value = section ? section.room : "";
  byId("section-adviser").value = section ? section.adviser : "";
  byId("section-delete").classList.toggle("d-none", !section);
  hideError("section-form-error");
  sectionModal().show();
}

byId("add-section-button").addEventListener("click", () => openSectionForm(null));
byId("section-modal").addEventListener("shown.bs.modal", () => byId("section-name").focus());

byId("section-form").addEventListener("submit", (event) => {
  event.preventDefault();
  run(byId("section-save"), async () => {
    const body = { name: byId("section-name").value, grade: byId("section-grade").value,
      room: byId("section-room").value, adviser: byId("section-adviser").value };
    const url = editingSection ? `/api/schedule/sections/${editingSection.id}` : "/api/schedule/sections";
    if (!await send(url, editingSection ? "PUT" : "POST", body, "section-form-error")) return;
    sectionModal().hide();
    await load();
  });
});

byId("section-delete").addEventListener("click", () => {
  if (!window.confirm(t("Delete this section and its subjects and timetable?"))) return;
  run(byId("section-delete"), async () => {
    if (!await send(`/api/schedule/sections/${editingSection.id}`, "DELETE", undefined, "section-form-error")) return;
    sectionModal().hide();
    await load();
  });
});

// --- teachers ----------------------------------------------------------------------------

function renderTeachers() {
  if (!data.teachers.length) {
    byId("teacher-list").replaceChildren(emptyRow(t("No teachers yet. Tap Add teacher.")));
    return;
  }
  byId("teacher-list").replaceChildren(...data.teachers.map((teacher) => {
    const row = el("button", "list-group-item list-group-item-action d-flex justify-content-between align-items-start gap-2");
    row.type = "button";
    const account = data.accounts.find((item) => item.id === teacher.user_id);
    const left = el("div");
    left.append(el("div", "fw-semibold", teacher.name),
      el("div", "small text-body-secondary", [account ? t("Account {username}", { username: account.username }) : t("No account linked"),
        teacher.blocked.length ? `${plural(teacher.blocked.length, "period")} unavailable` : ""].filter(Boolean).join(" · ")));
    const load = data.assignments.filter((a) => a.teacher_id === teacher.id).reduce((sum, a) => sum + a.per_week, 0);
    row.append(left, el("span", "badge text-bg-secondary", `${load} periods`));
    row.addEventListener("click", () => openTeacherForm(teacher));
    return row;
  }));
}

const teacherModal = () => bootstrap.Modal.getOrCreateInstance(byId("teacher-modal"));

function openTeacherForm(teacher) {
  editingTeacher = teacher;
  byId("teacher-modal-title").textContent = teacher ? t("Edit teacher") : t("Add teacher");
  byId("teacher-name").value = teacher ? teacher.name : "";
  byId("teacher-gap").value = teacher && teacher.max_gap !== null ? teacher.max_gap : "";
  byId("teacher-day").value = teacher && teacher.max_per_day !== null ? teacher.max_per_day : "";

  // The accounts not linked to another teacher
  const taken = new Set(data.teachers.filter((item) => !teacher || item.id !== teacher.id).map((item) => item.user_id));
  const select = byId("teacher-account");
  select.replaceChildren(new Option(t("No account"), ""),
    ...data.accounts.filter((account) => !taken.has(account.id)).map((account) => new Option(`${account.name} (${account.username})`, account.id)));
  select.value = teacher && teacher.user_id ? String(teacher.user_id) : "";

  // A box for every day and period the teacher might not be free
  const blocked = new Set((teacher ? teacher.blocked : []).map(([day, period]) => `${day}-${period}`));
  const head = el("tr");
  head.append(el("th", "", ""), ...data.days.map((day) => el("th", "small", day.slice(0, 3))));
  const rows = data.periods.map((period, index) => {
    const row = el("tr");
    row.append(el("th", "small text-nowrap fw-normal", period.label));
    data.days.forEach((_, day) => {
      const cell = el("td");
      const box = el("input", "form-check-input");
      box.type = "checkbox";
      box.dataset.day = day;
      box.dataset.period = index;
      box.checked = blocked.has(`${day}-${index}`);
      box.setAttribute("aria-label", `${data.days[day]} ${period.label} unavailable`);
      cell.append(box);
      row.append(cell);
    });
    return row;
  });
  byId("blocked-table").replaceChildren(head, ...rows);

  byId("teacher-delete").classList.toggle("d-none", !teacher);
  hideError("teacher-form-error");
  teacherModal().show();
}

byId("add-teacher-button").addEventListener("click", () => openTeacherForm(null));
byId("teacher-modal").addEventListener("shown.bs.modal", () => byId("teacher-name").focus());

byId("teacher-form").addEventListener("submit", (event) => {
  event.preventDefault();
  run(byId("teacher-save"), async () => {
    const number = (id) => (byId(id).value === "" ? null : Number(byId(id).value));
    const body = {
      name: byId("teacher-name").value,
      user_id: number("teacher-account"),
      max_gap: number("teacher-gap"),
      max_per_day: number("teacher-day"),
      blocked: [...byId("blocked-table").querySelectorAll("input:checked")].map((box) => [Number(box.dataset.day), Number(box.dataset.period)]),
    };
    const url = editingTeacher ? `/api/schedule/teachers/${editingTeacher.id}` : "/api/schedule/teachers";
    if (!await send(url, editingTeacher ? "PUT" : "POST", body, "teacher-form-error")) return;
    teacherModal().hide();
    await load();
  });
});

byId("teacher-delete").addEventListener("click", () => {
  if (!window.confirm(t("Delete this teacher?"))) return;
  run(byId("teacher-delete"), async () => {
    if (!await send(`/api/schedule/teachers/${editingTeacher.id}`, "DELETE", undefined, "teacher-form-error")) return;
    teacherModal().hide();
    await load();
  });
});

// --- subjects of a section ---------------------------------------------------------------

const chosenSection = () => Number(byId("assignment-section").value) || null;

function renderAssignmentSection() {
  const select = byId("assignment-section");
  const keep = select.value;
  select.replaceChildren(...data.sections.map((section) => new Option(section.name, section.id)));
  if (data.sections.some((section) => String(section.id) === keep)) select.value = keep;
}

// One editable row: subject, teacher, periods a week, Save (and Delete for a saved one)
function assignmentRow(assignment) {
  const row = el("div", "row g-2 align-items-center mb-2");
  const subject = el("input", "form-control");
  subject.maxLength = 30;
  subject.placeholder = t("Subject");
  subject.setAttribute("aria-label", t("Subject"));
  subject.value = assignment ? assignment.subject : "";
  subject.disabled = Boolean(assignment); // the subject is the key; delete it to rename
  const teacher = el("select", "form-select");
  teacher.setAttribute("aria-label", t("Teacher"));
  teacher.append(new Option(t("Teacher"), ""), ...data.teachers.map((item) => new Option(item.name, item.id)));
  teacher.value = assignment ? String(assignment.teacher_id) : "";
  const perWeek = el("input", "form-control");
  perWeek.type = "number";
  perWeek.min = 1;
  perWeek.max = SLOTS_A_WEEK();
  perWeek.placeholder = t("Periods");
  perWeek.setAttribute("aria-label", t("Periods a week"));
  perWeek.value = assignment ? assignment.per_week : "";
  const save = el("button", `btn btn-outline-success bi ${assignment ? "bi-check-lg" : "bi-plus-lg"}`, assignment ? t("Save") : t("Add"));
  save.type = "button";
  save.addEventListener("click", () => run(save, async () => {
    const body = { section_id: chosenSection(), subject: subject.value, teacher_id: Number(teacher.value) || null,
      per_week: perWeek.value === "" ? null : Number(perWeek.value) };
    if (!await send("/api/schedule/assignments", "PUT", body, "schedule-error")) return;
    await load();
  }));

  const columns = [[subject, "col-12 col-sm-3"], [teacher, "col-12 col-sm-4"], [perWeek, "col-6 col-sm-2"]];
  columns.forEach(([input, width]) => {
    const cell = el("div", width);
    cell.append(input);
    row.append(cell);
  });
  const actions = el("div", "col-6 col-sm-3 d-flex gap-2");
  actions.append(save);
  if (assignment) {
    const remove = el("button", "btn btn-outline-danger bi bi-trash");
    remove.type = "button";
    remove.setAttribute("aria-label", t("Remove {subject}", { subject: assignment.subject }));
    remove.addEventListener("click", () => run(remove, async () => {
      if (!await send(`/api/schedule/assignments/${assignment.id}`, "DELETE", undefined, "schedule-error")) return;
      await load();
    }));
    actions.append(remove);
  }
  row.append(actions);
  return row;
}

function renderAssignments() {
  const sectionId = chosenSection();
  if (!sectionId) {
    byId("assignment-list").replaceChildren(el("div", "text-body-secondary", t("Add a section first.")));
    return;
  }
  const mine = data.assignments.filter((assignment) => assignment.section_id === sectionId);
  const total = periodsOf(sectionId);
  const note = el("div", `small mb-2 ${total > SLOTS_A_WEEK() ? "text-danger" : "text-body-secondary"}`,
    `${total} of ${SLOTS_A_WEEK()} periods a week used`);
  byId("assignment-list").replaceChildren(note, ...mine.map(assignmentRow), assignmentRow(null));
}

byId("assignment-section").addEventListener("change", renderAssignments);

// --- rules, building, publishing -----------------------------------------------------------

byId("rules-form").addEventListener("submit", (event) => {
  event.preventDefault();
  run(byId("rules-button"), async () => {
    const day = byId("rule-day").value;
    const answer = await send("/api/schedule/rules", "PUT",
      { max_gap: byId("rule-gap").value === "" ? null : Number(byId("rule-gap").value), max_per_day: day === "" ? null : Number(day) },
      "schedule-error");
    if (answer) showResult(t("Rules saved. Build the schedule again to use them."));
  });
});

byId("generate-button").addEventListener("click", () => {
  if (data.built && !window.confirm(t("Build a new schedule? The current one, with any swaps, is replaced."))) return;
  run(byId("generate-button"), async () => {
    const answer = await send("/api/schedule/generate", "POST", {}, "schedule-error");
    if (!answer) return;
    await load();
    const lines = [...answer.unplaced.map((line) => t("Not placed: {line}", { line })), ...answer.problems];
    showResult(t("Built: {periods} placed.", { periods: plural(answer.placed, "period") }) + (lines.length ? t(" Check these:") : ""), lines);
  });
});

byId("publish-button").addEventListener("click", () => run(byId("publish-button"), async () => {
  if (!await send("/api/schedule/published", "PUT", { published: !data.published }, "schedule-error")) return;
  await load();
}));

// --- the timetable ------------------------------------------------------------------------

function renderViewSelect() {
  const select = byId("view-select");
  const keep = select.value;
  const sections = data.sections.map((section) => new Option(t("Section: {name}", { name: section.name }), `s:${section.id}`));
  const teachers = data.teachers.map((teacher) => new Option(t("Teacher: {name}", { name: teacher.name }), `t:${teacher.id}`));
  select.replaceChildren(new Option(data.built ? t("Choose a section or a teacher") : t("Build the schedule first"), ""), ...sections, ...teachers);
  if ([...select.options].some((option) => option.value === keep)) select.value = keep;
  showTimetable();
}

// The cell of a section's timetable: the subject and its teacher. Tap two cells to swap them.
function sectionCell(cell, day, period) {
  const td = el("td", "swap-cell");
  td.style.cursor = "pointer";
  if (picked && picked.day === day && picked.period === period) td.classList.add("table-primary");
  if (cell) td.append(el("div", "fw-semibold", cell.subject), el("div", "text-body-secondary", cell.teacher));
  else td.append(el("span", "text-body-secondary", t("Free")));
  td.addEventListener("click", () => tapCell(day, period));
  return td;
}

async function tapCell(day, period) {
  if (!picked) {
    picked = { day, period };
    showTimetable();
    return;
  }
  if (picked.day === day && picked.period === period) {
    picked = null;
    showTimetable();
    return;
  }
  const first = picked;
  picked = null;
  const sectionId = Number(byId("view-select").value.slice(2));
  const answer = await send("/api/schedule/swap", "POST",
    { section_id: sectionId, a: [first.day, first.period], b: [day, period] }, "schedule-error");
  const box = byId("swap-result");
  box.replaceChildren();
  if (answer && answer.warnings.length) {
    box.append(el("div", "fw-semibold", t("Swapped. These rules are now broken:")));
    const list = el("ul", "mb-0");
    list.append(...answer.warnings.map((line) => el("li", "", line)));
    box.append(list);
  }
  box.classList.toggle("d-none", !(answer && answer.warnings.length));
  await load();
}

async function showTimetable() {
  const value = byId("view-select").value;
  const table = byId("schedule-table");
  table.classList.toggle("d-none", !value);
  byId("view-note").textContent = "";
  if (!value) return;
  const isSection = value.startsWith("s:");
  const url = `/api/schedule/${isSection ? "sections" : "teachers"}/${value.slice(2)}/grid`;
  try {
    const response = await apiFetch(url);
    if (!response) return;
    const grid = await response.json();
    if (!response.ok) {
      showError("schedule-error", grid.error || t("Could not load the timetable."));
      return;
    }
    byId("view-note").textContent = [grid.details, isSection ? t("Tap two periods to swap them.") : ""].filter(Boolean).join(" · ");
    scheduleGrid(grid, isSection ? sectionCell : teacherCell);
  } catch {
    showError("schedule-error", t("Cannot reach the server. Check your connection."));
  }
}

byId("view-select").addEventListener("change", () => {
  picked = null;
  byId("swap-result").classList.add("d-none");
  showTimetable();
});

load();
