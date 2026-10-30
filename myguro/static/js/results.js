// Results of one assignment (a sheet given to a class), for the teacher: every student's
// status and score (in total and per activity section). Tapping a student opens the checking
// page (check.js), where the teacher scores answers and moves on to the next student.

const assignmentId = document.querySelector("main").dataset.assignmentId;
let results = null; // from /api/assignments/<id>/results

const STATUS = {
  not_started: [t("Not started"), "text-bg-light border"],
  in_progress: [t("Answering"), "text-bg-info"],
  submitted: [t("Submitted"), "text-bg-success"],
  excluded: [t("Excluded"), "text-bg-secondary"],
};

// The search and filter come back from the checking page's "Back to results" link.
const startParams = new URLSearchParams(window.location.search);
document.getElementById("search").value = startParams.get("q") || "";
const startFilter = startParams.get("filter");
if (startFilter && document.querySelector(`#filter option[value="${startFilter}"]`)) {
  document.getElementById("filter").value = startFilter;
}

function el(tag, className = "", text = "") {
  const element = document.createElement(tag);
  if (className) element.className = className;
  if (text !== "") element.textContent = text;
  return element;
}

// "4 / 6" (+ "+5 to check"), or "–"
function scoreCell(score) {
  const cell = el("td", "text-nowrap");
  if (!score) {
    cell.append(el("span", "text-body-secondary", "–"));
    return cell;
  }
  cell.append(el("span", "fw-semibold", `${score.earned} / ${score.possible - score.pending}`));
  if (score.pending) cell.append(el("div", "small text-warning-emphasis", t("+{pending} to check", { pending: score.pending })));
  return cell;
}

// Checking a student is its own page. The search and filter go along, so "Next student" there
// follows the same list the teacher sees here.
function openStudent(studentId) {
  const params = new URLSearchParams();
  const query = document.getElementById("search").value.trim();
  const filter = document.getElementById("filter").value;
  if (query) params.set("q", query);
  if (filter !== "all") params.set("filter", filter);
  const suffix = params.toString() ? `?${params}` : "";
  window.location.href = `/results/${assignmentId}/students/${studentId}${suffix}`;
}

// --- The table ----------------------------------------------------------------------

// excludeCell(student) -> the table cell with an "Exclude" button, or "Add back" for an excluded
// student. A student who already submitted has no button.
function excludeCell(student) {
  const cell = el("td", "text-end");
  if (!student.excluded && student.attempts > 0) return cell;
  const button = el("button",
    `btn btn-sm text-nowrap bi ${student.excluded ? "btn-outline-primary bi-person-plus" : "btn-outline-secondary bi-person-dash"}`,
    student.excluded ? t("Add back") : t("Exclude"));
  button.type = "button";
  // The row opens the checking page: keep a click or Enter on the button from doing that too.
  button.addEventListener("keydown", (event) => event.stopPropagation());
  button.addEventListener("click", async (event) => {
    event.stopPropagation();
    const stopLoading = startLoading(button);
    if (!stopLoading) return;
    hideError("results-error");
    try {
      const response = await apiFetch(`/api/assignments/${assignmentId}/students/${student.id}/excluded`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ excluded: !student.excluded }),
      });
      if (!response) return;
      if (!response.ok) {
        showError("results-error", (await response.json()).error || t("Could not save."));
        return;
      }
      await loadResults(); // the totals change too
    } catch {
      showError("results-error", t("Cannot reach the server. Check your connection."));
    } finally {
      stopLoading();
    }
  });
  cell.append(button);
  return cell;
}

