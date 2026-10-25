// Assign popup in the activity editor: give the sheet to some of the teacher's classes,
// each to everyone or to selected students, and/or to individual students who are in no class,
// with an optional due date.
// Uses activityId, unsaved, el() and showEditorError() from activity-editor.js.

let assignClasses = []; // the teacher's classes, each with .assignment (null = not given)
let assignDirect = null; // the direct assignment (individual students, no class), or null
let directDraft = null; // popup choices until Save: { due_date, students: Map of student id -> student }

const DIRECT_TITLE = "Individual students";
const DIRECT_SEARCH_DELAY = 300; // ms after the last key

const assignModal = bootstrap.Modal.getOrCreateInstance(document.getElementById("assign-modal"));
const assignList = document.getElementById("assign-classes");
const assignSaveButton = document.getElementById("assign-save-button");

// One class or group the sheet is given to: "Grade 12 – Luna" / "3 of 3 submitted · average 67% · due Oct 15, 2026".
// The text opens its results; the button opens the sheet to that class or group, or closes it again.
function checkItem(item) {
  const row = el("div", "list-group-item d-flex justify-content-between align-items-center gap-2");
  const link = el("a", "flex-grow-1 text-decoration-none text-reset");
  link.href = `/results/${item.id}`;
  const details = [`${item.submitted} of ${item.students} submitted`];
  if (item.average !== null) details.push(`average ${item.average}%`);
  if (item.due_date) details.push(`due ${formatDay(item.due_date)}`);
  link.append(el("div", "fw-semibold", item.class_name), el("div", "small text-body-secondary", details.join(" · ")));
  // Points still to check (short answers) stand out; "Checked" only once someone has submitted
  const badge = !item.to_check && !item.submitted ? el("span", "badge text-bg-secondary", "No answers yet")
    : el("span", item.to_check ? "badge text-bg-warning" : "badge text-bg-success",
      item.to_check ? `${plural(item.to_check, "point")} to check` : "Checked");
  badge.classList.add("d-none", "d-sm-inline");  // the buttons matter more on a small phone

  // Students see the sheet only while this is open. Closed is the starting state.
  const toggle = el("button", item.is_open
    ? "btn btn-sm btn-outline-secondary text-nowrap bi bi-door-closed"
    : "btn btn-sm btn-success text-nowrap bi bi-door-open", item.is_open ? " Close" : " Open");
  toggle.type = "button";
  toggle.dataset.openToggle = "1";  // lockEditor() leaves it enabled on a locked sheet
  toggle.setAttribute("aria-label", `${item.is_open ? "Close" : "Open"} for ${item.class_name}`);
  toggle.addEventListener("click", () => setOpened(item, toggle));
  row.append(link, badge, toggle);
  return row;
}

async function setOpened(item, button) {
  const stopLoading = startLoading(button);
  if (!stopLoading) return;
  try {
    const response = await apiFetch(`/api/assignments/${item.id}/open`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ open: !item.is_open }),
    });
    if (!response) return;
    if (!response.ok) {
      showEditorError((await response.json()).error || "Could not save.");
      return;
    }
    await loadCheckCard();
  } catch {
    showEditorError("Cannot reach the server. Check your connection.");
  } finally {
    stopLoading();
  }
}

// The card replaces the old "Given to" line: every class or group the sheet is given to.
async function loadCheckCard() {
  const list = document.getElementById("check-list");
  const message = (text) => el("div", "list-group-item small text-body-secondary", text);
  try {
    const response = await apiFetch(`/api/results/to-check?activity_id=${activityId}`);
    if (!response) return;
    if (!response.ok) {
      list.replaceChildren(message("Could not load the results."));
      return;
    }
    const items = (await response.json()).assignments;
    list.replaceChildren(...(items.length ? items.map(checkItem) : [message("Not given to any class or student yet.")]));
  } catch {
    list.replaceChildren(message("Cannot reach the server."));
  }
}

