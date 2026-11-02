// The dashboard's Upcoming holidays card. Each row opens that day on the Calendar.
// Wrapped in a function so its names cannot clash with the other dashboard scripts on the same page.
(() => {
  const KIND_NAMES = {
    regular: "Regular holiday",
    special: "Special non-working day",
    "special-working": "Special working day",
    local: "Local holiday",
  };

  // daysBetween("2026-11-02", "2026-11-30") -> 28, counted in whole days so time zones cannot shift it
  const daysBetween = (first, last) => {
    const utc = (iso) => {
      const [year, month, day] = iso.split("-").map(Number);
      return Date.UTC(year, month - 1, day);
    };
    return Math.round((utc(last) - utc(first)) / 86400000);
  };

  // whenText(0) -> "Today", whenText(1) -> "Tomorrow", whenText(28) -> "In 28 days"
  const whenText = (days) => {
    if (days === 0) return t("Today");
    return days === 1 ? t("Tomorrow") : t("In {days} days", { days });
  };

  // holidayRow({day: "2026-11-30", name: "Bonifacio Day", kind: "regular"}, "2026-11-02") -> a link to that day
  const holidayRow = (holiday, today) => {
    const row = document.createElement("a");
    row.className = "list-group-item list-group-item-action d-flex justify-content-between align-items-center gap-2";
    row.href = `/calendar/${holiday.day.replaceAll("-", "/")}`;
    const left = document.createElement("div");
    left.style.minWidth = "0"; // a long name wraps instead of pushing the day count out
    const name = document.createElement("div");
    name.className = "fw-semibold";
    name.textContent = holiday.name;
    const details = document.createElement("div");
    details.className = "small text-body-secondary";
    details.textContent = `${formatDay(holiday.day)} · ${t(KIND_NAMES[holiday.kind])}`;
    left.append(name, details);
    const when = document.createElement("span");
    when.className = "small text-nowrap";
    when.textContent = whenText(daysBetween(today, holiday.day));
    row.append(left, when);
    return row;
  };

  const load = async () => {
    const list = document.getElementById("holidays-list");
    try {
      const response = await apiFetch("/api/calendar/upcoming");
      if (!response) return;
      if (!response.ok) {
        list.replaceChildren();
        showError("holidays-error", t("Could not load the holidays."));
        return;
      }
      const { holidays, today } = await response.json();
      if (holidays.length) {
        list.replaceChildren(...holidays.map((holiday) => holidayRow(holiday, today)));
      } else {
        const empty = document.createElement("div");
        empty.className = "list-group-item small text-body-secondary";
        empty.textContent = t("No upcoming holidays.");
        list.replaceChildren(empty);
      }
    } catch {
      list.replaceChildren();
      showError("holidays-error", t("Cannot reach the server. Check your connection."));
    }
  };

  load();
})();
