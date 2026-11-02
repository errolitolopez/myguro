// The calendar: one month at a time, or one day. The admin can add, change and remove local holidays and school events.

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
const loadedEvents = {}; // year -> school events, loaded together with the holidays
let editingId = null;
let editingEventId = null;
let view = "month"; // "month" or "day"
let shownDate = new Date(today.getFullYear(), today.getMonth(), today.getDate()); // the day in the Day view
let firstDraw = true;

// isoDay(2026, 0, 5) -> "2026-01-05"
const isoDay = (year, month, day) =>
  `${year}-${String(month + 1).padStart(2, "0")}-${String(day).padStart(2, "0")}`;

// dayIso(new Date(2026, 0, 5)) -> "2026-01-05"
const dayIso = (date) => isoDay(date.getFullYear(), date.getMonth(), date.getDate());

// holidaysOn("2026-01-01") -> the holidays of that day (a list, maybe empty)
const holidaysOn = (day) => (loadedYears[shownYear] || []).filter((holiday) => holiday.day === day);

// eventsBetween("2026-06-01", "2026-06-30") -> the events with at least one day in that range.
// ISO days sort like dates, so comparing the text is enough.
const eventsBetween = (first, last) =>
  (loadedEvents[shownYear] || []).filter((item) => item.start_day <= last && item.end_day >= first);

async function loadYear(year) {
  if (loadedYears[year]) return true;
  try {
    const response = await apiFetch(`/api/calendar?year=${year}`);
    if (!response) return false;
    if (!response.ok) {
      showError("calendar-error", t("Could not load the calendar."));
      return false;
    }
    const body = await response.json();
    loadedYears[year] = body.holidays;
    loadedEvents[year] = body.events;
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
  // Tap a day to see just that day (a keyboard can do it too).
  cell.setAttribute("role", "button");
  cell.tabIndex = 0;
  cell.style.cursor = "pointer";
  const events = eventsBetween(day.iso, day.iso);
  const label = new Date(shownYear, shownMonth, day.number).toLocaleDateString(undefined, { dateStyle: "full" });
  const eventCount = events.length === 1 ? t("1 school event") : t("{count} school events", { count: events.length });
  cell.setAttribute("aria-label", events.length ? `${label}, ${eventCount}` : label);
  const openDay = () => {
    shownDate = new Date(shownYear, shownMonth, day.number);
    setView("day");
  };
  cell.addEventListener("click", openDay);
  cell.addEventListener("keydown", (event) => {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      openDay();
    }
  });
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
  // Some days hold many events and many run for weeks, so a cell shows only how many; the names are in the lists.
  if (events.length) {
    const mark = document.createElement("div");
    mark.className = "badge text-bg-primary bi bi-calendar-event d-block mt-1";
    mark.textContent = ` ${events.length}`;
    mark.title = events.map((item) => item.name).join("\n");
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
  // What the day is about: our own sentence for a national holiday (translated), the admin's words for a local one.
  if (holiday.description) {
    const about = document.createElement("div");
    about.className = "small mt-1";
    about.textContent = t(holiday.description);
    text.append(about);
  }
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
    remove.addEventListener("click", () =>
      removeItem(`/api/calendar/holidays/${holiday.id}`, t("Delete this holiday?"), remove));
    item.append(edit, remove);
  }
  return item;
}

// eventDays({start_day: "2026-06-01", end_day: "2026-06-05"}) -> "Jun 1, 2026 – Jun 5, 2026"
const eventDays = (item) =>
  (item.start_day === item.end_day ? formatDay(item.start_day) : `${formatDay(item.start_day)} – ${formatDay(item.end_day)}`);

function eventItem(schoolEvent) {
  const item = document.createElement("li");
  item.className = "list-group-item d-flex flex-wrap align-items-center gap-2";
  const text = document.createElement("div");
  text.className = "flex-grow-1";
  text.style.minWidth = "0"; // a long DepEd name wraps instead of pushing the buttons out
  const name = document.createElement("div");
  name.className = "fw-semibold";
  name.textContent = schoolEvent.name;
  const details = document.createElement("div");
  details.className = "small text-body-secondary";
  details.textContent = eventDays(schoolEvent);
  text.append(name, details);
  const badge = document.createElement("span");
  badge.className = "badge text-bg-primary";
  badge.textContent = t("School event");
  item.append(text, badge);
  if (isAdmin) {
    const edit = document.createElement("button");
    edit.type = "button";
    edit.className = "btn btn-sm btn-outline-primary bi bi-pencil";
    edit.setAttribute("aria-label", t("Edit school event"));
    edit.addEventListener("click", () => openEventForm(schoolEvent));
    const remove = document.createElement("button");
    remove.type = "button";
    remove.className = "btn btn-sm btn-outline-danger bi bi-trash";
    remove.setAttribute("aria-label", t("Delete school event"));
    remove.addEventListener("click", () =>
      removeItem(`/api/calendar/events/${schoolEvent.id}`, t("Delete this school event?"), remove));
    item.append(edit, remove);
  }
  return item;
}

