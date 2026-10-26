// Shared by the bar charts (dashboard-chart.js, log-chart.js). Chart.js must be loaded first.
// Chart.js draws on a canvas and cannot read CSS, so the theme colours are read here, and the charts
// are drawn again when the theme changes (each page does that with its own last view).

// cssColor("--accent-to") -> "#06b6d4"
const cssColor = (name) => getComputedStyle(document.documentElement).getPropertyValue(name).trim();

// shorten("Pre-test: Ancient Greece", 12) -> "Pre-test: An…"
const shorten = (text, max) => (text.length > max ? `${text.slice(0, max - 1)}…` : text);

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
// The bar picked as a filter (view.selected) is the solid accent, so it stands out.
const barFill = (selected) => (context) => {
  if (selected !== null && selected !== undefined && context.dataIndex === selected) return cssColor("--accent-to");
  const area = context.chart.chartArea;
  if (!area) return cssColor("--accent-from");
  const gradient = context.chart.ctx.createLinearGradient(0, area.bottom, 0, area.top);
  gradient.addColorStop(0, cssColor("--accent-from"));
  gradient.addColorStop(1, cssColor("--accent-to"));
  return gradient;
};

// makeBarChart(canvas, view, previousChart) -> a new bar chart (the previous one is destroyed first).
// view = {labels, values, titles, details, max, suffix, onBarClick, selected}
//   titles = the full names for the tooltip, details = the text under the name in the tooltip,
//   onBarClick(index) is optional, selected = the index of a highlighted bar (or null).
function makeBarChart(canvas, view, previous) {
  if (previous) previous.destroy();
  const textColor = cssColor("--bs-secondary-color");
  const calm = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  return new Chart(canvas, {
    type: "bar",
    data: {
      labels: view.labels,
      datasets: [{
        data: view.values,
        backgroundColor: barFill(view.selected),
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
}
