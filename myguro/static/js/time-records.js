// The admin's Time records page: every teacher's time in / time out for a range of days.

const recordsFrom = document.getElementById("records-from");
const recordsTo = document.getElementById("records-to");
const recordsTeacher = document.getElementById("records-teacher");
const recordsList = document.getElementById("records-list");
let teachersLoaded = false;

const timeOnly = (utcText) =>
  new Date(utcText.replace(" ", "T") + "Z").toLocaleTimeString(undefined, { hour: "numeric", minute: "2-digit", hour12: true });

// hoursText(5400) -> "1 h 30 min"
const hoursText = (seconds) => {
  const minutes = Math.round(seconds / 60);
  return minutes >= 60 ? `${Math.floor(minutes / 60)} h ${minutes % 60} min` : `${minutes} min`;
};

// sessionText({time_in, time_out}) -> "8:00 AM – 12:00 PM", or "8:00 AM – No time out"
const sessionText = (session) =>
  `${timeOnly(session.time_in)} – ${session.time_out ? timeOnly(session.time_out) : t("No time out")}`;

function rowItem(row) {
  const item = document.createElement("div");
  item.className = "list-group-item";
  const head = document.createElement("div");
  head.className = "d-flex justify-content-between fw-semibold";
  const who = document.createElement("span");
  who.textContent = row.teacher_name;
  const total = document.createElement("span");
  total.textContent = hoursText(row.total_seconds);
  head.append(who, total);
  const day = document.createElement("div");
  day.className = "small text-body-secondary";
  day.textContent = formatDay(row.day);
  const sessions = row.sessions.map((session) => {
    const line = document.createElement("div");
    line.className = "small";
    line.textContent = sessionText(session);
    return line;
  });
  item.append(head, day, ...sessions);
  return item;
}

function show(data) {
  recordsFrom.value = data.first_day;
  recordsTo.value = data.last_day;
  if (!teachersLoaded) {
    teachersLoaded = true;
    recordsTeacher.append(...data.teachers.map((teacher) => new Option(teacher.name, teacher.id)));
  }
  if (!data.rows.length) {
    const empty = document.createElement("div");
    empty.className = "list-group-item text-body-secondary";
    empty.textContent = t("No records for these days.");
    recordsList.replaceChildren(empty);
    return;
  }
  recordsList.replaceChildren(...data.rows.map(rowItem));
}

async function load() {
  const params = new URLSearchParams();
  if (recordsFrom.value) params.set("from", recordsFrom.value);
  if (recordsTo.value) params.set("to", recordsTo.value);
  if (recordsTeacher.value) params.set("teacher_id", recordsTeacher.value);
  try {
    const response = await apiFetch(`/api/time-records?${params}`);
    if (!response) return;
    const data = await response.json();
    if (!response.ok) {
      showError("records-error", data.error || t("Could not load."));
      return;
    }
    hideError("records-error");
    show(data);
  } catch {
    showError("records-error", t("Cannot reach the server. Check your connection."));
  }
}

for (const field of [recordsFrom, recordsTo, recordsTeacher]) field.addEventListener("change", load);
load();
