// Attendance (teacher): pick a day, tap a mark for each student from the paper record, Save.

const classId = document.querySelector("main").dataset.classId;
const STATUS_LABELS = { present: "Present", late: "Late", absent: "Absent", excused: "Excused" };
// The colour of a chosen mark; the others stay outlined
const STATUS_COLORS = { present: "success", late: "warning", absent: "danger", excused: "info" };

let sheet = null; // from /api/classes/<id>/attendance
let marks = {}; // student id -> status or null, what is on screen (saved or not)

const dayInput = document.getElementById("day");
const list = document.getElementById("student-list");
const saveButton = document.getElementById("save-button");

// todayText() -> "2026-10-26" (this computer's day; the server checks it against the school's day)
const todayText = () => {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}-${String(now.getDate()).padStart(2, "0")}`;
};

// shiftDay("2026-10-26", -1) -> "2026-10-25"
const shiftDay = (isoDay, days) => {
  const [year, month, day] = isoDay.split("-").map(Number);
  const moved = new Date(year, month - 1, day + days);
  return `${moved.getFullYear()}-${String(moved.getMonth() + 1).padStart(2, "0")}-${String(moved.getDate()).padStart(2, "0")}`;
};

function el(tag, className = "", text = "") {
  const element = document.createElement(tag);
  if (className) element.className = className;
  if (text !== "") element.textContent = text;
  return element;
}

function studentRow(student) {
  const row = el("div", "list-group-item");
  const name = el("div", "fw-semibold", student.name);
  const totals = student.totals;
  const details = el("div", "small text-body-secondary mb-2", [
    gradeSection(student),
    `P ${totals.present} · L ${totals.late} · A ${totals.absent} · E ${totals.excused}`,
  ].filter(Boolean).join(" · "));

  const group = el("div", "btn-group w-100");
  group.setAttribute("role", "group");
  group.setAttribute("aria-label", `Attendance of ${student.name}`);
  sheet.statuses.forEach((status) => {
    const button = el("button", "btn btn-sm", STATUS_LABELS[status]);
    button.type = "button";
    const chosen = marks[student.id] === status;
    button.classList.add(chosen ? `btn-${STATUS_COLORS[status]}` : "btn-outline-secondary");
    button.setAttribute("aria-pressed", String(chosen));
    button.addEventListener("click", () => {
      marks[student.id] = chosen ? null : status;
      render();
    });
    group.append(button);
  });
  row.append(name, details, group);
  return row;
}

function render() {
  dayInput.value = sheet.day;
  dayInput.max = todayText();
  document.getElementById("day-next").disabled = sheet.day >= todayText();
  if (!sheet.students.length) {
    const empty = el("div", "list-group-item text-body-secondary", "No students in this class yet.");
    list.replaceChildren(empty);
  } else {
    list.replaceChildren(...sheet.students.map(studentRow));
  }
  const counts = { present: 0, late: 0, absent: 0, excused: 0 };
  Object.values(marks).forEach((status) => { if (status) counts[status] += 1; });
  const marked = Object.values(counts).reduce((sum, n) => sum + n, 0);
  document.getElementById("day-summary").textContent =
    `${marked} of ${sheet.students.length} marked · ${counts.present} present · ${counts.late} late · ${counts.absent} absent · ${counts.excused} excused`;
}

async function loadDay(day) {
  try {
    const response = await apiFetch(`/api/classes/${classId}/attendance${day ? `?date=${day}` : ""}`);
    if (!response) return;
    const data = await response.json();
    if (!response.ok) {
      showError("attendance-error", data.error || "Could not load the attendance.");
      if (sheet) dayInput.value = sheet.day;
      return;
    }
    hideError("attendance-error");
    sheet = data;
    marks = Object.fromEntries(sheet.students.map((student) => [student.id, student.status]));
    document.getElementById("attendance-details").textContent = [
      sheet.class.name, sheet.class.subject, plural(sheet.recorded_days.length, "day") + " recorded",
    ].filter(Boolean).join(" · ");
    document.getElementById("attendance-saved").classList.add("d-none");
    render();
  } catch {
    showError("attendance-error", "Cannot reach the server. Check your connection.");
  }
}

// Changing the day drops marks that were not saved, so ask first.
function unsaved() {
  return sheet.students.some((student) => marks[student.id] !== student.status);
}

function changeDay(day) {
  if (unsaved() && !window.confirm("You have marks that are not saved. Change the day anyway?")) {
    dayInput.value = sheet.day;
    return;
  }
  loadDay(day);
}

dayInput.addEventListener("change", () => dayInput.value && changeDay(dayInput.value));
document.getElementById("day-previous").addEventListener("click", () => changeDay(shiftDay(sheet.day, -1)));
document.getElementById("day-next").addEventListener("click", () => changeDay(shiftDay(sheet.day, 1)));
document.getElementById("mark-all-present").addEventListener("click", () => {
  sheet.students.forEach((student) => { if (!marks[student.id]) marks[student.id] = "present"; });
  render();
});

saveButton.addEventListener("click", async () => {
  const stopLoading = startLoading(saveButton);
  if (!stopLoading) return;
  hideError("attendance-error");
  try {
    const response = await apiFetch(`/api/classes/${classId}/attendance`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ day: sheet.day, marks }),
    });
    if (!response) return;
    const data = await response.json();
    if (!response.ok) {
      showError("attendance-error", data.error || "Could not save the attendance.");
      return;
    }
    sheet = data;
    marks = Object.fromEntries(sheet.students.map((student) => [student.id, student.status]));
    render();
    document.getElementById("attendance-saved").classList.remove("d-none");
  } catch {
    showError("attendance-error", "Cannot reach the server. Check your connection.");
  } finally {
    stopLoading();
  }
});

// The export links carry the chosen days: /classes/1/attendance.xlsx?from=2026-10-01&to=2026-10-31
const exportFrom = document.getElementById("export-from");
const exportTo = document.getElementById("export-to");
const exportLinks = [document.getElementById("export-xlsx"), document.getElementById("export-pdf")];
const exportBase = exportLinks.map((link) => link.getAttribute("href"));

function updateExportLinks() {
  const query = new URLSearchParams();
  if (exportFrom.value) query.set("from", exportFrom.value);
  if (exportTo.value) query.set("to", exportTo.value);
  exportLinks.forEach((link, index) => link.setAttribute("href", exportBase[index] + (query.toString() ? `?${query}` : "")));
}
exportFrom.addEventListener("input", updateExportLinks);
exportTo.addEventListener("input", updateExportLinks);

loadDay(todayText());
