// Results of one assignment (a sheet given to a class), for the teacher: every student's
// status and score (in total and per activity section), and one student's answers next to
// the answer key, where the teacher scores short answers or changes any question's points.
// A student who answered on paper gets a paper score (a total typed by the teacher).

const assignmentId = document.querySelector("main").dataset.assignmentId;
let results = null; // from /api/assignments/<id>/results
let openStudentId = null; // the student shown in the popup
let detail = null; // the attempt shown in the popup
let changedPoints = {}; // question id -> new points, not saved yet

const LETTERS = "ABCDEF";
const STATUS = {
  not_started: ["Not started", "text-bg-light border"],
  in_progress: ["Answering", "text-bg-info"],
  submitted: ["Submitted", "text-bg-success"],
};

const studentModal = bootstrap.Modal.getOrCreateInstance(document.getElementById("student-modal"));
const savePointsButton = document.getElementById("save-points-button");

function el(tag, className = "", text = "") {
  const element = document.createElement(tag);
  if (className) element.className = className;
  if (text !== "") element.textContent = text;
  return element;
}

// "4 / 6" (+ "+5 to check"), or "–"
function scoreCell(score) {
  const cell = el("td", "text-nowrap");
  if (!score) {
    cell.append(el("span", "text-body-secondary", "–"));
    return cell;
  }
  cell.append(el("span", "fw-semibold", `${score.earned} / ${score.possible - score.pending}`));
  if (score.pending) cell.append(el("div", "small text-warning-emphasis", `+${score.pending} to check`));
  return cell;
}

// --- The table ----------------------------------------------------------------------

function render() {
  const { assignment, sections, students, summary } = results;
  document.title = `${assignment.title} · Results · myguro`;
  document.getElementById("results-title").textContent = assignment.title;
  document.getElementById("results-details").textContent = [
    assignment.class_name,
    assignment.due_date ? `due ${formatDay(assignment.due_date)}` : "no due date",
    assignment.max_attempts === null ? "unlimited submissions"
      : plural(assignment.max_attempts, "submission") + " allowed",
  ].join(" · ");
  const back = document.getElementById("back-link");
  back.href = `/classes/${assignment.class_id}`;
  back.textContent = `‹ ${assignment.class_name}`;
  document.getElementById("edit-link").href = `/activities/${assignment.activity_id}`;

  document.getElementById("stat-submitted").textContent = `${summary.submitted} / ${summary.students}`;
  document.getElementById("stat-not-started").textContent = summary.not_started;
  document.getElementById("stat-late").textContent = summary.late;
  document.getElementById("stat-average").textContent = summary.average === null ? "–" : `${summary.average}%`;
  document.getElementById("stat-to-check").textContent = summary.to_check;

  const head = document.getElementById("results-head");
  head.replaceChildren(el("th", "", "Student"), el("th", "", "Status"), el("th", "", "Score"),
    ...sections.map((section) => el("th", "small fw-normal", section.title)), el("th", "", "Tries"));

  const query = document.getElementById("search").value.trim().toLowerCase();
  const filter = document.getElementById("filter").value;
  const shown = students.filter((student) => {
    if (query && !student.name.toLowerCase().includes(query) && !student.username.includes(query)) return false;
    if (filter === "submitted") return student.score !== null;
    if (filter === "not_submitted") return student.score === null;
    if (filter === "to_check") return student.score !== null && student.score.pending > 0;
    if (filter === "late") return student.late;
    return true;
  });

  const body = document.getElementById("results-body");
  if (shown.length === 0) {
    const row = el("tr");
    const cell = el("td", "text-body-secondary",
      students.length ? "No student matches." : "No students in this assignment.");
    cell.colSpan = 4 + sections.length;
    row.append(cell);
    body.replaceChildren(row);
    return;
  }
  body.replaceChildren(...shown.map((student) => {
    const row = el("tr");
    row.tabIndex = 0;
    row.addEventListener("click", () => openStudent(student.id));
    row.addEventListener("keydown", (event) => {
      if (event.key === "Enter") openStudent(student.id);
    });

    const name = el("td");
    name.append(el("div", "fw-semibold", student.name),
      el("div", "small text-body-secondary", gradeSection(student) || student.username));
    const status = el("td");
    const [label, style] = STATUS[student.status];
    status.append(el("span", `badge ${style}`, label));
    if (student.paper) status.append(" ", el("span", "badge text-bg-secondary", "Paper"));
    if (student.late) status.append(" ", el("span", "badge text-bg-warning", "Late"));

    row.append(name, status, scoreCell(student.score),
      ...sections.map((section) => scoreCell(student.section_scores[section.id])),
      el("td", "text-body-secondary", student.attempts ? String(student.attempts) : "–"));
    return row;
  }));
}

