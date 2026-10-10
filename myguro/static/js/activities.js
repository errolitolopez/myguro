// Teacher's learning activity sheets: list them (tap to edit) and start new ones.

let activities = []; // all of the teacher's sheets; the search filters them here

const list = document.getElementById("activity-list");
const searchInput = document.getElementById("search");
const modalElement = document.getElementById("new-activity-modal");
const form = document.getElementById("new-activity-form");
const titleInput = document.getElementById("new-title");
const subjectInput = document.getElementById("new-subject");
const createButton = document.getElementById("new-activity-button");

// "2026-10-10 07:17:40" (UTC, from SQLite) -> "Oct 10, 2026" in the viewer's time zone
function formatDate(value) {
  return new Date(value.replace(" ", "T") + "Z").toLocaleDateString(undefined, {
    month: "short", day: "numeric", year: "numeric",
  });
}

function activityItem(activity) {
  const row = document.createElement("a");
  row.href = `/activities/${activity.id}`;
  row.className = "list-group-item list-group-item-action d-flex justify-content-between align-items-start gap-2";

  const left = document.createElement("div");
  const title = document.createElement("div");
  title.className = "fw-semibold";
  title.textContent = activity.title;
  const details = document.createElement("div");
  details.className = "small text-body-secondary";
  details.textContent = [
    activity.subject,
    plural(activity.sections, "section"),
    plural(activity.questions, "question"),
    `edited ${formatDate(activity.updated_at)}`,
  ].filter(Boolean).join(" · ");
  left.append(title, details);

  const badge = document.createElement("span");
  badge.className = activity.assigned ? "badge text-bg-primary" : "badge text-bg-secondary";
  badge.textContent = activity.assigned ? `Assigned · ${plural(activity.assigned, "class", "classes")}` : "Draft";

  row.append(left, badge);
  return row;
}

function messageItem(text) {
  const div = document.createElement("div");
  div.className = "list-group-item text-body-secondary";
  div.textContent = text;
  return div;
}

function render() {
  const query = searchInput.value.trim().toLowerCase();
  const shown = activities.filter(
    (activity) =>
      activity.title.toLowerCase().includes(query) || activity.subject.toLowerCase().includes(query),
  );
  if (activities.length === 0) {
    list.replaceChildren(messageItem("No activities yet. Tap + New activity to write your first one."));
  } else if (shown.length === 0) {
    list.replaceChildren(messageItem("No activity matches your search."));
  } else {
    list.replaceChildren(...shown.map(activityItem));
  }
}

async function loadActivities() {
  try {
    const response = await apiFetch("/api/activities");
    if (!response) return;
    if (!response.ok) {
      showError("activities-error", "Could not load your activities.");
      return;
    }
    hideError("activities-error");
    activities = (await response.json()).activities;
    render();
  } catch {
    showError("activities-error", "Cannot reach the server. Check your connection.");
  }
}

searchInput.addEventListener("input", render);

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  hideError("new-activity-error");
  const title = titleInput.value.trim();
  if (!title) {
    showError("new-activity-error", "Title is required.");
    titleInput.focus();
    return;
  }

  createButton.disabled = true;
  try {
    const response = await apiFetch("/api/activities", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ title, subject: subjectInput.value.trim() }),
    });
    if (!response) return;
    const data = await response.json();
    if (!response.ok) {
      showError("new-activity-error", data.error || "Could not create the activity.");
      return;
    }
    window.location.href = `/activities/${data.activity.id}`;
  } catch {
    showError("new-activity-error", "Cannot reach the server. Check your connection.");
  } finally {
    createButton.disabled = false;
  }
});

modalElement.addEventListener("show.bs.modal", () => {
  form.reset();
  hideError("new-activity-error");
});
modalElement.addEventListener("shown.bs.modal", () => titleInput.focus());

loadActivities();