async function loadAssignments() {
  try {
    const response = await apiFetch(`/api/activities/${activityId}/assignments`);
    if (!response) return;
    if (!response.ok) {
      showEditorError("Could not load the classes.");
      return;
    }
    const data = await response.json();
    assignClasses = data.classes;
    assignDirect = data.direct;
  } catch {
    showEditorError("Cannot reach the server.");
  }
}

// One class in the popup. Ticking it shows the due date and who gets it.
// The choices are kept in item.draft until Save.
function assignItem(item) {
  const draft = item.draft;
  const box = el("div", "border rounded p-2");

  const check = el("div", "form-check");
  const checkbox = el("input", "form-check-input");
  checkbox.type = "checkbox";
  checkbox.id = `assign-${item.id}`;
  checkbox.checked = draft.given;
  const label = el("label", "form-check-label fw-semibold", classTitle(item));
  label.htmlFor = checkbox.id;
  label.append(el("span", "fw-normal small text-body-secondary", ` · ${plural(item.students.length, "student")}`));
  check.append(checkbox, label);
  box.append(check);

  const options = el("div", "ms-4 mt-2");
  options.classList.toggle("d-none", !draft.given);
  checkbox.addEventListener("change", () => {
    draft.given = checkbox.checked;
    options.classList.toggle("d-none", !draft.given);
  });

  // Due date
  const dueRow = el("div", "d-flex align-items-center gap-2 mb-2");
  const dueId = `due-${item.id}`;
  const dueLabel = el("label", "small text-nowrap", "Due date");
  dueLabel.htmlFor = dueId;
  const due = el("input", "form-control form-control-sm");
  due.type = "date";
  due.id = dueId;
  due.value = draft.due_date || "";
  due.style.maxWidth = "11rem";
  due.addEventListener("input", () => (draft.due_date = due.value || null));
  dueRow.append(dueLabel, due, el("span", "small text-body-secondary", "(optional)"));
  options.append(dueRow);

  // Everyone or selected students
  const who = el("div", "mb-1");
  const studentList = el("div", "border rounded p-2 mt-1 overflow-auto");
  studentList.style.maxHeight = "14rem";
  for (const [value, text] of [[true, "All students"], [false, "Selected students"]]) {
    const option = el("div", "form-check form-check-inline");
    const radio = el("input", "form-check-input");
    radio.type = "radio";
    radio.name = `who-${item.id}`;
    radio.id = `who-${item.id}-${value}`;
    radio.checked = draft.everyone === value;
    radio.addEventListener("change", () => {
      draft.everyone = value;
      studentList.classList.toggle("d-none", draft.everyone);
      // Nothing picked yet: start with everyone ticked, so excluding one student is one untick.
      if (!draft.everyone && draft.student_ids.size === 0) setAll(true);
    });
    const radioLabel = el("label", "form-check-label small", text);
    radioLabel.htmlFor = radio.id;
    option.append(radio, radioLabel);
    who.append(option);
  }
  options.append(who);

  // Student checklist (for "Selected students")
  studentList.classList.toggle("d-none", draft.everyone);
  if (item.students.length === 0) {
    studentList.append(el("div", "small text-body-secondary", "No students in this class yet."));
  }
  // "Select all" sits above the students and follows their ticks: checked when all are
  // ticked, dashed (indeterminate) when only some are.
  const ticks = [];
  let selectAll = null;
  const syncSelectAll = () => {
    if (!selectAll) return;
    const count = ticks.filter((tick) => tick.checked).length;
    selectAll.checked = count === ticks.length;
    selectAll.indeterminate = count > 0 && count < ticks.length;
  };
  const setAll = (checked) => {
    for (const tick of ticks) tick.checked = checked;
    for (const student of item.students) {
      if (checked) draft.student_ids.add(student.id);
      else draft.student_ids.delete(student.id);
    }
    syncSelectAll();
  };
  if (item.students.length > 0) {
    const allRow = el("div", "form-check border-bottom pb-1 mb-1");
    selectAll = el("input", "form-check-input");
    selectAll.type = "checkbox";
    selectAll.id = `pick-all-${item.id}`;
    selectAll.addEventListener("change", () => setAll(selectAll.checked));
    const allLabel = el("label", "form-check-label small fw-semibold", "Select all");
    allLabel.htmlFor = selectAll.id;
    allRow.append(selectAll, allLabel);
    studentList.append(allRow);
  }
  for (const student of item.students) {
    const row = el("div", "form-check");
    const tick = el("input", "form-check-input");
    tick.type = "checkbox";
    tick.id = `pick-${item.id}-${student.id}`;
    tick.checked = draft.student_ids.has(student.id);
    tick.addEventListener("change", () => {
      if (tick.checked) draft.student_ids.add(student.id);
      else draft.student_ids.delete(student.id);
      syncSelectAll();
    });
    ticks.push(tick);
    const tickLabel = el("label", "form-check-label small", student.name);
    tickLabel.htmlFor = tick.id;
    const place = gradeSection(student);
    if (place) tickLabel.append(el("span", "text-body-secondary", ` · ${place}`));
    row.append(tick, tickLabel);
    studentList.append(row);
  }
  syncSelectAll();
  options.append(studentList);

  box.append(options);
  return box;
}

