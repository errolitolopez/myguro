// The holiday calendar: one month at a time. The admin can add, change and remove local holidays.

const isAdmin = document.getElementById("calendar-page").dataset.admin === "yes";
const KIND_BADGE = {
  regular: "text-bg-danger",
  special: "text-bg-warning",
  "special-working": "text-bg-info",
  local: "text-bg-success",
};
const KIND_LABEL = {
  regular: "Regular holiday",
  special: "Special non-working day",
  "special-working": "Special working day",
  local: "Local holiday",
};

const today = new Date();
let shownYear = today.getFullYear();
let shownMonth = today.getMonth(); // 0 = January
const loadedYears = {}; // year -> holidays, so moving between months of one year asks the server once
let editingId = null;

// isoDay(2026, 0, 5) -> "2026-01-05"
const isoDay = (year, month, day) =>
  `${year}-${String(month + 1).padStart(2, "0")}-${String(day).padStart(2, "0")}`;

// holidaysOn("2026-01-01") -> the holidays of that day (a list, maybe empty)
const holidaysOn = (day) => (loadedYears[shownYear] || []).filter((holiday) => holiday.day === day);

async function loadYear(year) {
  if (loadedYears[year]) return true;
  try {
    const response = await apiFetch(`/api/calendar?year=${year}`);
    if (!response) return false;
    if (!response.ok) {
      showError("calendar-error", t("Could not load the calendar."));
      return false;
    }
    loadedYears[year] = (await response.json()).holidays;
    hideError("calendar-error");
    return true;
  } catch {
    showError("calendar-error", t("Cannot reach the server. Check your connection."));
    return false;
  }
}

function weekdayHeaders() {
  const names = [t("Sun"), t("Mon"), t("Tue"), t("Wed"), t("Thu"), t("Fri"), t("Sat")];
  document.getElementById("weekday-row").replaceChildren(...names.map((name, index) => {
    const cell = document.createElement("th");
    cell.className = `small fw-semibold${index === 0 ? " text-danger" : ""}`;
    cell.scope = "col";
    cell.textContent = name;
    return cell;
  }));
}

function dayCell(day, isToday) {
  const cell = document.createElement("td");
  cell.className = "p-1 align-top";
  cell.style.height = "4.5rem";
  const number = document.createElement("div");
  number.className = isToday ? "fw-bold text-success" : "small";
  number.textContent = day.number;
  cell.append(number);
  // A dot per holiday keeps a phone-sized cell readable; the full names are in the list below.
  for (const holiday of holidaysOn(day.iso)) {
    const mark = document.createElement("div");
    mark.className = `badge ${KIND_BADGE[holiday.kind]} d-block text-truncate mt-1`;
    mark.textContent = holiday.name;
    mark.title = holiday.name;
    cell.append(mark);
  }
  return cell;
}

function drawMonth() {
  const title = new Date(shownYear, shownMonth, 1).toLocaleDateString(undefined, { month: "long", year: "numeric" });
  document.getElementById("month-title").textContent = title;
  const firstWeekday = new Date(shownYear, shownMonth, 1).getDay();
  const daysInMonth = new Date(shownYear, shownMonth + 1, 0).getDate();
  const todayIso = isoDay(today.getFullYear(), today.getMonth(), today.getDate());

  const rows = [];
  let row = document.createElement("tr");
  for (let blank = 0; blank < firstWeekday; blank += 1) row.append(document.createElement("td"));
  for (let number = 1; number <= daysInMonth; number += 1) {
    const iso = isoDay(shownYear, shownMonth, number);
    row.append(dayCell({ number, iso }, iso === todayIso));
    if (row.children.length === 7) {
      rows.push(row);
      row = document.createElement("tr");
    }
  }
  if (row.children.length) {
    while (row.children.length < 7) row.append(document.createElement("td"));
    rows.push(row);
  }
  document.getElementById("month-body").replaceChildren(...rows);
}

