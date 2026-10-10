// Assign popup in the activity editor: give the sheet to some of the teacher's classes,
// each to everyone or to selected students, with an optional due date.
// Uses activityId, unsaved, el(), showEditorError() and showStatusBadge() from activity-editor.js.

let assignClasses = []; // the teacher's classes, each with .assignment (null = not given)

const assignModal = bootstrap.Modal.getOrCreateInstance(document.getElementById("assign-modal"));
const assignList = document.getElementById("assign-classes");
const assignSaveButton = document.getElementById("assign-save-button");

// "Grade 9 - Rizal · Science (due Oct 15, 2026), Grade 9 - Bonifacio · Science (5 students)"
function showAssignedSummary() {
  const given = assignClasses.filter((item) => item.assignment);
  showStatusBadge(given.length);
  const summary = document.getElementById("assigned-summary");
  if (given.length === 0) {
    summary.replaceChildren("No class yet — this is a draft only you can see.");
    return;
  }
  // One line per class, each with a link to its results.
  summary.replaceChildren(...given.map((item) => {
    const details = [];
    if (!item.assignment.everyone) details.push(plural(item.assignment.student_ids.length, "student"));
    if (item.assignment.due_date) details.push(`due ${formatDay(item.assignment.due_date)}`);
    const line = el("div", "", classTitle(item) + (details.length ? ` (${details.join(", ")})` : "") + " · ");
    const link = el("a", "", "Results");
    link.href = `/results/${item.assignment.id}`;
    line.append(link);
    return line;
  }));
}

async function loadAssignments() {
  try {
    const response = await apiFetch(`/api/activities/${activityId}/assignments`);
    if (!response) return;
    if (!response.ok) {
      document.getElementById("assigned-summary").textContent = "Could not load the classes.";
      return;
    }
    assignClasses = (await response.json()).classes;
    showAssignedSummary();
  } catch {
    document.getElementById("assigned-summary").textContent = "Cannot reach the server.";
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
  for (const student of item.students) {
    const row = el("div", "form-check");
    const tick = el("input", "form-check-input");
    tick.type = "checkbox";
    tick.id = `pick-${item.id}-${student.id}`;
    tick.checked = draft.student_ids.has(student.id);
    tick.addEventListener("change", () => {
      if (tick.checked) draft.student_ids.add(student.id);
      else draft.student_ids.delete(student.id);
    });
    const tickLabel = el("label", "form-check-label small", student.name);
    tickLabel.htmlFor = tick.id;
    const place = gradeSection(student);
    if (place) tickLabel.append(el("span", "text-body-secondary", ` · ${place}`));
    row.append(tick, tickLabel);
    studentList.append(row);
  }
  options.append(studentList);

  box.append(options);
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
  if (assignClasses.length === 0) {
    const empty = el("p", "text-body-secondary mb-0", "You have no classes yet. ");
    const link = el("a", "", "Create a class");
    link.href = "/classes";
    empty.append(link, " first.");
    assignList.replaceChildren(empty);
  } else {
    assignList.replaceChildren(...assignClasses.map(assignItem));
  }
  assignSaveButton.disabled = assignClasses.length === 0;
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

  assignSaveButton.disabled = true;
  try {
    const response = await apiFetch(`/api/activities/${activityId}/assignments`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ assignments }),
    });
    if (!response) return;
    const data = await response.json();
    if (!response.ok) {
      showError("assign-error", data.error || "Could not save.");
      return;
    }
    assignClasses = data.classes;
    showAssignedSummary();
    assignModal.hide();
  } catch {
    showError("assign-error", "Cannot reach the server. Check your connection.");
  } finally {
    assignSaveButton.disabled = false;
  }
});

loadAssignments();
