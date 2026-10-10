// Activity sheet editor (teacher). The sheet is a list of sections, each either
//   text:     a title + description (for reading, e.g. "VI. Let's Learn"), or
//   activity: a title + directions + questions (e.g. "III. Pre-test").
// Questions: multiple choice, true or false, identification, fill in the blank (each with its
// answer key), and short answer (a short essay the teacher scores; optional guide), with points. Nothing is sent until Save; leaving with unsaved changes asks first.

const activityId = document.querySelector("main").dataset.activityId;
let sections = []; // the sheet as edited here (see fromServer / toServer)
let unsaved = false;
let nextKey = 1; // gives every question a unique key for its radio button names

const titleInput = document.getElementById("activity-title");
const subjectInput = document.getElementById("activity-subject");
const sectionList = document.getElementById("section-list");
const saveButton = document.getElementById("save-button");
const saveStatus = document.getElementById("save-status");

const QUESTION_TYPES = {
  multiple_choice: "Multiple choice",
  true_false: "True or False",
  identification: "Identification",
  fill_blank: "Fill in the blank",
  short_answer: "Short answer",
};
// Short answers are worth more than a one-word item by default.
const DEFAULT_POINTS = { short_answer: 5 };
const LETTERS = "ABCDEF";
const MAX_CHOICES = 6;
const BLANK = /_{3,}/g; // ___ (three or more underscores) marks a blank

// --- Small helpers ---------------------------------------------------------------

// el("div", "card", "text") -> <div class="card">text</div>. textContent, so no HTML injection.
function el(tag, className = "", text = "") {
  const element = document.createElement(tag);
  if (className) element.className = className;
  if (text) element.textContent = text;
  return element;
}

// Textareas grow with their text so long descriptions don't need scrolling inside a small box.
function fitHeight(textarea) {
  textarea.style.height = "auto";
  textarea.style.height = `${textarea.scrollHeight + 2}px`;
}

function smallButton(label, title, onClick, disabled = false) {
  const button = el("button", "btn btn-sm btn-outline-secondary", label);
  button.type = "button";
  button.title = title;
  button.setAttribute("aria-label", title);
  button.disabled = disabled;
  button.addEventListener("click", onClick);
  return button;
}

// ↑ ↓ ✕ buttons for an item in a list (sections, or questions in a section).
function moveButtons(list, index, what) {
  const group = el("div", "btn-group");
  group.append(
    smallButton("↑", `Move ${what} up`, () => move(list, index, -1), index === 0),
    smallButton("↓", `Move ${what} down`, () => move(list, index, 1), index === list.length - 1),
    smallButton("✕", `Delete ${what}`, () => {
      list.splice(index, 1);
      changed();
    }),
  );
  return group;
}

function move(list, index, step) {
  const [item] = list.splice(index, 1);
  list.splice(index + step, 0, item);
  changed();
}

// A labelled text box. onInput gets the new value.
function textField(id, label, value, placeholder, onInput, { multiline = false, maxLength = 150 } = {}) {
  const wrapper = el("div", "mb-2");
  const labelElement = el("label", "form-label small mb-1", label);
  labelElement.htmlFor = id;
  const input = el(multiline ? "textarea" : "input", "form-control");
  input.id = id;
  input.maxLength = maxLength;
  input.placeholder = placeholder;
  input.value = value;
  if (multiline) input.rows = 2;
  input.addEventListener("input", () => {
    onInput(input.value);
    if (multiline) fitHeight(input);
    markUnsaved();
  });
  wrapper.append(labelElement, input);
  return wrapper;
}

// --- Unsaved changes -----------------------------------------------------------

function markUnsaved() {
  unsaved = true;
  saveButton.disabled = false;
  saveStatus.textContent = "Unsaved changes";
  saveStatus.className = "small text-warning-emphasis fw-semibold";
  showTotals();
}

function markSaved() {
  unsaved = false;
  saveButton.disabled = true;
  saveStatus.textContent = "All changes saved";
  saveStatus.className = "small text-body-secondary";
  showTotals();
}

// Something was added, moved or deleted: draw the sections again.
function changed() {
  markUnsaved();
  render();
}

// The browser asks "Leave site?" when there are unsaved changes.
window.addEventListener("beforeunload", (event) => {
  if (unsaved) event.preventDefault();
});

titleInput.addEventListener("input", markUnsaved);
subjectInput.addEventListener("input", markUnsaved);

