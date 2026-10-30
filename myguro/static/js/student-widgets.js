// Student dashboard widgets: Next due, Progress and Score trend. They use only /api/my-activities.
// Wrapped in a function so its names (percentOf ...) cannot clash with dashboard-chart.js on the same page.
(() => {
  const NEXT_DUE_LIMIT = 3; // rows in Next due
  const TREND_POINTS = 8; // most recent released scores in the trend line
  const SVG = "http://www.w3.org/2000/svg";

  // dayNumber("2026-10-30") -> a whole number of days, so two calendar days can be subtracted without a time
  // zone shifting them (the server sends days as text)
  const dayNumber = (isoDay) => {
    const [year, month, day] = isoDay.split("-").map(Number);
    return Math.round(Date.UTC(year, month - 1, day) / 86400000);
  };

  // dueText("2026-11-02", "2026-10-30") -> "Due in 3 days"; "Due today"; "Overdue by 2 days"
  const dueText = (dueDay, today) => {
    const days = dayNumber(dueDay) - dayNumber(today);
    if (days === 0) return t("Due today");
    if (days === 1) return t("Due tomorrow");
    if (days > 0) return t("Due in {days} days", { days });
    return days === -1 ? t("Overdue by 1 day") : t("Overdue by {days} days", { days: -days });
  };

  // percentOf({earned: 8, possible: 12, pending: 2}) -> 80 (of the points checked so far), or null
  const percentOf = (score) => {
    if (!score) return null;
    const checked = score.possible - score.pending;
    return checked > 0 ? Math.round((100 * score.earned) / checked) : null;
  };

  // What the student can still answer, soonest due first; no due date goes last.
  const nextDue = (activities) => activities
    .filter((activity) => (!activity.done || activity.status === "in_progress") && !activity.closed)
    .sort((a, b) => (a.due_date || "9999").localeCompare(b.due_date || "9999"));

  const showNextDue = (activities, today) => {
    const rows = nextDue(activities).slice(0, NEXT_DUE_LIMIT).map((activity) => {
      const row = document.createElement("a");
      row.className = "list-group-item list-group-item-action d-flex justify-content-between align-items-center gap-2";
      row.href = `/my-activities/${activity.id}`;
      const text = document.createElement("div");
      const title = document.createElement("div");
      title.className = "fw-semibold";
      title.textContent = activity.title;
      const details = document.createElement("div");
      details.className = "small text-body-secondary";
      details.textContent = [activity.subject, activity.status === "in_progress"
        ? t("{answered} of {questions} answered", { answered: activity.answered, questions: activity.questions }) : ""].filter(Boolean).join(" · ");
      text.append(title, details);
      const badge = document.createElement("span");
      const overdue = activity.due_date && activity.due_date < today;
      badge.className = `badge text-nowrap ${overdue ? "text-bg-danger" : activity.due_date === today ? "text-bg-warning" : "text-bg-light border"}`;
      badge.textContent = activity.due_date ? dueText(activity.due_date, today) : t("No due date");
      const go = document.createElement("span");
      go.className = "btn btn-sm btn-success";
      go.textContent = activity.status === "in_progress" ? t("Continue") : t("Start");
      const right = document.createElement("div");
      right.className = "d-flex flex-column align-items-end gap-1";
      right.append(badge, go);
      row.append(text, right);
      return row;
    });
    const box = document.getElementById("next-due-list");
    if (rows.length === 0) {
      // Nothing to do: a centred message that fills the card (the card is as tall as its neighbours), not a
      // thin list row with empty space under it.
      const icon = document.createElement("i");
      icon.className = "bi bi-check-circle fs-1 text-success";
      icon.setAttribute("aria-hidden", "true");
      const message = document.createElement("div");
      message.className = "text-body-secondary";
      message.textContent = t("You're all caught up. Nothing to do right now.");
      box.className = "d-flex flex-column align-items-center justify-content-center text-center gap-2 p-4 flex-grow-1";
      box.replaceChildren(icon, message);
      return;
    }
    box.className = "list-group list-group-flush";
    box.replaceChildren(...rows);
  };

  // Progress: activities submitted out of everything given this school year, and how many this week.
  const showProgress = (activities) => {
    const done = activities.filter((activity) => activity.done).length;
    document.getElementById("progress-ring").replaceChildren(scoreRing(done, activities.length));
    document.getElementById("progress-text").textContent = activities.length === 0
      ? t("Nothing given yet")
      : activities.length === 1 ? t("{done} of 1 activity done", { done })
      : t("{done} of {total} activities done", { done, total: activities.length });
    const weekAgo = Date.now() - 7 * 86400000;
    const thisWeek = activities.filter((activity) => activity.submitted_at
      && new Date(`${activity.submitted_at.replace(" ", "T")}Z`).getTime() >= weekAgo).length;
    document.getElementById("progress-week").textContent = thisWeek ? t("{count} submitted this week", { count: thisWeek }) : "";
  };

  // A small line through the scores, drawn as SVG so it follows the text colour and needs no library.
  const trendLine = (percents) => {
    const width = 120;
    const height = 40;
    const svg = document.createElementNS(SVG, "svg");
    svg.setAttribute("viewBox", `0 0 ${width} ${height}`);
    svg.setAttribute("preserveAspectRatio", "none");
    svg.setAttribute("width", "100%");
    svg.setAttribute("height", "100%");
    svg.setAttribute("role", "img");
    svg.setAttribute("aria-label", t("Your last scores: {scores}", { scores: percents.map((percent) => `${percent}%`).join(", ") }));
    const step = percents.length > 1 ? (width - 8) / (percents.length - 1) : 0;
    const points = percents.map((percent, index) => [4 + index * step, 36 - (percent / 100) * 32]);
    const line = document.createElementNS(SVG, "polyline");
    line.setAttribute("points", points.map((point) => point.join(",")).join(" "));
    line.setAttribute("fill", "none");
    line.setAttribute("stroke", "currentColor");
    line.setAttribute("stroke-width", "2");
    line.setAttribute("vector-effect", "non-scaling-stroke");
    svg.append(line);
    for (const [x, y] of points) {
      const dot = document.createElementNS(SVG, "circle");
      dot.setAttribute("cx", x);
      dot.setAttribute("cy", y);
      dot.setAttribute("r", "2.5");
      dot.setAttribute("fill", "currentColor");
      svg.append(dot);
    }
    return svg;
  };

  // Score trend: the released scores in the order they were submitted; the latest and how it moved.
  const showTrend = (activities) => {
    const scored = activities
      .filter((activity) => activity.submitted_at && percentOf(activity.score) !== null)
      .sort((a, b) => a.submitted_at.localeCompare(b.submitted_at))
      .slice(-TREND_POINTS)
      .map((activity) => percentOf(activity.score));
    const latest = document.getElementById("trend-latest");
    const change = document.getElementById("trend-change");
    const line = document.getElementById("trend-line");
    if (scored.length === 0) {
      latest.textContent = "–";
      change.textContent = t("Scores show here once your teacher releases them.");
      line.replaceChildren();
      return;
    }
    latest.textContent = `${scored[scored.length - 1]}%`;
    const difference = scored.length > 1 ? scored[scored.length - 1] - scored[scored.length - 2] : null;
    change.textContent = difference === null ? t("Your latest score")
      : difference === 0 ? t("Same as the one before")
      : difference > 0 ? t("Up {n}% from the one before", { n: difference })
      : t("Down {n}% from the one before", { n: -difference });
    line.replaceChildren(scored.length > 1 ? trendLine(scored) : "");
  };

  async function loadStudentWidgets() {
    hideError("next-due-error");
    try {
      const response = await apiFetch("/api/my-activities");
      if (!response) return;
      const data = await response.json();
      if (!response.ok) {
        showError("next-due-error", data.error || t("Could not load your activities."));
        document.getElementById("next-due-list").replaceChildren();
        return;
      }
      showNextDue(data.activities, data.today);
      showProgress(data.activities);
      showTrend(data.activities);
    } catch {
      document.getElementById("next-due-list").replaceChildren();
      showError("next-due-error", t("Cannot reach the server. Check your connection."));
    }
  }

  loadStudentWidgets();

  // The To do card: with nothing left to do, tapping it celebrates (confetti) instead of opening an empty list.
  const todoCard = document.getElementById("stat-to-do").closest("a");
  todoCard.addEventListener("click", (event) => {
    if (document.getElementById("stat-to-do").textContent.trim() !== "0") return; // still work: open the list
    event.preventDefault();
    confetti();
    const label = todoCard.querySelector(".small");
    label.textContent = t("All done, great job!");
    setTimeout(() => (label.textContent = t("To do")), 3000);
  });
})();
