// Student: the activities given to them. "To do" (never submitted, soonest due first) and
// "Submitted" (with the score that counts: the latest submission). First the subjects, grouped by
// teacher; tap one to open its page with that teacher's activities of that subject. Tapping an activity opens it.

let activities = [];
let today = "";

const list = document.getElementById("activity-list");

// progressText({answered: 3, questions: 10}) -> "3 / 10 answered"
function progressText(activity) {
  return t("{answered} / {questions} answered", { answered: activity.answered, questions: activity.questions });
}

// The badge on the right: due date / overdue, or the score once submitted.
function statusBadges(activity) {
  const badges = document.createElement("div");
  badges.className = "d-flex flex-column align-items-end gap-1 text-nowrap";
  const add = (className, text) => {
    const badge = document.createElement("span");
    badge.className = `badge ${className}`;
    badge.textContent = text;
    badges.append(badge);
  };

  if (activity.closed) add("text-bg-dark", t("Closed"));
  if (activity.done) {
    const score = activity.score;
    if (score) {
      add("text-bg-success", `${score.earned} / ${score.possible - score.pending}`);
      if (score.pending) add("text-bg-light border", t("+{pending} pts to check", { pending: score.pending }));
    } else {
      add("text-bg-success", t("Submitted"));
      add("text-bg-light border", t("Score not released yet"));
    }
    if (activity.paper) add("text-bg-secondary", t("Paper"));
    if (activity.late) add("text-bg-warning", t("Late"));
    if (activity.status === "in_progress") add("text-bg-info", t("Trying again · attempt {attempt} · {progress}", { attempt: activity.attempt, progress: progressText(activity) }));
    else if (activity.can_retry) add("text-bg-light border", t("Can try again"));
    return badges;
  }
  if (activity.overdue) add("text-bg-danger", t("Overdue · was due {day}", { day: formatDay(activity.due_date) }));
  else if (activity.due_date === today) add("text-bg-warning", t("Due today"));
  else if (activity.due_date) add("text-bg-light border", t("Due {day}", { day: formatDay(activity.due_date) }));
  if (activity.status === "in_progress") add("text-bg-info", t("In progress · {progress}", { progress: progressText(activity) }));
  else add("text-bg-light border", t("Not started yet"));
  return badges;
}

function activityItem(activity) {
  const row = document.createElement("a");
  row.href = `/my-activities/${activity.id}`;
  row.className = "list-group-item list-group-item-action d-flex justify-content-between align-items-start gap-2";

  const left = document.createElement("div");
  const title = document.createElement("div");
  title.className = "fw-semibold";
  title.textContent = activity.title;
  const details = document.createElement("div");
  details.className = "small text-body-secondary";
  details.textContent = [activity.subject, activity.class_name, activity.teacher].filter(Boolean).join(" · ");
  left.append(title, details);

  // A small ring with the percent once the score is released and there is something checked.
  const right = document.createElement("div");
  right.className = "d-flex align-items-center gap-2";
  const score = activity.done && activity.score;
  if (score && score.possible - score.pending > 0) {
    right.append(scoreRing(score.earned, score.possible - score.pending, true));
  }
  right.append(statusBadges(activity));

  row.append(left, right);
  return row;
}

// The teacher in the address (?teacher=3), or null. Two teachers can teach a subject with the same name,
// so a subject is always opened for one teacher.
function chosenTeacher() {
  const value = new URLSearchParams(window.location.search).get("teacher");
  return value === null ? null : Number(value);
}

// The subjects grouped by teacher: a heading with the teacher's name, then that teacher's subjects.
// Tapping a subject opens ?subject=...&teacher=<id> (showQuery keeps the To do / Submitted choice).
function teacherGroupsElement(items, showQuery) {
  const teachers = new Map();
  items.forEach((item) => {
    if (!teachers.has(item.teacher_id)) teachers.set(item.teacher_id, { name: item.teacher, items: [] });
    teachers.get(item.teacher_id).items.push(item);
  });
  const box = document.createElement("div");
  [...teachers.entries()].sort((a, b) => a[1].name.localeCompare(b[1].name)).forEach(([id, teacher]) => {
    const heading = document.createElement("h2");
    heading.className = "h6 text-body-secondary mt-3 mb-2 bi bi-person";
    heading.textContent = ` ${teacher.name}`;
    box.append(heading, subjectListElement(groupBySubject(teacher.items), `${showQuery}&teacher=${id}`));
  });
  return box;
}

// The subject's name as the first activity wrote it ("No subject" when it has none), with the teacher.
function subjectLabel(key, teacherId) {
  const mine = activities.filter((activity) => activity.teacher_id === teacherId);
  const label = groupBySubject(mine).find((group) => group.key === key)?.label || t("No subject");
  return `${label} · ${mine[0] ? mine[0].teacher : ""}`;
}

// isTodo(activity) -> true when there is still something to answer: never submitted, or trying again
function isTodo(activity) {
  return !activity.done || activity.status === "in_progress";
}

function render() {
  const showDone = document.getElementById("show-done").checked;
  // Once submitted it is under Submitted; Try again moves it back to To do until it is submitted again.
  const subject = chosenSubject(); // null = the list of subjects
  const teacher = chosenTeacher();
  const inSubject = activities.filter((activity) => subject === null
    || (subjectKey(activity.subject) === subject && (teacher === null || activity.teacher_id === teacher)));
  const todo = inSubject.filter(isTodo);
  const done = inSubject.filter((activity) => !isTodo(activity));
  document.getElementById("count-todo").textContent = `(${todo.length})`;
  document.getElementById("count-done").textContent = `(${done.length})`;

  const shown = showDone ? done : todo;
  // The page address keeps the To do / Submitted choice when a subject is opened or closed.
  const extraQuery = showDone ? "&show=done" : "";
  if (shown.length === 0) {
    const box = document.createElement("div");
    box.className = "list-group";
    const empty = document.createElement("div");
    empty.className = "list-group-item text-body-secondary";
    empty.textContent = showDone ? t("Nothing submitted yet.") : t("Nothing to do. Great job!");
    box.append(empty);
    list.replaceChildren(...(subject === null ? [] : [subjectHeaderElement(subjectLabel(subject, teacher), extraQuery)]), box);
  } else if (subject === null) {
    list.replaceChildren(teacherGroupsElement(shown, extraQuery));
  } else {
    const rows = document.createElement("div");
    rows.className = "list-group";
    rows.append(...shown.map(activityItem));
    list.replaceChildren(subjectHeaderElement(subjectLabel(subject, teacher), extraQuery), rows);
  }
}

async function loadActivities() {
  try {
    const response = await apiFetch("/api/my-activities");
    if (!response) return;
    if (!response.ok) {
      showError("list-error", t("Could not load your activities."));
      return;
    }
    hideError("list-error");
    const data = await response.json();
    activities = data.activities;
    today = data.today;
    render();
  } catch {
    showError("list-error", t("Cannot reach the server. Check your connection."));
  }
}

// Keep the To do / Submitted choice in the address, so the back link and reload remember it.
document.querySelectorAll('input[name="show"]').forEach((radio) => radio.addEventListener("change", () => {
  const params = new URLSearchParams(window.location.search);
  if (document.getElementById("show-done").checked) params.set("show", "done");
  else params.delete("show");
  history.replaceState(null, "", params.toString() ? `?${params}` : window.location.pathname);
  render();
}));
document.getElementById("show-done").checked = new URLSearchParams(window.location.search).get("show") === "done";
document.getElementById("show-todo").checked = !document.getElementById("show-done").checked;

loadActivities();