// The error box is at the top of the page and Save is at the bottom, so scroll to it.
function showEditorError(message) {
  showError("editor-error", message);
  document.getElementById("editor-error").scrollIntoView({ behavior: "smooth", block: "center" });
}

// "12 questions · 15 points"
function showTotals() {
  const questions = sections.flatMap((section) => (section.kind === "activity" ? section.questions : []));
  const points = questions.reduce((sum, question) => sum + (parseInt(question.points, 10) || 0), 0);
  document.getElementById("totals").textContent = questions.length
    ? `${plural(questions.length, "question")} · ${plural(points, "point")}`
    : "";
}

// --- Converting between the server and the editor --------------------------------
// Accepted answers are typed in one box separated by "/" ("Taoism / Daoism");
// the server keeps them as a list.

function splitAnswers(text) {
  return text.split("/").map((answer) => answer.trim()).filter(Boolean);
}

function newQuestion(type) {
  const question = { key: nextKey++, type, prompt: "", points: DEFAULT_POINTS[type] || 1 };
  if (type === "multiple_choice") {
    question.choices = ["", "", "", ""];
    question.answer = null;
  } else if (type === "true_false") {
    question.answer = null;
  } else if (type === "identification" || type === "short_answer") {
    question.answerText = "";
  } else {
    question.blankAnswers = [];
  }
  return question;
}

function fromServer(section) {
  return {
    id: section.id,
    kind: section.kind,
    title: section.title,
    description: section.description,
    questions: section.questions.map((question) => {
      const edited = { ...newQuestion(question.type), id: question.id, prompt: question.prompt,
        points: question.points };
      if (question.type === "multiple_choice") {
        edited.choices = question.choices;
        edited.answer = question.answer;
      } else if (question.type === "true_false") {
        edited.answer = question.answer;
      } else if (question.type === "identification") {
        edited.answerText = question.answer.join(" / ");
      } else if (question.type === "short_answer") {
        edited.answerText = question.answer;
      } else {
        edited.blankAnswers = question.answer.map((answers) => answers.join(" / "));
      }
      return edited;
    }),
  };
}

function toServer(section) {
  return {
    id: section.id,
    kind: section.kind,
    title: section.title.trim(),
    description: section.description.trim(),
    questions: section.kind === "text" ? [] : section.questions.map((question) => {
      const sent = { id: question.id, type: question.type, prompt: question.prompt,
        points: Number(question.points) };
      if (question.type === "multiple_choice") {
        sent.choices = question.choices;
        sent.answer = question.answer;
      } else if (question.type === "true_false") {
        sent.answer = question.answer;
      } else if (question.type === "identification") {
        sent.answer = splitAnswers(question.answerText);
      } else if (question.type === "short_answer") {
        sent.answer = question.answerText.trim();
      } else {
        // One list of accepted answers per blank (an answer box left empty sends []).
        sent.answer = Array.from({ length: blankCount(question.prompt) },
          (_, index) => splitAnswers(question.blankAnswers[index] || ""));
      }
      return sent;
    }),
  };
}

function blankCount(text) {
  return (text.match(BLANK) || []).length;
}

// --- Questions -------------------------------------------------------------------

function multipleChoiceFields(question, id) {
  const wrapper = el("div", "mb-2");
  wrapper.append(el("div", "form-label small mb-1", "Choices (tap the circle of the correct answer)"));

  question.choices.forEach((choice, index) => {
    const row = el("div", "input-group input-group-sm mb-1");

    const radioBox = el("span", "input-group-text");
    const radio = el("input", "form-check-input mt-0");
    radio.type = "radio";
    radio.name = `correct-${question.key}`;
    radio.checked = question.answer === index;
    radio.setAttribute("aria-label", `Choice ${LETTERS[index]} is correct`);
    radio.addEventListener("change", () => {
      question.answer = index;
      markUnsaved();
    });
    radioBox.append(radio);

    const input = el("input", "form-control");
    input.id = `${id}-choice-${index}`;
    input.maxLength = 200;
    input.placeholder = `Choice ${LETTERS[index]}`;
    input.value = choice;
    input.addEventListener("input", () => {
      question.choices[index] = input.value;
      markUnsaved();
    });

    const remove = smallButton("✕", `Remove choice ${LETTERS[index]}`, () => {
      question.choices.splice(index, 1);
      if (question.answer === index) question.answer = null;
      else if (question.answer > index) question.answer -= 1;
      changed();
    }, question.choices.length <= 2);

    row.append(radioBox, el("span", "input-group-text", LETTERS[index]), input, remove);
    wrapper.append(row);
  });

  if (question.choices.length < MAX_CHOICES) {
    const add = el("button", "btn btn-sm btn-link px-0", "+ Add choice");
    add.type = "button";
    add.addEventListener("click", () => {
      question.choices.push("");
      changed();
      document.getElementById(`${id}-choice-${question.choices.length - 1}`).focus();
    });
    wrapper.append(add);
  }
  return wrapper;
}