// drawEvents("event-list", events, "Nothing here.") fills a list, or says that it is empty.
function drawEvents(listId, events, emptyText) {
  if (!events.length) {
    const empty = document.createElement("li");
    empty.className = "list-group-item text-body-secondary";
    empty.textContent = emptyText;
    document.getElementById(listId).replaceChildren(empty);
    return;
  }
  document.getElementById(listId).replaceChildren(...events.map(eventItem));
}

function drawList() {
  const prefix = isoDay(shownYear, shownMonth, 1).slice(0, 7);
  const lastDay = isoDay(shownYear, shownMonth, new Date(shownYear, shownMonth + 1, 0).getDate());
  drawEvents("event-list", eventsBetween(`${prefix}-01`, lastDay), t("No school events this month."));
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

// The Day view: the day's name and its holidays (or a line saying there is none).
function drawDay() {
  document.getElementById("day-title").textContent =
    shownDate.toLocaleDateString(undefined, { weekday: "long", month: "long", day: "numeric", year: "numeric" });
  const holidays = holidaysOn(dayIso(shownDate));
  drawEvents("day-events", eventsBetween(dayIso(shownDate), dayIso(shownDate)), t("No school events on this day."));
  if (!holidays.length) {
    const empty = document.createElement("li");
    empty.className = "list-group-item text-body-secondary";
    empty.textContent = t("No holiday on this day.");
    document.getElementById("day-holidays").replaceChildren(empty);
    return;
  }
  document.getElementById("day-holidays").replaceChildren(...holidays.map(holidayItem));
}

// calendarPath() -> "/calendar/2026/09" for a month, "/calendar/2026/09/15" for a day
function calendarPath() {
  const [year, month, day] = (view === "day" ? dayIso(shownDate) : isoDay(shownYear, shownMonth, 1)).split("-");
  return view === "day" ? `/calendar/${year}/${month}/${day}` : `/calendar/${year}/${month}`;
}

// Keeps the address on what is shown, so it can be shared and the browser's Back button works. The first page
// replaces the address instead, or Back would land on /calendar and bounce forward again.
function updateAddress() {
  const path = calendarPath();
  if (window.location.pathname === path) return;
  if (firstDraw) window.history.replaceState(null, "", path);
  else window.history.pushState(null, "", path);
}

// Sets shownDate from the address and returns the view it asks for. Plain /calendar means this month.
function readAddress() {
  const found = window.location.pathname.match(/^\/calendar\/(\d+)\/(\d+)(?:\/(\d+))?/);
  if (!found) {
    shownDate = new Date(today.getFullYear(), today.getMonth(), today.getDate());
    return "month";
  }
  shownDate = new Date(Number(found[1]), Number(found[2]) - 1, Number(found[3] || 1));
  return found[3] ? "day" : "month";
}

async function show() {
  updateAddress();
  firstDraw = false;
  if (!(await loadYear(shownYear))) return;
  if (view === "day") {
    drawDay();
    return;
  }
  drawMonth();
  drawList();
}

// setView("day") shows the Day view for shownDate; setView("month") the month the day is in.
function setView(name) {
  view = name;
  shownYear = shownDate.getFullYear();
  shownMonth = shownDate.getMonth();
  document.getElementById("month-view").classList.toggle("d-none", name !== "month");
  document.getElementById("day-view").classList.toggle("d-none", name !== "day");
  for (const [id, own] of [["view-month", "month"], ["view-day", "day"]]) {
    const button = document.getElementById(id);
    button.classList.toggle("active", name === own);
    button.setAttribute("aria-pressed", name === own ? "true" : "false");
  }
  show();
}

function moveDay(step) {
  shownDate = new Date(shownDate.getFullYear(), shownDate.getMonth(), shownDate.getDate() + step);
  setView("day");
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

document.getElementById("view-month").addEventListener("click", () => setView("month"));
document.getElementById("view-day").addEventListener("click", () => {
  // From the month grid: today when this is the month of today, else the 1st of the month on screen.
  const thisMonth = shownYear === today.getFullYear() && shownMonth === today.getMonth();
  if (view === "month") shownDate = thisMonth ? new Date(today.getFullYear(), today.getMonth(), today.getDate()) : new Date(shownYear, shownMonth, 1);
  setView("day");
});
window.addEventListener("popstate", () => setView(readAddress()));

const copyLinkButton = document.getElementById("copy-link");
copyLinkButton.addEventListener("click", async () => {
  try {
    await navigator.clipboard.writeText(window.location.href);
    copyLinkButton.textContent = ` ${t("Copied!")}`;
  } catch {
    copyLinkButton.textContent = ` ${t("Can't copy")}`;
  }
  setTimeout(() => (copyLinkButton.textContent = ` ${t("Copy link")}`), 1500);
});

document.getElementById("previous-day").addEventListener("click", () => moveDay(-1));
document.getElementById("next-day").addEventListener("click", () => moveDay(1));
document.getElementById("today-day-button").addEventListener("click", () => {
  shownDate = new Date(today.getFullYear(), today.getMonth(), today.getDate());
  setView("day");
});

// ---- Admin: add, change, remove local holidays and school events ----

// removeItem("/api/calendar/events/3", "Delete this?", button) asks first, deletes, and draws the calendar again.
async function removeItem(url, question, button) {
  if (!window.confirm(question)) return;
  const stopLoading = startLoading(button);
  if (!stopLoading) return;
  try {
    const response = await apiFetch(url, { method: "DELETE" });
    if (!response) return;
    if (!response.ok) {
      showError("calendar-error", (await response.json()).error);
      return;
    }
    // An event can run into the next year, so forget every year, not only this one.
    for (const key of Object.keys(loadedYears)) delete loadedYears[key];
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
  const descriptionInput = document.getElementById("holiday-description");

  // openHolidayForm() -> a blank form; openHolidayForm(holiday) -> that holiday, to change it
  window.openHolidayForm = (holiday) => {
    editingId = holiday ? holiday.id : null;
    document.getElementById("holiday-modal-title").textContent = holiday ? t("Edit local holiday") : t("Add local holiday");
    dayInput.value = holiday ? holiday.day : (view === "day" ? dayIso(shownDate) : isoDay(shownYear, shownMonth, 1));
    nameInput.value = holiday ? holiday.name : "";
    descriptionInput.value = holiday ? holiday.description : "";
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
        body: JSON.stringify({ day: dayInput.value, name: nameInput.value, description: descriptionInput.value }),
      });
      if (!response) return;
      if (!response.ok) {
        showError("holiday-form-error", (await response.json()).error);
        return;
      }
      modal.hide();
      // Show the month (or day) of the holiday that was just saved, so the admin sees it.
      const [year, month, day] = dayInput.value.split("-").map(Number);
      for (const key of Object.keys(loadedYears)) delete loadedYears[key];
      shownDate = new Date(year, month - 1, day);
      setView(view);
    } catch {
      showError("holiday-form-error", t("Cannot reach the server. Check your connection."));
    } finally {
      stopLoading();
    }
  });
}