function render() {
  const { assignment, sections, students, summary } = results;
  document.title = t("{title} · Results · MyGuro", { title: assignment.title });
  document.getElementById("results-title").textContent = assignment.title;
  document.getElementById("results-details").textContent = [
    assignment.class_name,
    assignment.due_date ? `due ${formatDay(assignment.due_date)}` : "no due date",
    assignment.max_attempts === null ? "unlimited submissions"
      : plural(assignment.max_attempts, "submission") + " allowed",
    summary.excluded ? `${plural(summary.excluded, "student")} excluded` : null,
  ].filter(Boolean).join(" · ");
  const back = document.getElementById("back-link");
  // A direct assignment has no class page: go back to the activities list.
  back.href = assignment.class_id === null ? "/activities" : `/classes/${assignment.class_id}`;
  back.textContent = assignment.class_id === null ? t("‹ Activities") : `‹ ${assignment.class_name}`;
  document.getElementById("edit-link").href = `/activities/${assignment.activity_id}`;

  // Not started / Open / Closed: students answer only while it is open for this class or group.
  const action = STATUS_ACTIONS[assignment.status];
  document.getElementById("open-button").textContent = action.label;
  document.getElementById("open-button").className = `btn btn-sm text-nowrap bi ${action.icon} ${action.className}`;
  document.getElementById("open-note").textContent = {
    not_started: t("Not started: students can't see this activity yet. Open it when they may answer."),
    open: t("Open: students can see and answer this activity."),
    closed: t("Closed: all work was submitted as it was. Students can only read the questions. ") +
      t("Re-open it to let unfinished students continue."),
  }[assignment.status];

  const released = assignment.scores_released;
  document.getElementById("release-button").textContent = released ? t("Hide scores") : t("Release scores");
  document.getElementById("release-button").className =
    `btn btn-sm text-nowrap ${released ? "btn-outline-secondary" : "btn-primary"}`;
  document.getElementById("release-note").textContent = released
    ? t("Students can see their scores.")
    : t("Students can't see their scores yet. Release them when everyone is done.");
  document.getElementById("stat-submitted").textContent = `${summary.submitted} / ${summary.students}`;
  document.getElementById("stat-not-started").textContent = summary.not_started;
  document.getElementById("stat-late").textContent = summary.late;
  document.getElementById("stat-average").textContent = summary.average === null ? "–" : `${summary.average}%`;
  document.getElementById("stat-average-ring").replaceChildren(
    ...(summary.average === null ? [] : [scoreRing(summary.average, 100, true)]));
  document.getElementById("stat-to-check").textContent = summary.to_check;

  const head = document.getElementById("results-head");
  head.replaceChildren(el("th", "", t("Student")), el("th", "", t("Status")), el("th", "", t("Score")),
    ...sections.map((section) => el("th", "small fw-normal", section.title)), el("th", "", t("Tries")),
    el("th", "visually-hidden", t("Actions")));

  const query = document.getElementById("search").value.trim().toLowerCase();
  const filter = document.getElementById("filter").value;
  const shown = students.filter((student) => {
    if (query && !student.name.toLowerCase().includes(query) && !student.username.includes(query)) return false;
    if (filter === "submitted") return student.score !== null;
    if (filter === "not_submitted") return student.score === null && !student.excluded;
    if (filter === "to_check") return student.score !== null && student.score.pending > 0;
    if (filter === "late") return student.late;
    return true;
  });

  const body = document.getElementById("results-body");
  if (shown.length === 0) {
    const row = el("tr");
    const cell = el("td", "text-body-secondary",
      students.length ? t("No student matches.") : t("No students in this assignment."));
    cell.colSpan = 5 + sections.length;
    row.append(cell);
    body.replaceChildren(row);
    return;
  }
  body.replaceChildren(...shown.map((student) => {
    const row = el("tr", student.excluded ? "text-body-secondary" : "");
    row.tabIndex = 0;
    row.addEventListener("click", () => openStudent(student.id));
    row.addEventListener("keydown", (event) => {
      if (event.key === "Enter") openStudent(student.id);
    });

    const name = el("td");
    name.append(el("div", "fw-semibold", student.name),
      el("div", "small text-body-secondary", gradeSection(student) || student.username));
    const status = el("td");
    const [label, style] = STATUS[student.status];
    status.append(el("span", `badge ${style}`, label));
    if (student.paper) status.append(" ", el("span", "badge text-bg-secondary", t("Paper")));
    if (student.late) status.append(" ", el("span", "badge text-bg-warning", t("Late")));

    // When they started and handed in; a close submits unfinished work, so then there is no real time spent
    if (student.started_at) status.append(el("div", "small text-body-secondary", t("Started {time}", { time: formatDateTime(student.started_at) })));
    if (student.submitted_at && !student.paper) {
      status.append(el("div", "small text-body-secondary", student.auto_submitted
        ? t("Submitted by close {time}", { time: formatDateTime(student.submitted_at) })
        : t("Submitted {time} · {duration}", { time: formatDateTime(student.submitted_at), duration: durationText(student.started_at, student.submitted_at) })));
    }

    row.append(name, status, scoreCell(student.score),
      ...sections.map((section) => scoreCell(student.section_scores[section.id])),
      el("td", "text-body-secondary", student.attempts ? String(student.attempts) : "–"),
      excludeCell(student));
    return row;
  }));
}

async function loadResults() {
  try {
    const response = await apiFetch(`/api/assignments/${assignmentId}/results`);
    if (!response) return;
    if (response.status === 404) {
      window.location.href = "/activities";
      return;
    }
    if (!response.ok) {
      showError("results-error", t("Could not load the results."));
      return;
    }
    hideError("results-error");
    results = await response.json();
    render();
  } catch {
    showError("results-error", t("Cannot reach the server. Check your connection."));
  }
}

document.getElementById("open-button").addEventListener("click", async (event) => {
  const stopLoading = startLoading(event.currentTarget);
  if (!stopLoading) return;
  hideError("results-error");
  try {
    const response = await putStatus(assignmentId, STATUS_ACTIONS[results.assignment.status].next,
      results.assignment.class_name);
    if (!response) return;
    if (!response.ok) {
      showError("results-error", (await response.json()).error || t("Could not save."));
      return;
    }
    await loadResults();  // a close or re-open changes the students' rows too
  } catch {
    showError("results-error", t("Cannot reach the server. Check your connection."));
  } finally {
    stopLoading();
  }
});

document.getElementById("release-button").addEventListener("click", async (event) => {
  const stopLoading = startLoading(event.currentTarget);
  if (!stopLoading) return;
  hideError("results-error");
  try {
    const response = await apiFetch(`/api/assignments/${assignmentId}/release`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ released: !results.assignment.scores_released }),
    });
    if (!response) return;
    if (!response.ok) {
      showError("results-error", (await response.json()).error || t("Could not save."));
      return;
    }
    results.assignment.scores_released = (await response.json()).scores_released;
    render();
  } catch {
    showError("results-error", t("Cannot reach the server. Check your connection."));
  } finally {
    stopLoading();
  }
});

document.getElementById("search").addEventListener("input", render);
document.getElementById("filter").addEventListener("change", render);

loadResults();