function trueFalseFields(question) {
  const wrapper = el("div", "mb-2");
  wrapper.append(el("div", "form-label small mb-1", "Correct answer"));
  const group = el("div", "btn-group");
  group.setAttribute("role", "group");
  for (const [value, label] of [[true, "True"], [false, "False"]]) {
    const radio = el("input", "btn-check");
    radio.type = "radio";
    radio.name = `correct-${question.key}`;
    radio.id = `tf-${question.key}-${label}`;
    radio.checked = question.answer === value;
    radio.addEventListener("change", () => {
      question.answer = value;
      markUnsaved();
    });
    const button = el("label", "btn btn-sm btn-outline-success", label);
    button.htmlFor = radio.id;
    group.append(radio, button);
  }
  wrapper.append(group);
  return wrapper;
}

const ANSWER_HINT = "Accept other answers too: separate them with /";

function identificationFields(question, id) {
  const field = textField(`${id}-answer`, "Correct answer", question.answerText, "Taoism / Daoism",
    (value) => (question.answerText = value), { maxLength: 500 });
  field.append(el("div", "form-text mt-0", `${ANSWER_HINT}. Capital letters don't matter.`));
  return field;
}

function shortAnswerFields(question, id) {
  const field = textField(`${id}-guide`, "Guide for checking (optional, only you see this)",
    question.answerText, "Key points to look for: chooses one question, explains why...",
    (value) => (question.answerText = value), { multiline: true, maxLength: 20000 });
  field.append(el("div", "form-text mt-0",
    "Students write their own answer. You read it and give a score from 0 to the points."));
  return field;
}

// One answer box per ___ in the question; redrawn when the number of blanks changes.
function blankAnswerFields(question, id, container) {
  const count = blankCount(question.prompt);
  container.replaceChildren();
  if (count === 0) {
    container.append(el("div", "form-text mb-2", "Type ___ (three underscores) in the question where each blank goes."));
    return;
  }
  for (let index = 0; index < count; index++) {
    container.append(textField(`${id}-blank-${index}`, `Blank ${index + 1} answer`,
      question.blankAnswers[index] || "", "India",
      (value) => (question.blankAnswers[index] = value), { maxLength: 500 }));
  }
  container.append(el("div", "form-text mt-0 mb-2", `${ANSWER_HINT}. Capital letters don't matter.`));
}

function questionCard(section, question, index) {
  const id = `q-${question.key}`;
  const card = el("div", "border rounded p-2 bg-body");

  const header = el("div", "d-flex justify-content-between align-items-center gap-2 mb-2");
  const label = el("span", "small fw-semibold", `${index + 1}. ${QUESTION_TYPES[question.type]}`);
  const right = el("div", "d-flex align-items-center gap-2");
  const points = el("input", "form-control form-control-sm text-end");
  points.type = "number";
  points.min = 1;
  points.max = 100;
  points.style.width = "4.5rem";
  points.value = question.points;
  points.setAttribute("aria-label", "Points");
  points.addEventListener("input", () => {
    question.points = points.value;
    markUnsaved();
  });
  right.append(points, el("span", "small text-body-secondary", "pts"),
    moveButtons(section.questions, index, "question"));
  header.append(label, right);
  card.append(header);

  const placeholders = {
    fill_blank: "Buddhism originated in ___.",
    short_answer: "Which of the four questions above is the MOST important? Explain why.",
  };
  const prompt = textField(`${id}-prompt`, "Question", question.prompt,
    placeholders[question.type] || "Which tradition originated in India?",
    (value) => (question.prompt = value), { multiline: true, maxLength: 20000 });
  card.append(prompt);

  if (question.type === "multiple_choice") {
    card.append(multipleChoiceFields(question, id));
  } else if (question.type === "true_false") {
    card.append(trueFalseFields(question));
  } else if (question.type === "identification") {
    card.append(identificationFields(question, id));
  } else if (question.type === "short_answer") {
    card.append(shortAnswerFields(question, id));
  } else {
    // Insert a blank at the cursor, then show one answer box per blank.
    const textarea = prompt.querySelector("textarea");
    const insert = el("button", "btn btn-sm btn-outline-secondary mb-2", "Insert blank ___");
    insert.type = "button";
    const answers = el("div");
    insert.addEventListener("click", () => {
      const start = textarea.selectionStart ?? textarea.value.length;
      textarea.setRangeText("___", start, textarea.selectionEnd ?? start, "end");
      textarea.dispatchEvent(new Event("input"));
      textarea.focus();
    });
    let blanks = blankCount(question.prompt);
    textarea.addEventListener("input", () => {
      if (blankCount(question.prompt) !== blanks) {
        blanks = blankCount(question.prompt);
        blankAnswerFields(question, id, answers);
      }
    });
    blankAnswerFields(question, id, answers);
    card.append(insert, answers);
  }
  return card;
}

