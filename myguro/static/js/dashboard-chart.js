// The dashboard bar chart, drawn with Chart.js (same idea as mymotoworks).
// Teacher: pick a class; one bar per activity (average score, or how many students submitted). Tap a bar
//   to open that activity's results.
// Student: one bar per subject (average score, or activities done). Tap a subject to see its activities,
//   tap an activity to open it.

const card = document.getElementById("chart-card");
const role = card.dataset.role;
const backButton = document.getElementById("chart-back");
const classSelect = document.getElementById("chart-class");
let chart = null;
let lastView = null; // what was drawn last, so a theme change can draw it again
let shownSubject = null; // student: the subject whose activities are shown, null for the subject bars
let activitiesData = []; // student: everything from /api/my-activities
let gradebook = null; // teacher: the gradebook of the chosen class

// cssColor("--accent-to") -> "#06b6d4". Chart.js draws on a canvas and cannot read CSS, so the theme's
// colour variables are read here (the chart is drawn again when the theme changes).
const cssColor = (name) => getComputedStyle(document.documentElement).getPropertyValue(name).trim();

const chosenMetric = () => document.querySelector("input[name=chart-metric]:checked").value;

// shorten("Pre-test: Ancient Greece", 12) -> "Pre-test: An…"
const shorten = (text, max) => (text.length > max ? `${text.slice(0, max - 1)}…` : text);

// percentOf({earned: 8, possible: 12, pending: 2}) -> 80 (of the points checked so far), or null
const percentOf = (score) => {
  if (!score) return null;
  const checked = score.possible - score.pending;
  return checked > 0 ? Math.round((100 * score.earned) / checked) : null;
};

// Writes each bar's value above it, but only when there are few bars (the tooltip has the rest).
const valueLabels = {
  id: "valueLabels",
  afterDatasetsDraw(instance) {
    const { ctx } = instance;
    const suffix = instance.options.plugins.valueLabels.suffix;
    ctx.save();
    ctx.fillStyle = cssColor("--bs-secondary-color");
    ctx.font = "11px sans-serif";
    ctx.textAlign = "center";
    instance.getDatasetMeta(0).data.forEach((bar, index) => {
      const value = instance.data.datasets[0].data[index];
      if (value > 0) ctx.fillText(`${value}${suffix}`, bar.x, bar.y - 4);
    });
    ctx.restore();
  },
};

// The accent gradient (bottom to top) for the bars. Before the chart has an area it is one colour.
const barFill = (context) => {
  const area = context.chart.chartArea;
  if (!area) return cssColor("--accent-from");
  const gradient = context.chart.ctx.createLinearGradient(0, area.bottom, 0, area.top);
  gradient.addColorStop(0, cssColor("--accent-from"));
  gradient.addColorStop(1, cssColor("--accent-to"));
  return gradient;
};

// fillTable(view) puts the same numbers in the hidden table
const fillTable = (view) => {
  const rows = view.titles.map((title, index) => {
    const row = document.createElement("tr");
    const name = document.createElement("th");
    name.scope = "row";
    name.textContent = title;
    const value = document.createElement("td");
    value.textContent = view.details[index];
    row.append(name, value);
    return row;
  });
  document.getElementById("chart-table").replaceChildren(...rows);
};

