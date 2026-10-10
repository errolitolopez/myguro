// Student answer page: shows the sheet section by section, saves answers automatically
// while the student works, and submits. After submitting, the answers are shown read-only
// with the score (short answers wait for the teacher). If the activity allows more
// submissions, Try again starts the next attempt with the same answers; the latest counts.

const assignmentId = document.querySelector("main").dataset.assignmentId;
let activity = null;
let answers = {}; // question id -> answer (choice index, true/false, text, or a list per blank)
let changedIds = new Set(); // questions changed since the last save
let saveTimer = null;
let saving = null; // the save request in progress, if any

const LETTERS = "ABCDEF";
const BLANK = /_{3,}/g;
const SAVE_DELAY = 800; // ms after the last change

const saveStatus = document.getElementById("save-status");
const submitModal = bootstrap.Modal.getOrCreateInstance(document.getElementById("submit-modal"));

function el(tag, className = "", text = "") {
  const element = document.createElement(tag);
  if (className) element.className = className;
  if (text) element.textContent = text;
  return element;
}

function isAnswered(value) {
  if (value === null || value === undefined) return false;
  if (typeof value === "string") return value.trim() !== "";
  if (Array.isArray(value)) return value.some((item) => item.trim() !== "");
  return true; // a choice index or true/false
}

function allQuestions() {
  return activity.sections.flatMap((section) => section.questions);
}

function showProgress() {
  const questions = allQuestions();
  const answered = questions.filter((question) => isAnswered(answers[question.id])).length;
  document.getElementById("progress").textContent = `${answered} of ${questions.length} answered`;
}

// --- Saving as they go -------------------------------------------------------------

function setAnswer(questionId, value) {
  answers[questionId] = value;
  changedIds.add(questionId);
  showProgress();
  saveStatus.textContent = "Not saved yet...";
  clearTimeout(saveTimer);
  saveTimer = setTimeout(saveAnswers, SAVE_DELAY);
}

// Sends only the changed answers. Empty answers are sent as null (removes them).
async function saveAnswers() {
  clearTimeout(saveTimer);
  if (changedIds.size === 0) return true;
  if (saving) await saving; // one save at a time
  const sending = {};
  for (const id of changedIds) sending[id] = isAnswered(answers[id]) ? answers[id] : null;
  changedIds = new Set();
  saveStatus.textContent = "Saving...";

  saving = (async () => {
    try {
      const response = await apiFetch(`/api/my-activities/${assignmentId}/answers`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ answers: sending }),
        keepalive: true, // still sent if the page is closing
      });
      if (!response) return false;
      if (!response.ok) {
        const data = await response.json();
        saveStatus.textContent = data.error || "Could not save.";
        return false;
      }
      saveStatus.textContent = "All answers saved";
      return true;
    } catch {
      // Try again with the next change; keep these answers marked as not saved.
      Object.keys(sending).forEach((id) => changedIds.add(Number(id)));
      saveStatus.textContent = "Not saved — check your connection";
      return false;
    }
  })();
  const ok = await saving;
  saving = null;
  return ok;
}

// Save right away when the student leaves the page or switches apps (common on phones).
document.addEventListener("visibilitychange", () => {
  if (document.visibilityState === "hidden") saveAnswers();
});
window.addEventListener("beforeunload", (event) => {
  if (changedIds.size > 0) {
    saveAnswers();
    event.preventDefault();
  }
});

// --- Questions -----------------------------------------------------------------------

function choiceQuestion(question, options, locked) {
  const group = el("div", "mt-2");
  options.forEach(([value, label], index) => {
    const row = el("div", "form-check");
    const radio = el("input", "form-check-input");
    radio.type = "radio";
    radio.name = `q-${question.id}`;
    radio.id = `q-${question.id}-${index}`;
    radio.checked = answers[question.id] === value;
    radio.disabled = locked;
    radio.addEventListener("change", () => setAnswer(question.id, value));
    const text = el("label", "form-check-label", label);
    text.htmlFor = radio.id;
    row.append(radio, text);
    group.append(row);
  });
  return group;
}