// --- Sections --------------------------------------------------------------------

function sectionCard(section, index) {
  const activity = section.kind === "activity";
  const card = el("div", `card ${activity ? "border-primary-subtle" : ""}`);

  const header = el("div", "card-header d-flex justify-content-between align-items-center py-1");
  const label = el("span", "small fw-semibold text-body-secondary", `Section ${index + 1} · `);
  label.append(el("span", activity ? "text-primary" : "text-success", activity ? "Activity" : "Text"));
  header.append(label, moveButtons(sections, index, "section"));

  const body = el("div", "card-body");
  const id = `section-${index}`;
  body.append(textField(`${id}-title`, "Title", section.title,
    activity ? "III. Pre-test" : "I. Title of the Lesson", (value) => (section.title = value)));
  body.append(textField(`${id}-description`, activity ? "Directions (optional)" : "Description",
    section.description,
    activity ? "Read each item carefully and choose the letter of the correct answer."
      : "At the end of this lesson, you will be able to...",
    (value) => (section.description = value), { multiline: true, maxLength: 20000 }));

  if (activity) {
    const questions = el("div", "d-grid gap-2 my-3");
    section.questions.forEach((question, questionIndex) =>
      questions.append(questionCard(section, question, questionIndex)));
    if (section.questions.length === 0) {
      questions.append(el("div", "small text-body-secondary", "No questions yet. Add one below."));
    }
    body.append(questions);

    const addRow = el("div", "d-flex flex-wrap gap-1");
    for (const [type, name] of Object.entries(QUESTION_TYPES)) {
      const add = el("button", "btn btn-sm btn-outline-primary", `+ ${name}`);
      add.type = "button";
      add.addEventListener("click", () => {
        const question = newQuestion(type);
        section.questions.push(question);
        changed();
        document.getElementById(`q-${question.key}-prompt`).focus();
      });
      addRow.append(add);
    }
    body.append(addRow);
  }

  card.append(header, body);
  return card;
}

function render() {
  sectionList.replaceChildren(...sections.map(sectionCard));
  document.getElementById("no-sections").classList.toggle("d-none", sections.length > 0);
  sectionList.querySelectorAll("textarea").forEach(fitHeight);
  showTotals();
}

function addSection(kind) {
  sections.push({ kind, title: "", description: "", questions: [] });
  changed();
  document.getElementById(`section-${sections.length - 1}-title`).focus();
}

document.getElementById("add-text-button").addEventListener("click", () => addSection("text"));
document.getElementById("add-activity-button").addEventListener("click", () => addSection("activity"));

// --- Load and save ---------------------------------------------------------------

function showActivity(activity) {
  document.title = `${activity.title} · myguro`;
  titleInput.value = activity.title;
  subjectInput.value = activity.subject;
  const badge = document.getElementById("status-badge");
  badge.textContent = activity.status === "published" ? "Published" : "Draft";
  badge.className = activity.status === "published" ? "badge text-bg-success" : "badge text-bg-secondary";
  sections = activity.sections.map(fromServer);
  render();
}

async function loadActivity() {
  try {
    const response = await apiFetch(`/api/activities/${activityId}`);
    if (!response) return;
    if (response.status === 404) {
      window.location.href = "/activities";
      return;
    }
    if (!response.ok) {
      showEditorError("Could not load the activity.");
      return;
    }
    showActivity((await response.json()).activity);
    markSaved();
  } catch {
    showEditorError("Cannot reach the server. Check your connection.");
  }
}