async function loadResults() {
  try {
    const response = await apiFetch(`/api/assignments/${assignmentId}/results`);
    if (!response) return;
    if (response.status === 404) {
      window.location.href = "/activities";
      return;
    }
    if (!response.ok) {
      showError("results-error", "Could not load the results.");
      return;
    }
    hideError("results-error");
    results = await response.json();
    render();
  } catch {
    showError("results-error", "Cannot reach the server. Check your connection.");
  }
}

document.getElementById("search").addEventListener("input", render);
document.getElementById("filter").addEventListener("change", render);

// --- One student ---------------------------------------------------------------------

// The student's answer, written out: "B. Hinduism", "True", "India, Japan", ...
function answerText(question, value) {
  if (value === null || value === undefined) return null;
  if (question.type === "multiple_choice") return `${LETTERS[value]}. ${question.choices[value]}`;
  if (question.type === "true_false") return value ? "True" : "False";
  if (question.type === "fill_blank") return value.map((item, index) => `${index + 1}) ${item || "—"}`).join("   ");
  return value;
}

// The answer key, written out.
function keyText(question) {
  if (question.type === "multiple_choice") return `${LETTERS[question.answer]}. ${question.choices[question.answer]}`;
  if (question.type === "true_false") return question.answer ? "True" : "False";
  if (question.type === "identification") return question.answer.join(" / ");
  if (question.type === "fill_blank") {
    return question.answer.map((accepted, index) => `${index + 1}) ${accepted.join(" / ")}`).join("   ");
  }
  return question.answer; // short answer: the guide (may be empty)
}

function questionReview(question, number, editable) {
  const item = el("div", "border rounded p-2 mb-2");
  const top = el("div", "d-flex justify-content-between align-items-start gap-2");
  top.append(el("div", "preserve-lines", `${number}. ${question.prompt}`));

  // Points: editable on a submitted attempt. Empty = short answer not checked yet.
  const pointsBox = el("div", "d-flex align-items-center gap-1 text-nowrap");
  if (editable) {
    const input = el("input", "form-control form-control-sm text-end");
    input.type = "number";
    input.min = 0;
    input.max = question.points;
    input.style.width = "4.5rem";
    input.value = question.earned === null ? "" : question.earned;
    input.placeholder = question.type === "short_answer" ? "?" : "0";
    input.setAttribute("aria-label", `Points for question ${number}`);
    input.addEventListener("input", () => {
      changedPoints[question.id] = input.value === "" ? null : Number(input.value);
      savePointsButton.disabled = false;
      document.getElementById("points-status").textContent = "Unsaved scores";
    });
    pointsBox.append(input, el("span", "small text-body-secondary", `/ ${question.points}`));
  } else {
    pointsBox.append(el("span", "small text-body-secondary", plural(question.points, "pt", "pts")));
  }
  top.append(pointsBox);
  item.append(top);

  const given = answerText(question, question.given);
  const answerRow = el("div", "mt-1 small");
  answerRow.append(el("span", "text-body-secondary", "Answer: "));
  answerRow.append(given === null ? el("em", "text-body-secondary", "no answer")
    : el("span", question.type === "short_answer" ? "preserve-lines d-block border rounded p-2 mt-1" : "fw-semibold", given));
  if (question.is_correct === true) answerRow.append(" ", el("span", "badge text-bg-success", "✓"));
  if (question.is_correct === false && question.earned > 0) answerRow.append(" ", el("span", "badge text-bg-warning", "part"));
  else if (question.is_correct === false) answerRow.append(" ", el("span", "badge text-bg-danger", "✗"));
  if (question.type === "short_answer" && editable && question.earned === null && given !== null) {
    answerRow.append(" ", el("span", "badge text-bg-warning", "to check"));
  }
  item.append(answerRow);

  const key = keyText(question);
  if (key) {
    const keyRow = el("div", "small text-body-secondary mt-1");
    keyRow.append(question.type === "short_answer" ? "Guide: " : "Key: ", el("span", "preserve-lines", key));
    item.append(keyRow);
  }
  return item;
}