function questionItem(question, locked) {
  const item = el("li", "mb-4");
  const points = el("span", "small text-body-secondary", ` (${plural(question.points, "pt", "pts")})`);

  if (question.type === "fill_blank") {
    // The sentence with a text box for each ___.
    const sentence = el("div", "lh-lg");
    const value = Array.isArray(answers[question.id]) ? [...answers[question.id]]
      : Array(question.blanks).fill("");
    question.prompt.split(BLANK).forEach((part, index) => {
      if (index > 0) {
        const blank = el("input", "form-control form-control-sm blank-input mx-1");
        blank.value = value[index - 1] || "";
        blank.disabled = locked;
        blank.maxLength = 200;
        blank.setAttribute("aria-label", `Blank ${index}`);
        blank.addEventListener("input", () => {
          value[index - 1] = blank.value;
          setAnswer(question.id, [...value]);
        });
        sentence.append(blank);
      }
      sentence.append(el("span", "preserve-lines", part));
    });
    sentence.append(points);
    item.append(sentence);
    return item;
  }

  const prompt = el("div", "preserve-lines", question.prompt);
  prompt.append(points);
  item.append(prompt);

  if (question.type === "multiple_choice") {
    item.append(choiceQuestion(question,
      question.choices.map((choice, index) => [index, `${LETTERS[index]}. ${choice}`]), locked));
  } else if (question.type === "true_false") {
    item.append(choiceQuestion(question, [[true, "True"], [false, "False"]], locked));
  } else {
    const short = question.type === "short_answer";
    const input = el(short ? "textarea" : "input", "form-control mt-2");
    input.value = answers[question.id] || "";
    input.disabled = locked;
    input.maxLength = short ? 5000 : 200;
    input.placeholder = short ? "Write your answer here..." : "Your answer";
    input.setAttribute("aria-label", "Your answer");
    if (short) input.rows = 4;
    input.addEventListener("input", () => setAnswer(question.id, input.value));
    item.append(input);
  }
  return item;
}

// --- The sheet ------------------------------------------------------------------------

function sectionBlock(section, locked) {
  if (section.kind === "text") {
    const block = el("section");
    if (section.title) block.append(el("h2", "h5", section.title));
    if (section.description) {
      const text = el("div", "preserve-lines");
      showDescription(text, section);
      block.append(text);
    }
    return block;
  }

  const card = el("section", "card");
  const body = el("div", "card-body");
  const header = el("div", "d-flex justify-content-between align-items-start gap-2");
  header.append(el("h2", "h5", section.title || "Activity"));
  // Section scores only on the submitted (read-only) sheet, not while trying again.
  const score = activity.submitted_at && activity.score && activity.score.sections[section.id];
  if (score) {
    const text = `${score.earned} / ${score.possible - score.pending}` +
      (score.pending ? ` (+${score.pending} to check)` : "");
    header.append(el("span", "badge text-bg-success text-nowrap", text));
  }
  body.append(header);
  if (section.description) {
    const text = el("div", "preserve-lines fst-italic");
    showDescription(text, section);
    body.append(text);
  }
  const list = el("ol", "mb-0 ps-3");
  section.questions.forEach((question) => list.append(questionItem(question, locked)));
  body.append(list);
  card.append(body);
  return card;
}

// "Attempt 2 of 3", "Attempt 2 (unlimited)"
function attemptText() {
  return activity.max_attempts === null
    ? `Attempt ${activity.attempt} (no limit)` : `Attempt ${activity.attempt} of ${activity.max_attempts}`;
}

function scoreText(total) {
  return `${total.earned} / ${total.possible - total.pending} points`;
}

function showResult() {
  const card = document.getElementById("result-card");
  const banner = document.getElementById("retry-banner");
  // Working on another attempt: remind them of the score that counts now.
  banner.classList.toggle("d-none", Boolean(activity.submitted_at) || !activity.score);
  if (!activity.submitted_at && activity.score) {
    banner.textContent = `${attemptText()}. Your last submitted score: ${scoreText(activity.score.total)}. ` +
      "Submitting again replaces it — your latest submission counts.";
  }
  if (!activity.submitted_at) {
    card.classList.add("d-none");
    return;
  }
  card.classList.remove("d-none");
  const total = activity.score && activity.score.total;
  // The score stays hidden until the teacher releases the scores.
  document.getElementById("result-label").textContent = total ? "Your score" : "Submitted";
  document.getElementById("result-score").textContent = total ? scoreText(total) : "Score not released yet";
  document.getElementById("result-note").textContent = !total
    ? "Your teacher will show the scores when everyone is done."
    : activity.paper
      ? "Scored by your teacher from your paper." + (activity.note ? ` ${activity.note}` : "")
      : total.pending
        ? `${plural(total.pending, "more point")} from short answers: waiting for your teacher to check.`
        : "Everything is checked.";
  document.getElementById("result-late").classList.toggle("d-none", !activity.late);

  const triesLeft = activity.max_attempts === null ? null : activity.max_attempts - activity.attempt;
  document.getElementById("result-attempts").textContent = activity.max_attempts === 1 ? ""
    : activity.can_retry
      ? `${attemptText()} · ${triesLeft === null ? "you can try again" : `${plural(triesLeft, "try", "tries")} left`}`
      : `${attemptText()} · no tries left`;
  document.getElementById("retry-button").classList.toggle("d-none", !activity.can_retry);
}

