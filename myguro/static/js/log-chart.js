// The bar chart on the activity log page. It counts the same entries the list shows (log.js builds the
// filters) and is a filter too: tap a day to see only that day, a category or a role to see only that one.
// Counts only; the server sends no names.

let logChart = null;
let lastLogChartView = null; // so a theme change can draw the chart again
let logChartRequest = 0; // only the newest request may draw its answer

const logChartView = () => document.querySelector("input[name=log-chart-view]:checked").value;

// dayLabel("2026-10-24") -> "Oct 24"; parsed as a calendar day so a time zone cannot shift it
function dayLabel(isoDay) {
  const [year, month, day] = isoDay.split("-").map(Number);
  return new Date(year, month - 1, day).toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

// capitalised("sign-in") -> "Sign-in"
const capitalised = (text) => text.charAt(0).toUpperCase() + text.slice(1);

function fillLogChartTable(view) {
  const rows = view.titles.map((title, index) => {
    const row = document.createElement("tr");
    const name = document.createElement("th");
    name.scope = "row";
    name.textContent = title;
    const count = document.createElement("td");
    count.textContent = view.values[index];
    row.append(name, count);
    return row;
  });
  document.getElementById("log-chart-table").replaceChildren(...rows);
}

// logChartFor(data) -> what to draw for the answer of /api/log/chart, with what a tap on a bar does
function logChartFor(data) {
  const entries = (count) => plural(count, "entry", "entries");
  if (data.view === "day") {
    // One day picked (From = To) is the highlighted bar; tapping it again goes back to the last 14 days.
    const picked = fromFilter.value && fromFilter.value === toFilter.value ? fromFilter.value : null;
    return {
      labels: data.items.map((item) => dayLabel(item.key)),
      values: data.items.map((item) => item.count),
      titles: data.items.map((item) => dayLabel(item.key)),
      details: data.items.map((item) => entries(item.count)),
      suffix: "",
      selected: picked === null ? null : data.items.findIndex((item) => item.key === picked),
      onBarClick: (index) => {
        const day = data.items[index].key;
        fromFilter.value = picked === day ? "" : day;
        toFilter.value = picked === day ? "" : day;
        search(1);
      },
      hint: picked ? t("Showing one day. Tap its bar again to go back.") : t("Entries per day. Tap a bar to see only that day."),
    };
  }
  const filter = data.view === "category" ? categoryFilter : roleFilter;
  return {
    labels: data.items.map((item) => capitalised(item.key)),
    values: data.items.map((item) => item.count),
    titles: data.items.map((item) => capitalised(item.key)),
    details: data.items.map((item) => entries(item.count)),
    suffix: "",
    selected: filter.value ? data.items.findIndex((item) => item.key === filter.value) : null,
    onBarClick: (index) => {
      filter.value = filter.value === data.items[index].key ? "" : data.items[index].key;
      search(1);
    },
    hint: t("Entries per {view}. Tap a bar to see only that {view}; tap it again to show all.", { view: data.view }),
  };
}

function drawLogChart(view) {
  lastLogChartView = view;
  fillLogChartTable(view);
  document.getElementById("log-chart-sub").textContent = view.hint;
  logChart = makeBarChart(document.getElementById("log-chart"), view, logChart);
}

// Loads the counts for the filters now chosen and draws them. Called by log.js on every new search.
async function loadLogChart() {
  if (typeof Chart === "undefined") {
    showError("log-chart-error", t("The chart could not load. Check your internet connection."));
    return;
  }
  const params = filterParams();
  params.set("view", logChartView());
  const mine = ++logChartRequest;
  try {
    const response = await apiFetch(`/api/log/chart?${params}`);
    if (!response || mine !== logChartRequest) return;
    const data = await response.json();
    if (!response.ok) {
      showError("log-chart-error", data.error || t("Could not load the chart."));
      return;
    }
    hideError("log-chart-error");
    drawLogChart(logChartFor(data));
  } catch {
    showError("log-chart-error", t("Cannot reach the server. Check your connection."));
  }
}

document.querySelectorAll("input[name=log-chart-view]").forEach((radio) => radio.addEventListener("change", loadLogChart));

// The theme picker changes these attributes; draw again so the chart colours follow.
new MutationObserver(() => { if (lastLogChartView) drawLogChart(lastLogChartView); })
  .observe(document.documentElement, { attributes: true, attributeFilter: ["data-bs-theme", "data-myguro-theme"] });
