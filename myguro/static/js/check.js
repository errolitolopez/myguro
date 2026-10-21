// Checking one student's answers, for the teacher (its own page, opened from the results table).
// Answers sit next to the answer key; the teacher scores short answers or changes any question's
// points, then goes on to the next student of the same list. A student who answered on paper
// gets a paper score (a total typed by the teacher).

const assignmentId = document.querySelector("main").dataset.assignmentId;
const studentId = Number(document.querySelector("main").dataset.studentId);
let detail = null; // the attempt shown
let changedPoints = {}; // question id -> new points, not saved yet
let changedFeedback = {}; // question id -> new remark, not saved yet
let neighbours = { previous: null, next: null }; // student ids to check before and after this one

// The results page's search and filter, so "Next student" follows the list the teacher came from.
const listParams = new URLSearchParams(window.location.search);

const LETTERS = "ABCDEFGHIJKL";
const savePointsButton = document.getElementById("save-points-button");
const nextButton = document.getElementById("next-button");
const previousButton = document.getElementById("previous-button");

// The results page with the same search and filter.
document.getElementById("back-link").href = `/results/${assignmentId}` +
  (listParams.toString() ? `?${listParams}` : "");

function el(tag, className = "", text = "") {
  const element = document.createElement(tag);
  if (className) element.className = className;
  if (text !== "") element.textContent = text;
  return element;
}

// --- Order of students ---------------------------------------------------------------

// The students the teacher can check, in the order of the results table and with the same
// search and filter: only those who submitted (a paper score counts too), not excluded ones.
function checkable(results) {
  const query = (listParams.get("q") || "").toLowerCase();
  const filter = listParams.get("filter") || "all";
  return results.students.filter((student) => {
    if (student.id === studentId) return true; // the student on screen stays in the list
    if (student.excluded || student.score === null) return false;
    if (query && !student.name.toLowerCase().includes(query) && !student.username.includes(query)) return false;
    if (filter === "to_check") return student.score.pending > 0;
    if (filter === "late") return student.late;
    if (filter === "not_submitted") return false; // nothing to check there
    return true;
  });
}

// Link to a student's checking page, with the same search and filter.
function studentUrl(id) {
  return `/results/${assignmentId}/students/${id}` + (listParams.toString() ? `?${listParams}` : "");
}

// "Student 3 of 12" and the Previous / Next buttons.
async function loadOrder() {
  try {
    const response = await apiFetch(`/api/assignments/${assignmentId}/results`);
    if (!response || !response.ok) return;
    const list = checkable(await response.json());
    const index = list.findIndex((student) => student.id === studentId);
    neighbours = {
      previous: index > 0 ? list[index - 1].id : null,
      next: index >= 0 && index < list.length - 1 ? list[index + 1].id : null,
    };
    document.getElementById("position").textContent =
      index >= 0 ? `Student ${index + 1} of ${list.length}` : "";
    previousButton.disabled = neighbours.previous === null;
    nextButton.disabled = neighbours.next === null;
    nextButton.title = neighbours.next === null ? "This is the last student of the list." : "";
  } catch {
    // The page still works without the order: only the Previous / Next buttons stay off.
  }
}

// Goes to another student; the typed scores are saved first so nothing is lost.
async function goTo(id) {
  if (id === null) return;
  if (!(await savePoints())) return;
  window.location.href = studentUrl(id);
}

previousButton.addEventListener("click", async (event) => {
  const stopLoading = startLoading(event.currentTarget);
  if (!stopLoading) return;
  await goTo(neighbours.previous);
  stopLoading();
});
nextButton.addEventListener("click", async (event) => {
  const stopLoading = startLoading(event.currentTarget);
  if (!stopLoading) return;
  await goTo(neighbours.next);
  stopLoading();
});

// --- One student ---------------------------------------------------------------------

// The student's answer, written out: "B. Hinduism", "True", "India, Japan", ...
function answerText(question, value) {
  if (value === null || value === undefined) return null;
  if (question.type === "multiple_choice") return `${LETTERS[value]}. ${question.choices[value]}`;
  if (question.type === "true_false") return value ? "True" : "False";
  if (question.type === "fill_blank") return value.map((item, index) => `${index + 1}) ${item || "—"}`).join("   ");
  if (question.type === "matching") return matchText(question, value);
  return value;
}

// Matching, written out: "Hinduism → B. India", one line per Column A item.
function matchText(question, picks) {
  return picks.map((pick, index) =>
    `${question.answer[index].item} → ${pick === null ? "—" : `${LETTERS[pick]}. ${question.choices[pick]}`}`)
    .join("\n");
}

