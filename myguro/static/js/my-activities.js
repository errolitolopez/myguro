// Student: the activities given to them. "To do" (never submitted, soonest due first) and
// "Submitted" (with the score that counts: the latest submission). First the subjects; tap one
// to open its page with the activities of that subject. Tapping an activity opens it.

let activities = [];
let today = "";

const list = document.getElementById("activity-list");

// progressText({answered: 3, questions: 10}) -> "3 / 10 answered"
function progressText(activity) {
  return `${activity.answered} / ${activity.questions} answered`;
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

  if (activity.closed) add("text-bg-dark", "Closed");
  if (activity.done) {
    const score = activity.score;
    if (score) {
      add("text-bg-success", `${score.earned} / ${score.possible - score.pending}`);
      if (score.pending) add("text-bg-light border", `+${score.pending} pts to check`);
    } else {
      add("text-bg-success", "Submitted");
      add("text-bg-light border", "Score not released yet");
    }
    if (activity.paper) add("text-bg-secondary", "Paper");
    if (activity.late) add("text-bg-warning", "Late");
    if (activity.status === "in_progress") add("text-bg-info", `Trying again · attempt ${activity.attempt} · ${progressText(activity)}`);
    else if (activity.can_retry) add("text-bg-light border", "Can try again");
    return badges;
  }
  if (activity.overdue) add("text-bg-danger", `Overdue · was due ${formatDay(activity.due_date)}`);
  else if (activity.due_date === today) add("text-bg-warning", "Due today");
  else if (activity.due_date) add("text-bg-light border", `Due ${formatDay(activity.due_date)}`);
  if (activity.status === "in_progress") add("text-bg-info", `In progress · ${progressText(activity)}`);
  else add("text-bg-light border", "Not started yet");
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

  row.append(left, statusBadges(activity));
  return row;
}

// The subject's name as the first activity wrote it ("No subject" when it has none).
function subjectLabel(key) {
  return groupBySubject(activities).find((group) => group.key === key)?.label || "No subject";
}

function render() {
  const showDone = document.getElementById("show-done").checked;
  // Once submitted it stays under Submitted, even while trying again.
  const subject = chosenSubject(); // null = the list of subjects
  const inSubject = activities.filter((activity) => subject === null || subjectKey(activity.subject) === subject);
  const todo = inSubject.filter((activity) => !activity.done);
  const done = inSubject.filter((activity) => activity.done);
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
    empty.textContent = showDone ? "Nothing submitted yet." : "Nothing to do. Great job!";
    box.append(empty);
    list.replaceChildren(...(subject === null ? [] : [subjectHeaderElement(subjectLabel(subject), extraQuery)]), box);
  } else if (subject === null) {
    list.replaceChildren(subjectListElement(groupBySubject(shown), extraQuery));
  } else {
    const rows = document.createElement("div");
    rows.className = "list-group";
    rows.append(...shown.map(activityItem));
    list.replaceChildren(subjectHeaderElement(subjectLabel(subject), extraQuery), rows);
  }
}

async function loadActivities() {
  try {
    const response = await apiFetch("/api/my-activities");
    if (!response) return;
    if (!response.ok) {
      showError("list-error", "Could not load your activities.");
      return;
    }
    hideError("list-error");
    const data = await response.json();
    activities = data.activities;
    today = data.today;
    render();
  } catch {
    showError("list-error", "Cannot reach the server. Check your connection.");
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