// --- Individual students (no class) ---------------------------------------------------

// The "Individual students" part of the popup: due date, chosen students as removable chips,
// and a search of the school's students to add more. Choices stay in directDraft until Save.
function directBlock() {
  const box = el("div", "border rounded p-2");
  box.append(el("div", "fw-semibold", DIRECT_TITLE));
  box.append(el("div", "small text-body-secondary mb-2",
    "Give it to students who are not in your classes. Leave it empty for none."));

  // Due date
  const dueRow = el("div", "d-flex align-items-center gap-2 mb-2");
  const dueLabel = el("label", "small text-nowrap", "Due date");
  dueLabel.htmlFor = "due-direct";
  const due = el("input", "form-control form-control-sm");
  due.type = "date";
  due.id = "due-direct";
  due.value = directDraft.due_date || "";
  due.style.maxWidth = "11rem";
  due.addEventListener("input", () => (directDraft.due_date = due.value || null));
  dueRow.append(dueLabel, due, el("span", "small text-body-secondary", "(optional)"));
  box.append(dueRow);

  // Chosen students
  const chips = el("div", "d-flex flex-wrap gap-1 mb-2");
  const results = el("div", "border rounded p-2 overflow-auto");
  results.style.maxHeight = "14rem";
  let found = []; // the last search result

  const drawChips = () => {
    if (directDraft.students.size === 0) {
      chips.replaceChildren(el("span", "small text-body-secondary", "No students chosen yet."));
      return;
    }
    chips.replaceChildren(...[...directDraft.students.values()].map((student) => {
      const chip = el("span", "badge text-bg-secondary d-inline-flex align-items-center gap-1", student.name);
      const remove = el("button", "btn-close btn-close-white");
      remove.type = "button";
      remove.style.fontSize = "0.6rem";
      remove.setAttribute("aria-label", `Remove ${student.name}`);
      remove.addEventListener("click", () => {
        directDraft.students.delete(student.id);
        drawChips();
        drawResults();
      });
      chip.append(remove);
      return chip;
    }));
  };

  const drawResults = () => {
    if (found.length === 0) {
      results.replaceChildren(el("div", "small text-body-secondary", "No students found."));
      return;
    }
    results.replaceChildren(...found.map((student) => {
      const row = el("div", "d-flex justify-content-between align-items-center gap-2 small py-1");
      const label = el("span", "", student.name);
      const place = gradeSection(student);
      if (place) label.append(el("span", "text-body-secondary", ` · ${place}`));
      const add = el("button", "btn btn-sm btn-outline-primary py-0 bi bi-plus-lg", "Add");
      add.type = "button";
      add.disabled = directDraft.students.has(student.id);
      add.addEventListener("click", () => {
        directDraft.students.set(student.id, student);
        drawChips();
        drawResults();
      });
      row.append(label, add);
      return row;
    }));
  };

  // Search: text + one grade/section choice, run a moment after the last change.
  const searchRow = el("div", "d-flex flex-wrap gap-2 mb-2");
  const search = el("input", "form-control form-control-sm flex-grow-1");
  search.type = "search";
  search.placeholder = "Search name, username or section";
  search.setAttribute("aria-label", "Search students");
  const place = el("select", "form-select form-select-sm w-auto");
  place.setAttribute("aria-label", "Grade and section");
  place.append(new Option("All grades and sections", ""));
  searchRow.append(search, place);

  let timer = null;
  let latest = 0; // ignore a slow answer to an older search
  const runSearch = async () => {
    const ticket = ++latest;
    const params = new URLSearchParams({ q: search.value });
    if (place.value !== "") {
      const [grade, section] = JSON.parse(place.value);
      params.set("grade", grade);
      params.set("section", section);
    }
    try {
      const response = await apiFetch(`/api/activities/${activityId}/student-search?${params}`);
      if (!response || ticket !== latest) return;
      if (!response.ok) {
        results.replaceChildren(el("div", "small text-danger", "Could not search."));
        return;
      }
      const data = await response.json();
      found = data.students;
      // Fill the grade/section dropdown once, keeping the choice.
      if (place.options.length === 1) {
        data.sections.forEach((item) => place.append(
          new Option(gradeSection(item) || "No grade or section", JSON.stringify([item.grade, item.section]))));
      }
      drawResults();
      if (data.more) {
        results.append(el("div", "small text-body-secondary pt-1", "More students match: search to narrow."));
      }
    } catch {
      results.replaceChildren(el("div", "small text-danger", "Cannot reach the server."));
    }
  };
  search.addEventListener("input", () => {
    clearTimeout(timer);
    timer = setTimeout(runSearch, DIRECT_SEARCH_DELAY);
  });
  place.addEventListener("change", runSearch);

  box.append(chips, searchRow, results);
  drawChips();
  results.replaceChildren(el("div", "small text-body-secondary", "Loading..."));
  runSearch();
  return box;
}