// drawChart({labels, values, titles, details, max, suffix, onBarClick}) -> one bar per value.
// titles = the full names for the tooltip; details = the text under the name in the tooltip.
const drawChart = (view) => {
  lastView = view;
  if (chart) chart.destroy();
  fillTable(view);
  const textColor = cssColor("--bs-secondary-color");
  const calm = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  chart = new Chart(document.getElementById("chart"), {
    type: "bar",
    data: {
      labels: view.labels,
      datasets: [{
        data: view.values,
        backgroundColor: barFill,
        hoverBackgroundColor: cssColor("--accent-to"),
        borderRadius: { topLeft: 4, topRight: 4 },
        borderSkipped: "bottom",
        maxBarThickness: 36,
      }],
    },
    options: {
      maintainAspectRatio: false,
      animation: calm ? false : { duration: 500 },
      layout: { padding: { top: 18 } },
      onClick: (event, elements) => {
        if (view.onBarClick && elements.length > 0) view.onBarClick(elements[0].index);
      },
      onHover: (event, elements) => {
        event.native.target.style.cursor = view.onBarClick && elements.length > 0 ? "pointer" : "default";
      },
      plugins: {
        legend: { display: false },
        valueLabels: { suffix: view.suffix },
        tooltip: {
          callbacks: {
            title: (items) => view.titles[items[0].dataIndex],
            label: (item) => view.details[item.dataIndex],
          },
        },
      },
      scales: {
        x: { grid: { display: false }, ticks: { color: textColor, maxRotation: 0, autoSkip: true } },
        y: {
          beginAtZero: true,
          max: view.max,
          grid: { color: cssColor("--bs-border-color") },
          ticks: { color: textColor, maxTicksLimit: 5, precision: 0, callback: (value) => `${value}${view.suffix}` },
        },
      },
    },
    plugins: view.labels.length <= 12 ? [valueLabels] : [],
  });
};

// showEmpty("No classes yet.") hides the chart and says why; showEmpty(null) shows the chart again
const showEmpty = (message) => {
  document.getElementById("chart-empty").textContent = message || "";
  document.getElementById("chart-empty").classList.toggle("d-none", !message);
  document.getElementById("chart-body").classList.toggle("d-none", Boolean(message));
};

// ---- Teacher ----

// showClassView() -> one bar per activity given to the chosen class
const showClassView = () => {
  const activities = gradebook.activities;
  if (activities.length === 0) {
    showEmpty("No activities have been given to this class yet.");
    return;
  }
  showEmpty(null);
  const metric = chosenMetric();
  const total = gradebook.students.length;
  // How many students submitted each activity (a cell is null when it was not given to that student).
  const submitted = activities.map((_, index) =>
    gradebook.students.filter((student) => student.cells[index] && student.cells[index].status === "submitted").length);
  const average = metric === "average";
  document.getElementById("chart-sub").textContent = average
    ? "Average score of the class on each activity. Tap a bar to open its results."
    : `Students who submitted each activity (${plural(total, "student")} in the class). Tap a bar to open its results.`;
  drawChart({
    labels: activities.map((activity) => shorten(activity.title, 12)),
    values: activities.map((activity, index) => (average ? activity.average || 0 : submitted[index])),
    titles: activities.map((activity) => activity.title),
    details: activities.map((activity, index) => average
      ? (activity.average === null ? "No scores yet" : `Average ${activity.average}%`)
      : `${submitted[index]} of ${total} submitted`),
    max: average ? 100 : Math.max(total, 1),
    suffix: average ? "%" : "",
    onBarClick: (index) => { window.location.href = `/results/${activities[index].assignment_id}`; },
  });
};

async function loadGradebook() {
  hideError("chart-error");
  try {
    const response = await apiFetch(`/api/classes/${classSelect.value}/gradebook`);
    if (!response) return;
    const data = await response.json();
    if (!response.ok) throw new Error(data.error);
    gradebook = data;
    showClassView();
  } catch (error) {
    showError("chart-error", error.message || "Could not load the chart.");
  }
}

async function startTeacher() {
  hideError("chart-error");
  try {
    const response = await apiFetch("/api/classes");
    if (!response) return;
    const data = await response.json();
    if (!response.ok) throw new Error(data.error);
    if (data.classes.length === 0) {
      classSelect.classList.add("d-none");
      showEmpty("No classes yet. Create a class to see its results here.");
      return;
    }
    classSelect.replaceChildren(...data.classes.map((item) => {
      const option = document.createElement("option");
      option.value = item.id;
      option.textContent = classTitle(item);
      return option;
    }));
    await loadGradebook();
  } catch (error) {
    showError("chart-error", error.message || "Could not load the chart.");
  }
}

// ---- Student ----

// subjectOf(activity) -> the subject, or "No subject" for an older sheet that has none
const subjectOf = (activity) => activity.subject || "No subject";

