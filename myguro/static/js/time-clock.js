// The teacher's Time in / out page: one button that switches between Time in and Time out, and the last 14 days.

const clockState = document.getElementById("clock-state");
const timeInButton = document.getElementById("time-in-button");
const timeOutButton = document.getElementById("time-out-button");
const clockDays = document.getElementById("clock-days");

// timeOnly("2026-11-02 00:15:00") -> "8:15 AM" (the time is UTC, shown in the viewer's time zone)
const timeOnly = (utcText) =>
  new Date(utcText.replace(" ", "T") + "Z").toLocaleTimeString(undefined, { hour: "numeric", minute: "2-digit", hour12: true });

// hoursText(5400) -> "1 h 30 min"; 600 -> "10 min"; 0 -> "0 min"
const hoursText = (seconds) => {
  const minutes = Math.round(seconds / 60);
  return minutes >= 60 ? `${Math.floor(minutes / 60)} h ${minutes % 60} min` : `${minutes} min`;
};

// One line per session: "8:00 AM – 12:00 PM · 4 h 0 min", or "8:00 AM – No time out"
const sessionLine = (session) => {
  const line = document.createElement("div");
  line.className = "small";
  if (!session.time_out) {
    line.textContent = `${timeOnly(session.time_in)} – ${t("No time out")}`;
    return line;
  }
  const seconds = (Date.parse(session.time_out.replace(" ", "T") + "Z") - Date.parse(session.time_in.replace(" ", "T") + "Z")) / 1000;
  line.textContent = `${timeOnly(session.time_in)} – ${timeOnly(session.time_out)} · ${hoursText(seconds)}`;
  return line;
};

function dayItem(day) {
  const item = document.createElement("div");
  item.className = "list-group-item";
  const head = document.createElement("div");
  head.className = "d-flex justify-content-between fw-semibold";
  const title = document.createElement("span");
  title.textContent = formatDay(day.day);
  const total = document.createElement("span");
  total.textContent = hoursText(day.total_seconds);
  head.append(title, total);
  item.append(head, ...day.sessions.map(sessionLine));
  return item;
}

function show(data) {
  const since = data.clocked_in ? t("You are timed in since {time}.", { time: timeOnly(data.since) }) : t("You are timed out.");
  clockState.textContent = since;
  timeInButton.classList.toggle("d-none", data.clocked_in);
  timeOutButton.classList.toggle("d-none", !data.clocked_in);
  if (!data.days.length) {
    const empty = document.createElement("div");
    empty.className = "list-group-item text-body-secondary";
    empty.textContent = t("No records yet.");
    clockDays.replaceChildren(empty);
    return;
  }
  clockDays.replaceChildren(...data.days.map(dayItem));
}

async function load() {
  try {
    const response = await apiFetch("/api/time-clock");
    if (!response) return;
    const data = await response.json();
    if (!response.ok) {
      showError("clock-error", data.error || t("Could not load."));
      return;
    }
    hideError("clock-error");
    show(data);
  } catch {
    showError("clock-error", t("Cannot reach the server. Check your connection."));
  }
}

// press(button, "in") sends the time in (or "out"), shows what the server answered, and restores the button
async function press(button, which) {
  hideError("clock-error");
  const stopLoading = startLoading(button);
  try {
    const response = await apiFetch(`/api/time-clock/${which}`, { method: "POST" });
    if (!response) return;
    const data = await response.json();
    if (!response.ok) {
      showError("clock-error", data.error || t("Could not save."));
      await load(); // the page was out of date (for example timed in on another device)
      return;
    }
    show(data);
  } catch {
    showError("clock-error", t("Cannot reach the server. Check your connection."));
  } finally {
    stopLoading();
  }
}

timeInButton.addEventListener("click", () => press(timeInButton, "in"));
timeOutButton.addEventListener("click", () => press(timeOutButton, "out"));
load();
