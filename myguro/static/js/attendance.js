// Attendance (teacher): pick a day and tap a mark for each student from the paper record. Every tap
// is saved by itself a moment later, so a lost connection or a closed tab never loses a whole class.

const classId = document.querySelector("main").dataset.classId;
const STATUS_LABELS = { present: t("Present"), late: t("Late"), absent: t("Absent"), excused: t("Excused") };
// The colour of a chosen mark; the others stay outlined
const STATUS_COLORS = { present: "success", late: "warning", absent: "danger", excused: "info" };

let sheet = null; // from /api/classes/<id>/attendance
let marks = {}; // student id -> status or null, what is on screen (saved or not)
let pending = {}; // student id -> status or null, taps not saved yet
let running = null; // the save in progress, so only one runs at a time
let saveTimer = null;

const dayInput = document.getElementById("day");
const list = document.getElementById("student-list");
const saveStatus = document.getElementById("save-status");

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
  group.setAttribute("aria-label", t("Attendance of {name}", { name: student.name }));
  sheet.statuses.forEach((status) => {
    const button = el("button", "btn btn-sm", STATUS_LABELS[status]);
    button.type = "button";
    const chosen = marks[student.id] === status;
    button.classList.add(chosen ? `btn-${STATUS_COLORS[status]}` : "btn-outline-secondary");
    button.setAttribute("aria-pressed", String(chosen));
    button.addEventListener("click", () => setMark(student.id, chosen ? null : status));
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
    const empty = el("div", "list-group-item text-body-secondary", t("No students in this class yet."));
    list.replaceChildren(empty);
  } else {
    list.replaceChildren(...sheet.students.map(studentRow));
  }
  const counts = { present: 0, late: 0, absent: 0, excused: 0 };
  Object.values(marks).forEach((status) => { if (status) counts[status] += 1; });
  const marked = Object.values(counts).reduce((sum, n) => sum + n, 0);
  document.getElementById("day-summary").textContent =
    t("{marked} of {count} marked · {present} present · {late} late · {absent} absent · {excused} excused", { marked, count: sheet.students.length, present: counts.present, late: counts.late, absent: counts.absent, excused: counts.excused });
}

async function loadDay(day) {
  try {
    const response = await apiFetch(`/api/classes/${classId}/attendance${day ? `?date=${day}` : ""}`);
    if (!response) return;
    const data = await response.json();
    if (!response.ok) {
      showError("attendance-error", data.error || t("Could not load the attendance."));
      if (sheet) dayInput.value = sheet.day;
      return;
    }
    hideError("attendance-error");
    sheet = data;
    marks = Object.fromEntries(sheet.students.map((student) => [student.id, student.status]));
    pending = {};
    showSaveStatus("");
    document.getElementById("attendance-details").textContent = [
      sheet.class.name, sheet.class.subject, plural(sheet.recorded_days.length, "day") + " recorded",
    ].filter(Boolean).join(" · ");
    render();
  } catch {
    showError("attendance-error", t("Cannot reach the server. Check your connection."));
  }
}

// showSaveStatus("Saved", "success") -> the line under the list
function showSaveStatus(text, color = "body-secondary") {
  saveStatus.textContent = text;
  saveStatus.className = `small text-${color}`;
}

// A tap: show it now, save it in half a second (more taps in that time go in the same save)
function setMark(studentId, status) {
  marks[studentId] = status;
  pending[studentId] = status;
  render();
  showSaveStatus(t("Saving..."));
  clearTimeout(saveTimer);
  saveTimer = setTimeout(flush, 500);
}

// Send the taps that are not saved yet. Resolves true when nothing is left unsaved.
function flush() {
  clearTimeout(saveTimer);
  if (!running) running = sendPending().finally(() => { running = null; });
  return running;
}

async function sendPending() {
  while (Object.keys(pending).length) {
    const sent = { ...pending };
    try {
      const response = await apiFetch(`/api/classes/${classId}/attendance`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ day: sheet.day, marks: sent }),
      });
      if (!response) return false;
      const data = await response.json();
      if (!response.ok) {
        if (response.status >= 500) throw new Error("server");
        // The server refused (for example a past school year): show why and go back to what is saved
        showError("attendance-error", data.error || t("Could not save the attendance."));
        showSaveStatus(t("Not saved"), "danger");
        await loadDay(sheet.day);
        showSaveStatus(t("Not saved"), "danger");
        return false;
      }
      hideError("attendance-error");
      // Forget the taps that were saved (a newer tap on the same student stays pending)
      Object.keys(sent).forEach((id) => { if (pending[id] === sent[id]) delete pending[id]; });
      data.students.forEach((student) => {
        const own = sheet.students.find((item) => item.id === student.id);
        if (own) { own.status = student.status; own.totals = student.totals; }
      });
      sheet.recorded_days = data.recorded_days;
      render();
    } catch {
      // No connection: keep the taps and try again soon
      showSaveStatus(t("Not saved yet. Trying again..."), "danger");
      saveTimer = setTimeout(flush, 3000);
      return false;
    }
  }
  showSaveStatus(t("All changes saved"), "success");
  return true;
}

// Save what is waiting before showing another day; if that fails, ask before dropping it.
async function changeDay(day) {
  if (Object.keys(pending).length && !(await flush())
      && !window.confirm(t("Some marks could not be saved. Change the day anyway?"))) {
    dayInput.value = sheet.day;
    return;
  }
  loadDay(day);
}

window.addEventListener("beforeunload", (event) => {
  if (Object.keys(pending).length) event.preventDefault(); // the browser asks before leaving
});

dayInput.addEventListener("change", () => dayInput.value && changeDay(dayInput.value));
document.getElementById("day-previous").addEventListener("click", () => changeDay(shiftDay(sheet.day, -1)));
document.getElementById("day-next").addEventListener("click", () => changeDay(shiftDay(sheet.day, 1)));
document.getElementById("mark-all-present").addEventListener("click", () => {
  const unmarked = sheet.students.filter((student) => !marks[student.id]);
  unmarked.forEach((student) => { marks[student.id] = "present"; pending[student.id] = "present"; });
  render();
  if (unmarked.length) {
    showSaveStatus(t("Saving..."));
    clearTimeout(saveTimer);
    saveTimer = setTimeout(flush, 500);
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
// The days start as the current month ("2026-10-01" to "2026-10-31"); clear them to export every day.
// monthBounds() -> ["2026-10-01", "2026-10-31"]
const monthBounds = () => {
  const now = new Date();
  const pad = (n) => String(n).padStart(2, "0");
  const last = new Date(now.getFullYear(), now.getMonth() + 1, 0).getDate();
  const month = `${now.getFullYear()}-${pad(now.getMonth() + 1)}`;
  return [`${month}-01`, `${month}-${pad(last)}`];
};
[exportFrom.value, exportTo.value] = monthBounds();
updateExportLinks();

exportFrom.addEventListener("input", updateExportLinks);
exportTo.addEventListener("input", updateExportLinks);

loadDay(todayText());