function holidayItem(holiday) {
  const item = document.createElement("li");
  item.className = "list-group-item d-flex flex-wrap align-items-center gap-2";
  const text = document.createElement("div");
  text.className = "flex-grow-1";
  const name = document.createElement("div");
  name.className = "fw-semibold";
  name.textContent = holiday.name;
  const details = document.createElement("div");
  details.className = "small text-body-secondary";
  details.textContent = formatDay(holiday.day);
  text.append(name, details);
  const badge = document.createElement("span");
  badge.className = `badge ${KIND_BADGE[holiday.kind]}`;
  badge.textContent = t(KIND_LABEL[holiday.kind]);
  item.append(text, badge);
  if (isAdmin && holiday.kind === "local") {
    const edit = document.createElement("button");
    edit.type = "button";
    edit.className = "btn btn-sm btn-outline-primary bi bi-pencil";
    edit.setAttribute("aria-label", t("Edit holiday"));
    edit.addEventListener("click", () => openHolidayForm(holiday));
    const remove = document.createElement("button");
    remove.type = "button";
    remove.className = "btn btn-sm btn-outline-danger bi bi-trash";
    remove.setAttribute("aria-label", t("Delete holiday"));
    remove.addEventListener("click", () => deleteHoliday(holiday, remove));
    item.append(edit, remove);
  }
  return item;
}

function drawList() {
  const prefix = isoDay(shownYear, shownMonth, 1).slice(0, 7);
  const holidays = (loadedYears[shownYear] || []).filter((holiday) => holiday.day.startsWith(prefix));
  if (!holidays.length) {
    const empty = document.createElement("li");
    empty.className = "list-group-item text-body-secondary";
    empty.textContent = t("No holidays this month.");
    document.getElementById("holiday-list").replaceChildren(empty);
    return;
  }
  document.getElementById("holiday-list").replaceChildren(...holidays.map(holidayItem));
}

async function show() {
  if (!(await loadYear(shownYear))) return;
  drawMonth();
  drawList();
}

function moveMonth(step) {
  const moved = new Date(shownYear, shownMonth + step, 1);
  shownYear = moved.getFullYear();
  shownMonth = moved.getMonth();
  show();
}

document.getElementById("previous-month").addEventListener("click", () => moveMonth(-1));
document.getElementById("next-month").addEventListener("click", () => moveMonth(1));
document.getElementById("today-button").addEventListener("click", () => {
  shownYear = today.getFullYear();
  shownMonth = today.getMonth();
  show();
});

// ---- Admin: add, change, remove a local holiday ----

async function deleteHoliday(holiday, button) {
  if (!window.confirm(t("Delete this holiday?"))) return;
  const stopLoading = startLoading(button);
  if (!stopLoading) return;
  try {
    const response = await apiFetch(`/api/calendar/holidays/${holiday.id}`, { method: "DELETE" });
    if (!response) return;
    if (!response.ok) {
      showError("calendar-error", (await response.json()).error);
      return;
    }
    delete loadedYears[shownYear];
    await show();
  } catch {
    showError("calendar-error", t("Cannot reach the server. Check your connection."));
  } finally {
    stopLoading();
  }
}

if (isAdmin) {
  const modal = bootstrap.Modal.getOrCreateInstance(document.getElementById("holiday-modal"));
  const form = document.getElementById("holiday-form");
  const dayInput = document.getElementById("holiday-day");
  const nameInput = document.getElementById("holiday-name");

  // openHolidayForm() -> a blank form; openHolidayForm(holiday) -> that holiday, to change it
  window.openHolidayForm = (holiday) => {
    editingId = holiday ? holiday.id : null;
    document.getElementById("holiday-modal-title").textContent = holiday ? t("Edit local holiday") : t("Add local holiday");
    dayInput.value = holiday ? holiday.day : isoDay(shownYear, shownMonth, 1);
    nameInput.value = holiday ? holiday.name : "";
    hideError("holiday-form-error");
    modal.show();
  };

  document.getElementById("add-holiday-button").addEventListener("click", () => window.openHolidayForm());

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const stopLoading = startLoading(document.getElementById("holiday-save"));
    if (!stopLoading) return;
    try {
      const response = await apiFetch(editingId ? `/api/calendar/holidays/${editingId}` : "/api/calendar/holidays", {
        method: editingId ? "PUT" : "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ day: dayInput.value, name: nameInput.value }),
      });
      if (!response) return;
      if (!response.ok) {
        showError("holiday-form-error", (await response.json()).error);
        return;
      }
      modal.hide();
      // Show the month of the holiday that was just saved, so the admin sees it.
      const [year, month] = dayInput.value.split("-").map(Number);
      for (const key of Object.keys(loadedYears)) delete loadedYears[key];
      shownYear = year;
      shownMonth = month - 1;
      await show();
    } catch {
      showError("holiday-form-error", t("Cannot reach the server. Check your connection."));
    } finally {
      stopLoading();
    }
  });
}

weekdayHeaders();
show();