function renderStudent(data) {
  const student = data.student;
  detail = data.detail;
  possiblePoints = data.possible;
  hidePaperForm();
  changedPoints = {};
  savePointsButton.disabled = true;
  document.getElementById("points-status").textContent = "";
  document.getElementById("student-title").textContent = student.name;
  document.getElementById("student-subtitle").textContent =
    [student.username, gradeSection(student)].filter(Boolean).join(" · ");

  // Attempt buttons: "Attempt 1", "Attempt 2 ✓ counts", "Attempt 3 (answering)"
  const buttons = document.getElementById("attempt-buttons");
  buttons.replaceChildren(...data.attempts.map((attempt) => {
    const label = `Attempt ${attempt.attempt}` + (attempt.paper ? " · paper" : "") + (attempt.counts ? " · counts" : "")
      + (attempt.submitted_at ? (attempt.late ? " · late" : "") : " · answering");
    const button = el("button", `btn ${detail && detail.attempt === attempt.attempt ? "btn-secondary" : "btn-outline-secondary"}`, label);
    button.type = "button";
    button.addEventListener("click", () => openStudent(student.id, attempt.attempt));
    return button;
  }));
  document.getElementById("reopen-button").classList.toggle("d-none", !data.can_reopen);
  document.getElementById("reopen-confirm").classList.add("d-none");

  const area = document.getElementById("student-detail");
  if (!detail) {
    area.replaceChildren(el("p", "text-body-secondary", "This student hasn't started yet."));
    savePointsButton.classList.add("d-none");
    return;
  }
  if (detail.paper) {
    // A paper score: only the total, with Edit.
    savePointsButton.classList.add("d-none");
    const card = el("div", "card card-body");
    card.append(el("p", "fw-semibold mb-1",
      `Paper score: ${detail.score.total.earned} / ${detail.score.total.possible}` + (detail.late ? " · submitted late" : "")));
    if (detail.note) card.append(el("p", "small text-body-secondary mb-2", detail.note));
    const edit = el("button", "btn btn-sm btn-outline-secondary align-self-start", "Edit paper score");
    edit.type = "button";
    edit.addEventListener("click", () => showPaperForm(detail));
    card.append(edit);
    area.replaceChildren(card);
    return;
  }

  const editable = Boolean(detail.submitted_at);
  savePointsButton.classList.toggle("d-none", !editable);

  const parts = [];
  if (detail.score) {
    const total = detail.score.total;
    parts.push(el("p", "fw-semibold",
      `Score: ${total.earned} / ${total.possible - total.pending}` +
      (total.pending ? ` (+${total.pending} points to check)` : "") + (detail.late ? " · submitted late" : "")));
  } else {
    parts.push(el("p", "text-body-secondary", "Still answering — these are the answers saved so far."));
  }
  detail.sections.filter((section) => section.kind === "activity").forEach((section) => {
    const block = el("section", "mb-3");
    const header = el("div", "d-flex justify-content-between align-items-center");
    header.append(el("h3", "h6 mb-2", section.title || "Activity"));
    const sectionScore = detail.score && detail.score.sections[section.id];
    if (sectionScore) {
      header.append(el("span", "badge text-bg-light border",
        `${sectionScore.earned} / ${sectionScore.possible - sectionScore.pending}` +
        (sectionScore.pending ? ` +${sectionScore.pending}` : "")));
    }
    block.append(header);
    section.questions.forEach((question, index) => block.append(questionReview(question, index + 1, editable)));
    parts.push(block);
  });
  area.replaceChildren(...parts);
}

async function openStudent(studentId, attempt) {
  if (Object.keys(changedPoints).length && openStudentId === studentId) {
    document.getElementById("points-status").textContent = "Save or close first: there are unsaved scores.";
    return;
  }
  openStudentId = studentId;
  hideError("student-error");
  try {
    const query = attempt ? `?attempt=${attempt}` : "";
    const response = await apiFetch(`/api/assignments/${assignmentId}/students/${studentId}${query}`);
    if (!response) return;
    const data = await response.json();
    if (!response.ok) {
      showError("student-error", data.error || "Could not load the answers.");
      return;
    }
    renderStudent(data);
    studentModal.show();
  } catch {
    showError("results-error", "Cannot reach the server. Check your connection.");
  }
}

