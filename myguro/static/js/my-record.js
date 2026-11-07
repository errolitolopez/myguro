// Student: their record. One card per teacher and subject, a row per activity with the score, and the
// subject's average. Only scores the teacher released are here (the server leaves the others out).

const subjectsBox = document.getElementById("subjects");
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

// The big ring with the overall average, and how many activities are done and late.
function renderOverview(record) {
  const stats = document.createElement("div");
  stats.append(
    statLine(`${record.done} / ${record.given}`, t("activities done")),
    statLine(record.late, t("submitted late")),
  );
  const average = record.average === null ? emptyAverage() : scoreRing(record.average, 100);
  overviewBox.replaceChildren(average, stats);
}

// emptyAverage() -> a small "-" in place of the ring, while nothing is scored yet
function emptyAverage() {
  const none = document.createElement("div");
  none.className = "text-body-secondary fs-4";
  none.textContent = "-";
  none.title = t("No scores yet");
  return none;
}

// What the right side of a row says: the score, or why there is none.
function scoreCell(activity) {
  const cell = document.createElement("div");
  cell.className = "d-flex flex-column align-items-end gap-1 text-nowrap";
  if (activity.score) {
    const checked = activity.score.possible - activity.score.pending;
    cell.append(badge("text-bg-success", `${activity.score.earned} / ${checked}`));
    if (activity.score.pending) cell.append(badge("text-bg-light border", t("+{pending} pts to check", { pending: activity.score.pending })));
  } else if (activity.done) {
    cell.append(badge("text-bg-light border", t("Score not released yet")));
  } else if (activity.status === "in_progress") {
    cell.append(badge("text-bg-info", t("In progress")));
  } else {
    cell.append(badge("text-bg-light border", t("Not started yet")));
  }
  if (activity.paper) cell.append(badge("text-bg-secondary", t("Paper")));
  if (activity.late) cell.append(badge("text-bg-warning", t("Late")));
  if (activity.closed && !activity.done) cell.append(badge("text-bg-dark", t("Closed")));
  return cell;
}

function activityRow(activity) {
  const row = document.createElement("a");
  row.href = `/my-activities/${activity.id}`;
  row.className = "list-group-item list-group-item-action d-flex justify-content-between align-items-center gap-2";

  const left = document.createElement("div");
  const title = document.createElement("div");
  title.className = "fw-semibold";
  title.textContent = activity.title;
  const details = document.createElement("div");
  details.className = "small text-body-secondary";
  details.textContent = [activity.class_name, activity.due_date ? t("Due {day}", { day: formatDay(activity.due_date) }) : ""]
    .filter(Boolean).join(" · ");
  left.append(title, details);

  const right = document.createElement("div");
  right.className = "d-flex align-items-center gap-2";
  if (activity.percent !== null) right.append(scoreRing(activity.percent, 100, true));
  right.append(scoreCell(activity));

  row.append(left, right);
  return row;
}

// One card per teacher and subject, built like every card: an icon title and one badge in the header,
// the list of rows last.
function subjectCard(subject, index) {
  const card = document.createElement("section");
  card.className = "card mb-3";
  card.setAttribute("aria-labelledby", `subject-title-${index}`);

  const header = document.createElement("div");
  header.className = "card-header d-flex justify-content-between align-items-center gap-2";
  const title = document.createElement("span");
  title.id = `subject-title-${index}`;
  title.className = "fw-semibold bi bi-book";
  title.textContent = ` ${subject.subject || t("No subject")} · ${subject.teacher}`;
  header.append(title, badge("text-bg-success", subject.average === null ? t("No average yet") : t("Average {percent}%", { percent: subject.average })));

  const rows = document.createElement("div");
  rows.className = "list-group list-group-flush";
  rows.append(...subject.activities.map(activityRow));

  card.append(header, rows);
  return card;
}

function renderRecord(record) {
  renderOverview(record);
  if (record.subjects.length === 0) {
    const empty = document.createElement("div");
    empty.className = "alert alert-light border";
    empty.textContent = t("Nothing has been given to you yet.");
    subjectsBox.replaceChildren(empty);
    return;
  }
  subjectsBox.replaceChildren(...record.subjects.map(subjectCard));
}

async function loadRecord() {
  try {
    const response = await apiFetch("/api/my-record");
    if (!response) return;
    if (!response.ok) {
      showError("record-error", t("Could not load your record."));
      return;
    }
    hideError("record-error");
    renderRecord((await response.json()).record);
  } catch {
    showError("record-error", t("Cannot reach the server. Check your connection."));
  }
}

loadRecord();