// The bars of the subjects: average score or number done.
const showSubjectView = () => {
  const done = activitiesData.filter((activity) => activity.done);
  if (done.length === 0) {
    showEmpty("Your scores will show here after you submit an activity.");
    return;
  }
  showEmpty(null);
  const subjects = [...new Set(done.map(subjectOf))].sort((a, b) => a.localeCompare(b));
  const metric = chosenMetric();
  const average = metric === "average";
  const stats = subjects.map((subject) => {
    const items = done.filter((activity) => subjectOf(activity) === subject);
    const percents = items.map((activity) => percentOf(activity.score)).filter((value) => value !== null);
    return {
      count: items.length,
      average: percents.length ? Math.round(percents.reduce((sum, value) => sum + value, 0) / percents.length) : null,
    };
  });
  document.getElementById("chart-sub").textContent = average
    ? "Your average score in each subject (only scores your teacher has released). Tap a bar to see its activities."
    : "Activities you finished in each subject. Tap a bar to see them.";
  drawChart({
    labels: subjects.map((subject) => shorten(subject, 12)),
    values: stats.map((stat) => (average ? stat.average || 0 : stat.count)),
    titles: subjects,
    details: stats.map((stat) => average
      ? (stat.average === null ? "No released scores yet" : `Average ${stat.average}%`)
      : `${plural(stat.count, "activity", "activities")} done`),
    max: average ? 100 : undefined,
    suffix: average ? "%" : "",
    onBarClick: (index) => { shownSubject = subjects[index]; showStudentData(); },
  });
};

// The bars of one subject: the score of each activity done.
const showActivityView = () => {
  const items = activitiesData.filter((activity) => activity.done && subjectOf(activity) === shownSubject);
  showEmpty(null);
  document.getElementById("chart-sub").textContent = `${shownSubject}: your score on each activity. Tap a bar to open it.`;
  drawChart({
    labels: items.map((activity) => shorten(activity.title, 12)),
    values: items.map((activity) => percentOf(activity.score) || 0),
    titles: items.map((activity) => activity.title),
    details: items.map((activity) => {
      const percent = percentOf(activity.score);
      return percent === null ? "Score not released yet" : `${activity.score.earned} / ${activity.score.possible - activity.score.pending} (${percent}%)`;
    }),
    max: 100,
    suffix: "%",
    onBarClick: (index) => { window.location.href = `/my-activities/${items[index].id}`; },
  });
};

function showStudentData() {
  const inSubject = shownSubject !== null;
  backButton.classList.toggle("d-none", !inSubject);
  // The "Done" count means nothing for a single subject's activities, so the choice hides there.
  document.getElementById("chart-metrics").classList.toggle("d-none", inSubject);
  document.getElementById("chart-title").textContent = inSubject ? ` ${shownSubject}` : " My scores";
  if (inSubject) showActivityView(); else showSubjectView();
}

async function startStudent() {
  hideError("chart-error");
  try {
    const response = await apiFetch("/api/my-activities");
    if (!response) return;
    const data = await response.json();
    if (!response.ok) throw new Error(data.error);
    activitiesData = data.activities;
    showStudentData();
  } catch (error) {
    showError("chart-error", error.message || "Could not load the chart.");
  }
}

// ---- Wiring ----

document.querySelectorAll("input[name=chart-metric]").forEach((radio) =>
  radio.addEventListener("change", () => {
    if (role === "teacher" && gradebook) showClassView();
    if (role === "student") showStudentData();
  }));
backButton.addEventListener("click", () => { shownSubject = null; showStudentData(); });
if (classSelect) classSelect.addEventListener("change", loadGradebook);

// The theme picker changes these attributes; draw again so the chart colours follow.
new MutationObserver(() => { if (lastView) drawChart(lastView); })
  .observe(document.documentElement, { attributes: true, attributeFilter: ["data-bs-theme", "data-myguro-theme"] });

if (typeof Chart === "undefined") {
  showError("chart-error", "The chart could not load. Check your internet connection.");
} else if (role === "teacher") {
  startTeacher();
} else {
  startStudent();
}
