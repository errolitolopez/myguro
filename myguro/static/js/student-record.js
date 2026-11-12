// Teacher: one student's record. An overview, then a card per class with a row per activity the teacher
// gave this student: the score that counts (released or not), its percent and badges. Tapping a row opens
// the checking page once the student worked on it, else the activity's results.

const studentId = Number(document.querySelector("main").dataset.studentId);
const classesBox = document.getElementById("classes");
const overviewBox = document.getElementById("overview");

// badge("text-bg-warning", "Late") -> <span class="badge text-bg-warning">Late</span>
function badge(className, text) {
  const element = document.createElement("span");
  element.className = `badge ${className}`;
  element.textContent = text;
  return element;
}

// statLine(5, "done") -> <div><strong>5</strong> done</div>
function statLine(value, label) {
  const line = document.createElement("div");
  const strong = document.createElement("strong");
  strong.textContent = value;
  line.append(strong, ` ${label}`);
  return line;
}

// emptyAverage() -> a small "-" in place of the ring, while nothing is scored yet
function emptyAverage() {
  const none = document.createElement("div");
  none.className = "text-body-secondary fs-4";
  none.textContent = "-";
  none.title = t("No scores yet");
  return none;
}

// The big ring with the average, then done of given, late and points still to check.
function renderOverview(record) {
  const stats = document.createElement("div");
  stats.append(
    statLine(`${record.done} / ${record.given}`, t("activities done")),
    statLine(record.late, t("submitted late")),
  );
  if (record.to_check) stats.append(statLine(record.to_check, t("points to check")));
  overviewBox.replaceChildren(record.average === null ? emptyAverage() : scoreRing(record.average, 100), stats);
}

// What the right side of a row says: the score, or why there is none.
function scoreCell(activity) {
  const cell = document.createElement("div");
  cell.className = "d-flex flex-column align-items-end gap-1 text-nowrap";
  if (activity.excluded) {
    cell.append(badge("text-bg-secondary", t("Excluded")));
  } else if (activity.score) {
    const checked = activity.score.possible - activity.score.pending;
    cell.append(badge("text-bg-success", `${activity.score.earned} / ${checked}`));
    if (activity.score.pending) cell.append(badge("text-bg-light border", t("+{pending} pts to check", { pending: activity.score.pending })));
    if (!activity.scores_released) cell.append(badge("text-bg-light border", t("Not released")));
  } else if (activity.status === "in_progress") {
    cell.append(badge("text-bg-info", t("Answering")));
  } else {
    cell.append(badge("text-bg-light border", t("Not started")));
  }
  if (activity.paper) cell.append(badge("text-bg-secondary", t("Paper")));
  if (activity.late) cell.append(badge("text-bg-warning", t("Late")));
  return cell;
}

function activityRow(activity) {
  const row = document.createElement("a");
  // The checking page needs an attempt; before that the results page is the useful one.
  row.href = activity.status === "not_started" || activity.excluded
    ? `/results/${activity.assignment_id}`
    : `/results/${activity.assignment_id}/students/${studentId}`;
  row.className = "list-group-item list-group-item-action d-flex justify-content-between align-items-center gap-2";

  const left = document.createElement("div");
  const title = document.createElement("div");
  title.className = "fw-semibold";
  title.textContent = activity.title;
  const details = document.createElement("div");
  details.className = "small text-body-secondary";
  details.textContent = activity.due_date ? t("Due {day}", { day: formatDay(activity.due_date) }) : "";
  left.append(title, details);

  const right = document.createElement("div");
  right.className = "d-flex align-items-center gap-2";
  if (activity.percent !== null && !activity.excluded) right.append(scoreRing(activity.percent, 100, true));
  right.append(scoreCell(activity));

  row.append(left, right);
  return row;
}

// One card per class (or the individual students group): the class in the header with its average, the
// rows last, like every card.
function classCard(group, index) {
  const card = document.createElement("section");
  card.className = "card mb-3";
  card.setAttribute("aria-labelledby", `class-title-${index}`);

  const header = document.createElement("div");
  header.className = "card-header d-flex justify-content-between align-items-center gap-2";
  const title = document.createElement("span");
  title.id = `class-title-${index}`;
  title.className = "fw-semibold bi bi-mortarboard";
  title.textContent = ` ${group.class_name}`;
  header.append(title, badge("text-bg-success", group.average === null
    ? t("No average yet") : t("Average {percent}%", { percent: group.average })));

  const rows = document.createElement("div");
  rows.className = "list-group list-group-flush";
  rows.append(...group.activities.map(activityRow));

  card.append(header, rows);
  return card;
}

function render(data) {
  const student = data.student;
  document.getElementById("student-name").textContent = student.name;
  document.title = `${student.name} · MyGuro`;
  document.getElementById("student-details").textContent =
    [student.username, gradeSection(student)].filter(Boolean).join(" · ");
  renderOverview(data.record);
  if (data.record.classes.length === 0) {
    const empty = document.createElement("div");
    empty.className = "alert alert-light border";
    empty.textContent = t("You have not given this student an activity yet.");
    classesBox.replaceChildren(empty);
    return;
  }
  classesBox.replaceChildren(...data.record.classes.map(classCard));
}

// The page has nothing to show (not the teacher's student, or no connection): only the error stays.
function showNothing() {
  document.getElementById("student-details").textContent = "";
  overviewBox.closest("section").classList.add("d-none");
  classesBox.replaceChildren();
}

async function loadRecord() {
  try {
    const response = await apiFetch(`/api/my-students/${studentId}/record`);
    if (!response) return;
    if (!response.ok) {
      const body = await response.json().catch(() => ({}));
      showError("record-error", body.error || t("Could not load the record."));
      showNothing();
      return;
    }
    hideError("record-error");
    render(await response.json());
  } catch {
    showError("record-error", t("Cannot reach the server. Check your connection."));
    showNothing();
  }
}

loadRecord();
