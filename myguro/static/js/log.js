// The activity log (supervisor and admin, read only): who did what, newest first, searched and
// filtered on the server, a page at a time. Tap a person's name to see only their entries.

const SEARCH_DELAY = 300; // ms after the last key
const SCHOOL_TIME_ZONE = "Asia/Manila"; // times are shown in school time, wherever the viewer is

const list = document.getElementById("log-list");
const searchInput = document.getElementById("search");
const roleFilter = document.getElementById("role-filter");
const categoryFilter = document.getElementById("category-filter");
const fromFilter = document.getElementById("from-filter");
const toFilter = document.getElementById("to-filter");
const personChip = document.getElementById("person-chip");

let page = 1;
let pages = 1;
let person = null; // {id, name} while showing one person's entries
let searchTimer = null;
let requestNumber = 0; // only the newest request may draw its answer

const ROLE_BADGES = {
  admin: "text-bg-dark", teacher: "text-bg-primary", student: "text-bg-success", supervisor: "text-bg-warning",
};

// "2026-10-01 15:30:00" (UTC, from SQLite) -> "Oct 1, 2026, 11:30 PM" in school time
function formatTime(value) {
  return new Date(value.replace(" ", "T") + "Z").toLocaleString(undefined, {
    month: "short", day: "numeric", year: "numeric", hour: "numeric", minute: "2-digit",
    timeZone: SCHOOL_TIME_ZONE,
  });
}

function messageItem(text) {
  const div = document.createElement("div");
  div.className = "list-group-item text-body-secondary";
  div.textContent = text;
  return div;
}

// One entry: the sentence on top, then who, their role, the time and the category.
function entryItem(entry) {
  const row = document.createElement("div");
  row.className = "list-group-item";

  const summary = document.createElement("div");
  summary.textContent = entry.summary;

  const details = document.createElement("div");
  details.className = "small text-body-secondary d-flex flex-wrap align-items-center gap-1 mt-1";

  // Tapping the name shows only this person (not for a failed login with an unknown username)
  const name = document.createElement(entry.actor.id ? "button" : "span");
  name.className = entry.actor.id ? "btn btn-link btn-sm p-0 fw-semibold" : "fw-semibold";
  name.textContent = entry.actor.name;
  if (entry.actor.id) {
    name.type = "button";
    name.addEventListener("click", () => showPerson(entry.actor));
  }
  details.append(name);

  if (entry.actor.role) {
    const badge = document.createElement("span");
    badge.className = `badge ${ROLE_BADGES[entry.actor.role] || "text-bg-secondary"}`;
    badge.textContent = entry.actor.role;
    details.append(badge);
  }
  const category = document.createElement("span");
  category.className = "badge text-bg-light border";
  category.textContent = entry.category;
  const time = document.createElement("span");
  time.textContent = formatTime(entry.at) + (entry.address ? ` · ${entry.address}` : "");
  details.append(category, time);

  row.append(summary, details);
  return row;
}

// How many of the filters in the box are used (the badge on the Filters button)
function filterCount() {
  return [roleFilter.value, categoryFilter.value, fromFilter.value, toFilter.value].filter(Boolean).length;
}

function showFilterCount() {
  const badge = document.getElementById("filter-count");
  const count = filterCount();
  badge.textContent = count;
  badge.classList.toggle("d-none", count === 0);
}

function showPerson(actor) {
  person = { id: actor.id, name: actor.name };
  document.getElementById("person-chip-name").textContent = actor.name;
  personChip.classList.remove("d-none");
  search(1);
}

function clearPerson() {
  person = null;
  personChip.classList.add("d-none");
  search(1);
}

// Loads one page of the log with the search, the filters and the person.
async function search(wantedPage) {
  const params = new URLSearchParams({ page: wantedPage, q: searchInput.value.trim() });
  if (roleFilter.value) params.set("role", roleFilter.value);
  if (categoryFilter.value) params.set("category", categoryFilter.value);
  if (fromFilter.value) params.set("from", fromFilter.value);
  if (toFilter.value) params.set("to", toFilter.value);
  if (person) params.set("user_id", person.id);
  const mine = ++requestNumber;
  showFilterCount();
  try {
    const response = await apiFetch(`/api/log?${params}`);
    if (!response || mine !== requestNumber) return;
    const data = await response.json();
    if (!response.ok) {
      showError("log-error", data.error || "Could not load the log.");
      return;
    }
    hideError("log-error");
    page = data.page;
    pages = data.pages;
    list.replaceChildren(...(data.entries.length ? data.entries.map(entryItem) : [messageItem("No entries match.")]));
    document.getElementById("log-summary").textContent = plural(data.total, "entry", "entries");
    document.getElementById("pager").classList.toggle("d-none", pages <= 1);
    document.getElementById("page-info").textContent = `Page ${page} of ${pages}`;
    document.getElementById("prev-page").disabled = page <= 1;
    document.getElementById("next-page").disabled = page >= pages;
  } catch {
    showError("log-error", "Cannot reach the server. Check your connection.");
  }
}

searchInput.addEventListener("input", () => {
  clearTimeout(searchTimer);
  searchTimer = setTimeout(() => search(1), SEARCH_DELAY);
});
[roleFilter, categoryFilter, fromFilter, toFilter].forEach((field) => field.addEventListener("change", () => search(1)));
document.getElementById("filter-clear").addEventListener("click", () => {
  [roleFilter, categoryFilter, fromFilter, toFilter].forEach((field) => (field.value = ""));
  search(1);
});
document.getElementById("person-chip-clear").addEventListener("click", clearPerson);
document.getElementById("prev-page").addEventListener("click", () => search(page - 1));
document.getElementById("next-page").addEventListener("click", () => search(page + 1));

search(1);