// Closing the popup drops unsaved scores (the table only shows saved ones).
document.getElementById("student-modal").addEventListener("hidden.bs.modal", () => {
  changedPoints = {};
});

savePointsButton.addEventListener("click", async () => {
  hideError("student-error");
  savePointsButton.disabled = true;
  document.getElementById("points-status").textContent = "Saving...";
  try {
    const response = await apiFetch(`/api/submissions/${detail.id}/points`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ points: changedPoints }),
    });
    if (!response) return;
    const data = await response.json();
    if (!response.ok) {
      showError("student-error", data.error || "Could not save the scores.");
      savePointsButton.disabled = false;
      document.getElementById("points-status").textContent = "";
      return;
    }
    changedPoints = {};
    await openStudent(openStudentId, data.detail.attempt);
    document.getElementById("points-status").textContent = "Scores saved";
    loadResults();
  } catch {
    showError("student-error", "Cannot reach the server. Check your connection.");
    savePointsButton.disabled = false;
  }
});

// --- Paper score ---------------------------------------------------------------------

let possiblePoints = 0; // the sheet's total points (the highest paper score)
let editingPaper = null; // the paper attempt being edited, or null when adding one
const paperForm = document.getElementById("paper-form");

function showPaperForm(paper = null) {
  editingPaper = paper;
  document.getElementById("paper-form-title").textContent = paper ? "Edit paper score" : "Paper score";
  document.getElementById("paper-score").max = possiblePoints;
  document.getElementById("paper-possible").textContent = `/ ${possiblePoints}`;
  document.getElementById("paper-score").value = paper ? paper.score.total.earned : "";
  document.getElementById("paper-late").checked = paper ? paper.late : false;
  document.getElementById("paper-note").value = paper ? paper.note : "";
  document.getElementById("paper-delete").classList.toggle("d-none", !paper);
  paperForm.classList.remove("d-none");
  document.getElementById("paper-score").focus();
}

function hidePaperForm() {
  paperForm.classList.add("d-none");
  editingPaper = null;
}

document.getElementById("paper-button").addEventListener("click", () => showPaperForm());
document.getElementById("paper-cancel").addEventListener("click", hidePaperForm);

// Sends a paper score change; on success shows the student again and refreshes the table.
async function sendPaper(url, method, body) {
  hideError("student-error");
  try {
    const response = await apiFetch(url, {
      method,
      headers: { "Content-Type": "application/json" },
      body: body ? JSON.stringify(body) : undefined,
    });
    if (!response) return;
    const data = await response.json();
    if (!response.ok) {
      showError("student-error", data.error || "Could not save the paper score.");
      return;
    }
    renderStudent(data);
    loadResults();
  } catch {
    showError("student-error", "Cannot reach the server. Check your connection.");
  }
}

paperForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const value = document.getElementById("paper-score").value;
  if (value === "") {
    showError("student-error", "Type the total score from the paper.");
    return;
  }
  const body = {
    score: Number(value),
    late: document.getElementById("paper-late").checked,
    note: document.getElementById("paper-note").value.trim(),
  };
  if (editingPaper) await sendPaper(`/api/submissions/${editingPaper.id}/paper`, "PUT", body);
  else await sendPaper(`/api/assignments/${assignmentId}/students/${openStudentId}/paper`, "POST", body);
});

document.getElementById("paper-delete").addEventListener("click", () => {
  if (editingPaper) sendPaper(`/api/submissions/${editingPaper.id}/paper`, "DELETE");
});

// --- Give another try ------------------------------------------------------------------

document.getElementById("reopen-button").addEventListener("click", () => {
  document.getElementById("reopen-confirm").classList.remove("d-none");
});
document.getElementById("reopen-no").addEventListener("click", () => {
  document.getElementById("reopen-confirm").classList.add("d-none");
});
document.getElementById("reopen-yes").addEventListener("click", async (event) => {
  event.target.disabled = true;
  hideError("student-error");
  try {
    const response = await apiFetch(`/api/assignments/${assignmentId}/students/${openStudentId}/reopen`,
      { method: "POST" });
    if (!response) return;
    const data = await response.json();
    if (!response.ok) {
      showError("student-error", data.error || "Could not reopen.");
      return;
    }
    renderStudent(data);
    loadResults();
  } catch {
    showError("student-error", "Cannot reach the server. Check your connection.");
  } finally {
    event.target.disabled = false;
  }
});

loadResults();
