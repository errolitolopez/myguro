// Teacher and student: rate MyGuro from 1 to 5 on a few questions. The earlier answers are shown and
// can be changed. The answers are private: the admin only sees totals.

const questionsBox = document.getElementById("feedback-questions");
const form = document.getElementById("feedback-form");
const saveButton = document.getElementById("feedback-save");
const MAX_STARS = 5;
let ratings = {}; // question key -> 1-5, the stars now chosen

// starRating(key, text) -> a block with the question and five star buttons (a radio group)
function starRating(key, text) {
  const block = document.createElement("div");
  block.className = "card";
  const body = document.createElement("div");
  body.className = "card-body";
  const label = document.createElement("div");
  label.className = "fw-semibold mb-2";
  label.id = `question-${key}`;
  label.textContent = text;

  const group = document.createElement("div");
  group.className = "star-rating";
  group.setAttribute("role", "radiogroup");
  group.setAttribute("aria-labelledby", label.id);
  for (let value = 1; value <= MAX_STARS; value++) {
    const star = document.createElement("button");
    star.type = "button";
    star.className = "star";
    star.dataset.value = value;
    star.setAttribute("role", "radio");
    star.setAttribute("aria-label", `${value} of ${MAX_STARS}`);
    star.append(document.createElement("i"));
    star.addEventListener("click", () => {
      ratings[key] = value;
      paintStars(group, value);
      document.getElementById("feedback-saved").classList.add("d-none");
    });
    group.append(star);
  }
  paintStars(group, ratings[key] || 0);
  body.append(label, group);
  block.append(body);
  return block;
}

// paintStars(group, 3) -> the first three stars filled, the rest empty
function paintStars(group, chosen) {
  group.querySelectorAll(".star").forEach((star) => {
    const filled = Number(star.dataset.value) <= chosen;
    star.firstChild.className = `bi ${filled ? "bi-star-fill" : "bi-star"}`;
    star.setAttribute("aria-checked", Number(star.dataset.value) === chosen ? "true" : "false");
  });
}

async function loadFeedback() {
  hideError("feedback-error");
  try {
    const response = await apiFetch("/api/feedback");
    if (!response) return;
    const data = await response.json();
    if (!response.ok) {
      questionsBox.replaceChildren();
      showError("feedback-error", data.error || "Could not load the questions.");
      return;
    }
    ratings = data.ratings;
    questionsBox.replaceChildren(...data.questions.map((question) => starRating(question.key, question.text)));
  } catch {
    questionsBox.replaceChildren();
    showError("feedback-error", "Cannot reach the server. Check your connection.");
  }
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const stopLoading = startLoading(saveButton);
  if (!stopLoading) return;
  hideError("feedback-error");
  try {
    const response = await apiFetch("/api/feedback", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ratings }),
    });
    if (!response) return;
    const data = await response.json();
    if (!response.ok) {
      showError("feedback-error", data.error || "Could not save your feedback.");
      return;
    }
    document.getElementById("feedback-saved").classList.remove("d-none");
    window.scrollTo({ top: 0 });
  } catch {
    showError("feedback-error", "Cannot reach the server. Check your connection.");
  } finally {
    stopLoading();
  }
});

loadFeedback();
