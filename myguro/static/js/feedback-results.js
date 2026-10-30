// Admin: the totals of the feedback. Per question: the average, how many rated, and how many gave
// each number of stars. Shows no names: the server never sends them.

const list = document.getElementById("feedback-list");
const MAX_STARS = 5;

// distributionRow(5, 12, 20) -> "5 ★ [bar 60%] 12"
function distributionRow(stars, count, most) {
  const row = document.createElement("div");
  row.className = "d-flex align-items-center gap-2 small";
  const label = document.createElement("span");
  label.className = "text-nowrap";
  label.style.width = "2.2rem";
  label.textContent = `${stars} ★`;
  const track = document.createElement("div");
  track.className = "progress flex-grow-1";
  track.setAttribute("role", "progressbar");
  track.setAttribute("aria-label", `${plural(count, "person", "people")} gave ${stars} of ${MAX_STARS}`);
  const bar = document.createElement("div");
  bar.className = "progress-bar";
  bar.style.width = most > 0 ? `${Math.round((100 * count) / most)}%` : "0%";
  track.append(bar);
  const number = document.createElement("span");
  number.className = "text-end";
  number.style.width = "2rem";
  number.textContent = count;
  row.append(label, track, number);
  return row;
}

// questionCard({text, count, average, counts}) -> one card: the question, the average ring, five bars
function questionCard(question) {
  const card = document.createElement("div");
  card.className = "card";
  const body = document.createElement("div");
  body.className = "card-body";

  const top = document.createElement("div");
  top.className = "d-flex justify-content-between align-items-center gap-3 mb-3";
  const left = document.createElement("div");
  const title = document.createElement("div");
  title.className = "fw-semibold";
  title.textContent = question.text;
  const sub = document.createElement("div");
  sub.className = "small text-body-secondary";
  sub.textContent = question.count === 0 ? t("Nobody rated this yet") : `${plural(question.count, "rating")}`;
  left.append(title, sub);

  const score = document.createElement("div");
  score.className = "d-flex align-items-center gap-2";
  const average = document.createElement("div");
  average.className = "fs-3 fw-bold stat-number";
  average.textContent = question.average === null ? "–" : question.average.toFixed(1);
  score.append(average);
  if (question.average !== null) score.append(scoreRing(question.average, MAX_STARS, true));
  top.append(left, score);

  const bars = document.createElement("div");
  bars.className = "d-grid gap-1";
  const most = Math.max(...question.counts);
  for (let stars = MAX_STARS; stars >= 1; stars--) {
    bars.append(distributionRow(stars, question.counts[stars - 1], most));
  }
  body.append(top, bars);
  card.append(body);
  return card;
}

const chosenGroup = () => document.querySelector("input[name=who]:checked").value;

async function loadSummary() {
  hideError("feedback-error");
  try {
    const group = chosenGroup();
    const response = await apiFetch(`/api/feedback/summary${group ? `?role=${group}` : ""}`);
    if (!response) return;
    const data = await response.json();
    if (!response.ok) {
      list.replaceChildren();
      showError("feedback-error", data.error || t("Could not load the feedback."));
      return;
    }
    document.getElementById("feedback-count").textContent = data.respondents === 0
      ? t("Nobody has given feedback yet.") : `${plural(data.respondents, "person", "people")} gave feedback`;
    list.replaceChildren(...data.questions.map(questionCard));
  } catch {
    list.replaceChildren();
    showError("feedback-error", t("Cannot reach the server. Check your connection."));
  }
}

document.querySelectorAll("input[name=who]").forEach((radio) => radio.addEventListener("change", loadSummary));
loadSummary();
