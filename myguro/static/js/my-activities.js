// Student: the activities given to them. "To do" (never submitted, soonest due first) and
// "Submitted" (with the score that counts: the latest submission). Tapping one opens it.

let activities = [];
let today = "";

const list = document.getElementById("activity-list");

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
    if (activity.status === "in_progress") add("text-bg-info", `Trying again · attempt ${activity.attempt}`);
    else if (activity.can_retry) add("text-bg-light border", "Can try again");
    return badges;
  }
  if (activity.overdue) add("text-bg-danger", `Overdue · was due ${formatDay(activity.due_date)}`);
  else if (activity.due_date === today) add("text-bg-warning", "Due today");
  else if (activity.due_date) add("text-bg-light border", `Due ${formatDay(activity.due_date)}`);
  if (activity.status === "in_progress") add("text-bg-info", "In progress");
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

function render() {
  const showDone = document.getElementById("show-done").checked;
  // Once submitted it stays under Submitted, even while trying again.
  const todo = activities.filter((activity) => !activity.done);
  const done = activities.filter((activity) => activity.done);
  document.getElementById("count-todo").textContent = `(${todo.length})`;
  document.getElementById("count-done").textContent = `(${done.length})`;

  const shown = showDone ? done : todo;
  if (shown.length === 0) {
    const empty = document.createElement("div");
    empty.className = "list-group-item text-body-secondary";
    empty.textContent = showDone ? "Nothing submitted yet." : "Nothing to do. Great job!";
    list.replaceChildren(empty);
  } else {
    list.replaceChildren(...shown.map(activityItem));
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

document.querySelectorAll('input[name="show"]').forEach((radio) => radio.addEventListener("change", render));

loadActivities();