function render() {
  const locked = Boolean(activity.submitted_at);
  document.title = `${activity.title} · myguro`;
  document.getElementById("activity-title").textContent = activity.title;
  document.getElementById("activity-details").textContent =
    [activity.subject, activity.class_name, activity.teacher].filter(Boolean).join(" · ");
  document.getElementById("activity-due").textContent = activity.due_date
    ? `Due ${formatDay(activity.due_date)}` : "";

  showResult();
  // A paper score has no answers here: show the sheet only for reference, collapsed.
  const sectionsArea = document.getElementById("sections");
  sectionsArea.replaceChildren(...activity.sections.map((section) => sectionBlock(section, locked)));
  sectionsArea.classList.toggle("d-none", locked && activity.paper);
  document.querySelectorAll("#sections textarea").forEach((textarea) => {
    textarea.style.height = "auto";
    textarea.style.height = `${Math.max(textarea.scrollHeight + 2, 100)}px`;
  });

  // The bottom bar is only for answering.
  const hasQuestions = allQuestions().length > 0;
  document.getElementById("answer-bar").classList.toggle("d-none", locked || !hasQuestions);
  if (!locked) {
    showProgress();
    saveStatus.textContent = Object.keys(answers).length ? "All answers saved" : "";
  }
}

async function loadActivity() {
  try {
    const response = await apiFetch(`/api/my-activities/${assignmentId}`);
    if (!response) return;
    if (response.status === 404) {
      window.location.href = "/my-activities";
      return;
    }
    if (!response.ok) {
      showError("answer-error", "Could not load the activity.");
      return;
    }
    activity = (await response.json()).activity;
    answers = activity.answers;
    render();
  } catch {
    showError("answer-error", "Cannot reach the server. Check your connection.");
  }
}

// --- Submit -----------------------------------------------------------------------------

document.getElementById("submit-button").addEventListener("click", () => {
  const unanswered = allQuestions().filter((question) => !isAnswered(answers[question.id])).length;
  const warning = document.getElementById("submit-warning");
  const triesAfter = activity.max_attempts === null ? null : activity.max_attempts - activity.attempt;
  document.getElementById("submit-note").textContent = triesAfter === 0
    ? "This is your last try: you can't change your answers after submitting."
    : `After submitting you can still try again (${triesAfter === null ? "no limit" : plural(triesAfter, "more try", "more tries")}); your latest submission counts.`;
  warning.textContent = unanswered
    ? `${plural(unanswered, "question")} ${unanswered === 1 ? "has" : "have"} no answer yet.` : "";
  warning.classList.toggle("d-none", !unanswered);
  submitModal.show();
});

document.getElementById("confirm-submit-button").addEventListener("click", async (event) => {
  event.target.disabled = true;
  hideError("answer-error");
  clearTimeout(saveTimer);
  if (saving) await saving;
  const sending = {};
  for (const question of allQuestions()) {
    sending[question.id] = isAnswered(answers[question.id]) ? answers[question.id] : null;
  }
  try {
    const response = await apiFetch(`/api/my-activities/${assignmentId}/submit`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ answers: sending }),
    });
    if (!response) return;
    const data = await response.json();
    submitModal.hide();
    if (!response.ok) {
      showError("answer-error", data.error || "Could not submit.");
      window.scrollTo({ top: 0 });
      return;
    }
    changedIds = new Set();
    activity = data.activity;
    answers = activity.answers;
    render();
    window.scrollTo({ top: 0, behavior: "smooth" });
  } catch {
    submitModal.hide();
    showError("answer-error", "Cannot reach the server. Your answers are kept here; try again.");
  } finally {
    event.target.disabled = false;
  }
});

// --- Try again ---------------------------------------------------------------------------

document.getElementById("retry-button").addEventListener("click", async (event) => {
  event.target.disabled = true;
  hideError("answer-error");
  try {
    const response = await apiFetch(`/api/my-activities/${assignmentId}/retry`, { method: "POST" });
    if (!response) return;
    const data = await response.json();
    if (!response.ok) {
      showError("answer-error", data.error || "Could not start again.");
      return;
    }
    activity = data.activity;
    answers = activity.answers;
    render();
    window.scrollTo({ top: 0, behavior: "smooth" });
  } catch {
    showError("answer-error", "Cannot reach the server. Check your connection.");
  } finally {
    event.target.disabled = false;
  }
});

loadActivity();