if (isAdmin) {
  const modal = bootstrap.Modal.getOrCreateInstance(document.getElementById("event-modal"));
  const form = document.getElementById("event-form");
  const startInput = document.getElementById("event-start");
  const endInput = document.getElementById("event-end");
  const nameInput = document.getElementById("event-name");

  // openEventForm() -> a blank form; openEventForm(schoolEvent) -> that event, to change it
  window.openEventForm = (schoolEvent) => {
    editingEventId = schoolEvent ? schoolEvent.id : null;
    document.getElementById("event-modal-title").textContent = schoolEvent ? t("Edit school event") : t("Add school event");
    startInput.value = schoolEvent ? schoolEvent.start_day : (view === "day" ? dayIso(shownDate) : isoDay(shownYear, shownMonth, 1));
    endInput.value = schoolEvent && schoolEvent.end_day !== schoolEvent.start_day ? schoolEvent.end_day : "";
    nameInput.value = schoolEvent ? schoolEvent.name : "";
    hideError("event-form-error");
    modal.show();
  };

  document.getElementById("add-event-button").addEventListener("click", () => window.openEventForm());

  form.addEventListener("submit", async (submitEvent) => {
    submitEvent.preventDefault();
    const stopLoading = startLoading(document.getElementById("event-save"));
    if (!stopLoading) return;
    try {
      const response = await apiFetch(editingEventId ? `/api/calendar/events/${editingEventId}` : "/api/calendar/events", {
        method: editingEventId ? "PUT" : "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ start_day: startInput.value, end_day: endInput.value, name: nameInput.value }),
      });
      if (!response) return;
      if (!response.ok) {
        showError("event-form-error", (await response.json()).error);
        return;
      }
      modal.hide();
      // Show the month (or day) the event starts in, so the admin sees it.
      const [year, month, day] = startInput.value.split("-").map(Number);
      for (const key of Object.keys(loadedYears)) delete loadedYears[key];
      shownDate = new Date(year, month - 1, day);
      setView(view);
    } catch {
      showError("event-form-error", t("Cannot reach the server. Check your connection."));
    } finally {
      stopLoading();
    }
  });
}

weekdayHeaders();
setView(readAddress());