async function save() {
  hideError("editor-error");
  if (!titleInput.value.trim()) {
    showEditorError("Title is required.");
    titleInput.focus();
    return;
  }

  saveButton.disabled = true;
  saveStatus.textContent = "Saving...";
  try {
    const response = await apiFetch(`/api/activities/${activityId}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        title: titleInput.value.trim(),
        subject: subjectInput.value.trim(),
        sections: sections.map(toServer),
      }),
    });
    if (!response) return;
    const data = await response.json();
    if (!response.ok) {
      showEditorError(data.error || "Could not save.");
      markUnsaved();
      return;
    }
    showActivity(data.activity);
    markSaved();
  } catch {
    showEditorError("Cannot reach the server. Check your connection.");
    markUnsaved();
  }
}

saveButton.addEventListener("click", save);

// Ctrl+S / Cmd+S saves instead of saving the web page.
document.addEventListener("keydown", (event) => {
  if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "s") {
    event.preventDefault();
    if (unsaved) save();
  }
});

// --- Preview -----------------------------------------------------------------------

// "Buddhism originated in ___." with each ___ drawn as a line, like on paper.
function withBlankLines(text) {
  const element = el("span", "preserve-lines");
  text.split(BLANK).forEach((part, index) => {
    if (index > 0) element.append(el("span", "blank-line"));
    element.append(part);
  });
  return element;
}

function previewQuestion(question) {
  const item = el("li", "mb-3");
  const prompt = el("div");
  prompt.append(question.type === "fill_blank" ? withBlankLines(question.prompt) : el("span", "preserve-lines", question.prompt));
  const points = parseInt(question.points, 10) || 0;
  prompt.append(el("span", "small text-body-secondary", ` (${plural(points, "pt", "pts")})`));
  item.append(prompt);

  if (question.type === "multiple_choice") {
    const choices = el("ol", "mb-0");
    choices.type = "A";
    question.choices.forEach((choice) => choices.append(el("li", "", choice)));
    item.append(choices);
  } else if (question.type === "true_false") {
    item.append(el("div", "text-body-secondary small", "○ True   ○ False"));
  } else if (question.type === "identification") {
    item.append(el("div", "blank-line mt-1"));
  } else if (question.type === "short_answer") {
    // An empty box with room for a few lines, like the "Answer: ____" lines on paper.
    const box = el("div", "border rounded mt-1 p-2 text-body-secondary small", "Answer:");
    box.style.minHeight = "5rem";
    item.append(box);
  }
  return item;
}

document.getElementById("preview-button").addEventListener("click", () => {
  document.getElementById("preview-title").textContent = titleInput.value.trim() || "(no title)";
  document.getElementById("preview-subject").textContent = subjectInput.value.trim();

  const body = document.getElementById("preview-body");
  body.replaceChildren();
  if (sections.length === 0) body.append(el("p", "text-body-secondary", "No sections yet."));
  for (const section of sections) {
    const block = el("section", "mb-4");
    if (section.title.trim()) block.append(el("h3", "h5", section.title.trim()));
    if (section.description.trim()) {
      const text = el("p", "preserve-lines", section.description.trim());
      if (section.kind === "activity") text.classList.add("fst-italic");
      block.append(text);
    }
    if (section.kind === "activity") {
      const list = el("ol");
      section.questions.forEach((question) => list.append(previewQuestion(question)));
      block.append(list);
    }
    body.append(block);
  }
  bootstrap.Modal.getOrCreateInstance(document.getElementById("preview-modal")).show();
});

// --- Delete --------------------------------------------------------------------------

const deleteConfirm = document.getElementById("delete-confirm");
document.getElementById("delete-button").addEventListener("click", () => deleteConfirm.classList.remove("d-none"));
document.getElementById("delete-no").addEventListener("click", () => deleteConfirm.classList.add("d-none"));
document.getElementById("delete-yes").addEventListener("click", async (event) => {
  event.target.disabled = true;
  try {
    const response = await apiFetch(`/api/activities/${activityId}`, { method: "DELETE" });
    if (!response) return;
    if (!response.ok) {
      const data = await response.json();
      showEditorError(data.error || "Could not delete the activity.");
      deleteConfirm.classList.add("d-none");
      return;
    }
    unsaved = false; // don't ask "Leave site?" after deleting
    window.location.href = "/activities";
  } catch {
    showEditorError("Cannot reach the server. Check your connection.");
  } finally {
    event.target.disabled = false;
  }
});

loadActivity();
