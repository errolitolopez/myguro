// Teacher's learning activity sheets: first the subjects, tap one to open its page with the
// activities of that subject (tap one to edit), and start new ones.

let activities = []; // all of the teacher's sheets; the search filters them here

const list = document.getElementById("activity-list");
const searchInput = document.getElementById("search");
const modalElement = document.getElementById("new-activity-modal");
const form = document.getElementById("new-activity-form");
const titleInput = document.getElementById("new-title");
const subjectInput = document.getElementById("new-subject");
const createButton = document.getElementById("new-activity-button");
const newSubjectPicker = subjectPicker(subjectInput);

// "2026-10-10 07:17:40" (UTC, from SQLite) -> "Oct 10, 2026" in the viewer's time zone
function formatDate(value) {
  return new Date(value.replace(" ", "T") + "Z").toLocaleDateString(undefined, {
    month: "short", day: "numeric", year: "numeric",
  });
}

const STATUS_LABELS = { not_started: "not started", open: "open", closed: "closed" };

// statusBadge("Rizal · open", "open") -> a green badge; closed is dark, not started is grey
function statusBadge(text, status) {
  const badge = document.createElement("span");
  badge.className = `badge ${status === "open" ? "text-bg-success" : status === "closed" ? "text-bg-dark" : "text-bg-secondary"}`;
  badge.textContent = text;
  return badge;
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

  // Under the details: where the sheet is given, a badge per class or group with its status, or
  // "Not given yet". Only the school year being viewed is listed.
  const givenTo = document.createElement("div");
  givenTo.className = "d-flex flex-wrap gap-1 mt-1";
  if (activity.given_to.length === 0) {
    givenTo.append(statusBadge("Not given yet", "not_started"));
  } else {
    givenTo.append(...activity.given_to.map((given) => statusBadge(`${given.name} · ${STATUS_LABELS[given.status]}`, given.status)));
  }
  left.append(givenTo);

  row.append(left);
  return row;
}

function messageItem(text) {
  const box = document.createElement("div");
  box.className = "list-group";
  const div = document.createElement("div");
  div.className = "list-group-item text-body-secondary";
  div.textContent = text;
  box.append(div);
  return box;
}

// A plain list of activity rows.
function activityListElement(items) {
  const box = document.createElement("div");
  box.className = "list-group";
  box.append(...items.map(activityItem));
  return box;
}

function render() {
  const query = searchInput.value.trim().toLowerCase();
  const subject = chosenSubject(); // null = the list of subjects
  const matches = activities.filter(
    (activity) => activity.title.toLowerCase().includes(query) || activity.subject.toLowerCase().includes(query),
  );
  if (activities.length === 0) {
    list.replaceChildren(messageItem("No activities yet. Tap + New activity to write your first one."));
  } else if (subject !== null) {
    // One subject's page: its activities (the search narrows them)
    const inSubject = matches.filter((activity) => subjectKey(activity.subject) === subject);
    const label = groupBySubject(activities).find((group) => group.key === subject)?.label || "No subject";
    list.replaceChildren(subjectHeaderElement(label),
      inSubject.length ? activityListElement(inSubject) : messageItem("No activity matches your search."));
  } else if (query) {
    // Searching on the subjects page lists the matches from every subject
    list.replaceChildren(matches.length ? activityListElement(matches) : messageItem("No activity matches your search."));
  } else {
    list.replaceChildren(subjectListElement(groupBySubject(activities)));
  }
}

// --- Deleted sheets ----------------------------------------------------------------------

const deletedToggle = document.getElementById("deleted-toggle");
const deletedList = document.getElementById("deleted-list");
let deletedActivities = [];

// One deleted sheet with a Restore button. A restored sheet comes back with its assignments not started.
function deletedItem(activity) {
  const row = document.createElement("div");
  row.className = "list-group-item d-flex justify-content-between align-items-center gap-2";
  const left = document.createElement("div");
  const title = document.createElement("div");
  title.className = "fw-semibold";
  title.textContent = activity.title;
  const details = document.createElement("div");
  details.className = "small text-body-secondary";
  details.textContent = [activity.subject, `deleted ${formatDate(activity.deleted_at)}`].filter(Boolean).join(" · ");
  left.append(title, details);

  const button = document.createElement("button");
  button.type = "button";
  button.className = "btn btn-sm btn-outline-primary text-nowrap bi bi-arrow-counterclockwise";
  button.textContent = "Restore";
  button.addEventListener("click", async () => {
    const stopLoading = startLoading(button);
    if (!stopLoading) return;
    hideError("activities-error");
    try {
      const response = await apiFetch(`/api/activities/${activity.id}/restore`, { method: "POST" });
      if (!response) return;
      if (!response.ok) {
        showError("activities-error", (await response.json()).error || "Could not restore the activity.");
        return;
      }
      await loadActivities();
    } catch {
      showError("activities-error", "Cannot reach the server. Check your connection.");
    } finally {
      stopLoading();
    }
  });
  row.append(left, button);
  return row;
}

function renderDeleted() {
  deletedToggle.classList.toggle("d-none", deletedActivities.length === 0);
  deletedToggle.textContent = `Deleted (${deletedActivities.length})`;
  if (deletedActivities.length === 0) deletedList.classList.add("d-none");
  deletedList.replaceChildren(...deletedActivities.map(deletedItem));
}

deletedToggle.addEventListener("click", () => {
  const open = deletedList.classList.toggle("d-none") === false;
  deletedToggle.setAttribute("aria-expanded", String(open));
});

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
    const deleted = await apiFetch("/api/activities?deleted=1");
    if (deleted && deleted.ok) {
      deletedActivities = (await deleted.json()).activities;
      renderDeleted();
    }
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
  if (!subjectInput.value.trim()) {
    showError("new-activity-error", "Subject is required.");
    subjectInput.focus();
    return;
  }

  const stopLoading = startLoading(createButton);
  if (!stopLoading) return;
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
    stopLoading();
  }
});

modalElement.addEventListener("show.bs.modal", () => {
  form.reset();
  newSubjectPicker.sync();
  hideError("new-activity-error");
});
modalElement.addEventListener("shown.bs.modal", () => titleInput.focus());

loadActivities();
