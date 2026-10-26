// Loads the dashboard numbers. Admins see totals for the whole school;
// teachers see their own students, activities and classes; students see what is to do and submitted.

function setText(id, text) {
  const element = document.getElementById(id);
  if (element) element.textContent = text;
}

// Teachers' rows open the class page; students' rows are plain (activities come later).
function showClasses(classes, role) {
  const list = document.getElementById("class-list");
  list.replaceChildren();
  document.getElementById("no-classes").classList.toggle("d-none", classes.length > 0);

  for (const item of classes) {
    const row = document.createElement(role === "teacher" ? "a" : "div");
    row.className = "list-group-item";
    if (role === "teacher") {
      row.href = `/classes/${item.id}`;
      row.classList.add("list-group-item-action");
    }

    const name = document.createElement("div");
    name.className = "fw-semibold";
    name.textContent = classTitle(item);
    const details = document.createElement("div");
    details.className = "small text-body-secondary";
    details.textContent =
      role === "teacher"
        ? `${plural(item.students, "student")} · ${plural(item.activities, "activity", "activities")}`
        : `${item.teacher} · ${plural(item.activities, "activity", "activities")}`;

    row.append(name, details);
    list.append(row);
  }
}

const MAX_TO_CHECK_ROWS = 5;

// toCheckRow({title, class_name, submitted, students, to_check, id}) -> a row that opens the results
function toCheckRow(item) {
  const row = document.createElement("a");
  row.href = `/results/${item.id}`;
  row.className = "list-group-item list-group-item-action d-flex justify-content-between align-items-center gap-2";

  const left = document.createElement("div");
  const title = document.createElement("div");
  title.className = "fw-semibold";
  title.textContent = item.title;
  const details = document.createElement("div");
  details.className = "small text-body-secondary";
  details.textContent = `${item.class_name} · ${item.submitted} of ${plural(item.students, "student")} submitted`;
  left.append(title, details);

  const badge = document.createElement("span");
  badge.className = "badge text-bg-warning text-nowrap";
  badge.textContent = `${item.to_check} pts to check`;

  row.append(left, badge);
  return row;
}

// Fills the To check card with the activities that have points still to check (short answers the
// teacher has not scored), and the total of those points.
async function loadToCheck() {
  const list = document.getElementById("to-check-list");
  const total = document.getElementById("to-check-total");
  const message = (text) => {
    const item = document.createElement("div");
    item.className = "list-group-item small text-body-secondary";
    item.textContent = text;
    return item;
  };
  hideError("to-check-error");
  try {
    const response = await apiFetch("/api/results/to-check");
    if (!response) return;
    const data = await response.json();
    if (!response.ok) {
      list.replaceChildren();
      showError("to-check-error", data.error || "Could not load what to check.");
      return;
    }
    const waiting = data.assignments.filter((item) => item.to_check > 0);
    const points = waiting.reduce((sum, item) => sum + item.to_check, 0);
    total.textContent = `${points} pts`;
    total.classList.toggle("d-none", waiting.length === 0);
    if (waiting.length === 0) {
      list.replaceChildren(message("Nothing to check. You are all caught up."));
      return;
    }
    const rows = waiting.slice(0, MAX_TO_CHECK_ROWS).map(toCheckRow);
    if (waiting.length > MAX_TO_CHECK_ROWS) {
      rows.push(message(`And ${plural(waiting.length - MAX_TO_CHECK_ROWS, "more activity", "more activities")} to check.`));
    }
    list.replaceChildren(...rows);
  } catch {
    list.replaceChildren();
    showError("to-check-error", "Cannot reach the server. Check your connection.");
  }
}

async function loadDashboard() {
  hideError("dashboard-error");
  try {
    const response = await apiFetch("/api/dashboard");
    if (!response) return;
    const data = await response.json();
    if (!response.ok) {
      showError("dashboard-error", data.error || "Could not load the dashboard.");
      return;
    }

    if (data.role === "admin") {
      setText("stat-teachers", data.teachers);
      setText("stat-classes", data.classes);
      setText("stat-students", data.students);
      setText("stat-activities", data.activities);
      setText("stat-supervisors", data.supervisors);
    } else if (data.role === "student") {
      setText("stat-submitted", data.submitted);
      setText("stat-to-do", data.to_do);
    } else {
      setText("stat-students", data.students);
      setText("stat-not-started", data.not_started);
      setText("stat-open", data.open);
      setText("stat-closed", data.closed);
      setText("stat-submissions", data.submissions);
      showClasses(data.classes, "teacher");
    }
  } catch {
    showError("dashboard-error", "Cannot reach the server. Check your connection.");
  }
}

loadDashboard();
// Only the teacher dashboard has the To check card.
if (document.getElementById("to-check-card")) loadToCheck();