document.getElementById("assign-button").addEventListener("click", async () => {
  if (unsaved) {
    showEditorError("Save your changes before assigning.");
    return;
  }
  hideError("assign-error");
  await loadAssignments();
  for (const item of assignClasses) {
    const given = item.assignment;
    item.draft = {
      given: Boolean(given),
      due_date: given ? given.due_date : null,
      everyone: given ? given.everyone : true,
      student_ids: new Set(given ? given.student_ids : []),
    };
  }
  directDraft = {
    due_date: assignDirect ? assignDirect.due_date : null,
    students: new Map((assignDirect ? assignDirect.students : []).map((student) => [student.id, student])),
  };
  if (assignClasses.length === 0) {
    const empty = el("p", "text-body-secondary mb-0", "You have no classes yet. ");
    const link = el("a", "", "Create a class");
    link.href = "/classes";
    empty.append(link, " first, or choose individual students below.");
    assignList.replaceChildren(empty);
  } else {
    assignList.replaceChildren(...assignClasses.map(assignItem));
  }
  document.getElementById("assign-direct").replaceChildren(directBlock());
  assignSaveButton.disabled = false;
  assignModal.show();
});

assignSaveButton.addEventListener("click", async () => {
  hideError("assign-error");
  const assignments = assignClasses
    .filter((item) => item.draft.given)
    .map((item) => ({
      class_id: item.id,
      due_date: item.draft.due_date,
      everyone: item.draft.everyone,
      student_ids: [...item.draft.student_ids],
    }));
  // No chosen students takes the direct assignment back.
  const direct = directDraft.students.size
    ? { due_date: directDraft.due_date, student_ids: [...directDraft.students.keys()] }
    : null;

  const stopLoading = startLoading(assignSaveButton);
  if (!stopLoading) return;
  try {
    const response = await apiFetch(`/api/activities/${activityId}/assignments`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ assignments, direct }),
    });
    if (!response) return;
    const data = await response.json();
    if (!response.ok) {
      showError("assign-error", data.error || "Could not save.");
      return;
    }
    assignClasses = data.classes;
    assignDirect = data.direct;
    loadCheckCard();
    assignModal.hide();
  } catch {
    showError("assign-error", "Cannot reach the server. Check your connection.");
  } finally {
    stopLoading();
  }
});

loadAssignments();
loadCheckCard();