// The answer key, written out.
function keyText(question) {
  if (question.type === "multiple_choice") return `${LETTERS[question.answer]}. ${question.choices[question.answer]}`;
  if (question.type === "true_false") return question.answer ? "True" : "False";
  if (question.type === "identification") return question.answer.join(" / ");
  if (question.type === "fill_blank") {
    return question.answer.map((accepted, index) => `${index + 1}) ${accepted.join(" / ")}`).join("   ");
  }
  if (question.type === "matching") return matchText(question, question.answer.map((pair) => pair.match));
  return question.answer; // short answer: the guide (may be empty)
}

// true when a score or a remark was typed and not saved yet
function hasUnsaved() {
  return Object.keys(changedPoints).length > 0 || Object.keys(changedFeedback).length > 0;
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

  // The teacher's remark on this answer. The student sees it once the scores are released.
  if (editable) {
    const remark = el("textarea", "form-control form-control-sm mt-2");
    remark.rows = 2;
    remark.maxLength = 1000;
    remark.value = question.feedback || "";
    remark.placeholder = "Remark for the student (optional)";
    remark.setAttribute("aria-label", `Remark for question ${number}`);
    remark.addEventListener("input", () => {
      changedFeedback[question.id] = remark.value;
      savePointsButton.disabled = false;
      document.getElementById("points-status").textContent = "Unsaved scores";
    });
    item.append(remark);
  } else if (question.feedback) {
    item.append(el("div", "small mt-2 preserve-lines", `Remark: ${question.feedback}`));
  }
  return item;
}

function renderStudent(data) {
  const student = data.student;
  detail = data.detail;
  possiblePoints = data.possible;
  hidePaperForm();
  changedPoints = {};
  changedFeedback = {};
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
    button.addEventListener("click", () => openAttempt(attempt.attempt));
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

async function loadStudent(attempt) {
  hideError("student-error");
  try {
    const query = attempt ? `?attempt=${attempt}` : "";
    const response = await apiFetch(`/api/assignments/${assignmentId}/students/${studentId}${query}`);
    if (!response) return false;
    if (response.status === 404) {
      window.location.href = `/results/${assignmentId}`;
      return false;
    }
    const data = await response.json();
    if (!response.ok) {
      showError("student-error", data.error || "Could not load the answers.");
      return false;
    }
    renderStudent(data);
    return true;
  } catch {
    showError("student-error", "Cannot reach the server. Check your connection.");
    return false;
  }
}

// Another attempt of the same student: ask first when there are unsaved scores.
function openAttempt(attempt) {
  if (hasUnsaved()) {
    document.getElementById("points-status").textContent = "Save the scores first.";
    return;
  }
  loadStudent(attempt);
}

// Leaving the page drops unsaved scores: let the browser ask first.
window.addEventListener("beforeunload", (event) => {
  if (hasUnsaved()) event.preventDefault();
});

// Saves the typed scores. Returns true when they are saved (or there was nothing to save).
async function savePoints() {
  if (!hasUnsaved()) return true;
  hideError("student-error");
  savePointsButton.disabled = true;
  document.getElementById("points-status").textContent = "Saving...";
  try {
    const response = await apiFetch(`/api/submissions/${detail.id}/points`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ points: changedPoints, feedback: changedFeedback }),
    });
    if (!response) return false;
    const data = await response.json();
    if (!response.ok) {
      showError("student-error", data.error || "Could not save the scores.");
      savePointsButton.disabled = false;
      document.getElementById("points-status").textContent = "";
      return false;
    }
    changedPoints = {};
    changedFeedback = {};
    await loadStudent(data.detail.attempt);
    document.getElementById("points-status").textContent = "Scores saved";
    loadOrder();
    return true;
  } catch {
    showError("student-error", "Cannot reach the server. Check your connection.");
    savePointsButton.disabled = false;
    return false;
  }
}

savePointsButton.addEventListener("click", async (event) => {
  const stopLoading = startLoading(event.currentTarget);
  if (!stopLoading) return;
  await savePoints();
  stopLoading();
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
    loadOrder();
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
  else await sendPaper(`/api/assignments/${assignmentId}/students/${studentId}/paper`, "POST", body);
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
  const stopLoading = startLoading(event.currentTarget);
  if (!stopLoading) return;
  hideError("student-error");
  try {
    const response = await apiFetch(`/api/assignments/${assignmentId}/students/${studentId}/reopen`,
      { method: "POST" });
    if (!response) return;
    const data = await response.json();
    if (!response.ok) {
      showError("student-error", data.error || "Could not reopen.");
      return;
    }
    renderStudent(data);
    loadOrder();
  } catch {
    showError("student-error", "Cannot reach the server. Check your connection.");
  } finally {
    stopLoading();
  }
});

loadStudent().then(() => loadOrder());
