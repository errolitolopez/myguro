// A short tip in a closable box under the navbar, a new one every few days.
// Which tip is next and whether it was closed is kept in this browser only.

(function () {
  const STATE_KEY = "myguro-tips";
  const OFF_KEY = "myguro-tips-off";
  const DAYS_BETWEEN_TIPS = 3;

  const TIPS = {
    teacher: [
      t("Tap Save in the activity editor often. It warns you if you leave with unsaved changes."),
      t("An activity you give to a class starts as Not started. Tap Open on the Check results card when students may answer. Close it to submit all work and keep it for review."),
      t("An activity students already submitted is locked. Use Make a copy in the editor to change it."),
      t("Scores stay hidden from students until you tap Release scores on the results page."),
      t("You can import a whole activity from Word on the Activities page."),
      t("A student answered on paper? Enter a paper score on the results page."),
      t("A student was absent? Exclude them from the assignment on the results page."),
      t("On the gradebook, swipe the table sideways to see every activity. Turning your phone sideways shows more."),
      t("Need a paper copy? Tap Print in the activity editor for a student copy or an answer key."),
      t("Deleted an assigned activity by mistake? Open Deleted on the Activities page and tap Restore."),
    ],
    student: [
      t("Your answers save as you go. You can also tap Save progress."),
      t("You can submit only once per try, so check for unanswered questions first."),
      t("Some activities let you try again after you submit."),
      t("Your score can stay hidden until your teacher releases it."),
      t("Late work is still accepted. It is marked Late."),
    ],
  };

  // The Settings page lists these so the admin can preview them.
  window.myguroTips = TIPS;

  // Whole days since 1970 in the browser's own time zone: used to count days between tips.
  function today() {
    return Math.floor((Date.now() - new Date().getTimezoneOffset() * 60000) / 86400000);
  }

  // load() -> {index: 2, shownOn: 20373, closed: false}, or a fresh state when nothing is saved
  function load() {
    try {
      const state = JSON.parse(localStorage.getItem(STATE_KEY));
      if (state && Number.isInteger(state.index) && Number.isInteger(state.shownOn)) return state;
    } catch {
      // Nothing saved, or storage is blocked: start fresh.
    }
    return { index: -1, shownOn: 0, closed: true };
  }

  function save(state) {
    try {
      localStorage.setItem(STATE_KEY, JSON.stringify(state));
    } catch {
      // Storage blocked: the tip will just show again on the next page.
    }
  }

  function tipsAreOff() {
    try {
      return localStorage.getItem(OFF_KEY) === "1";
    } catch {
      return false;
    }
  }

  document.addEventListener("DOMContentLoaded", () => {
    const box = document.getElementById("tip-box");
    if (!box || tipsAreOff()) return;
    const tips = TIPS[box.dataset.role];
    if (!tips) return;

    // A new tip once DAYS_BETWEEN_TIPS days have passed; until then the same one, unless closed.
    let state = load();
    if (today() - state.shownOn >= DAYS_BETWEEN_TIPS) {
      state = { index: (state.index + 1) % tips.length, shownOn: today(), closed: false };
      save(state);
    }
    if (state.closed) return;

    const text = document.createElement("span");
    text.textContent = tips[state.index % tips.length];

    const strong = document.createElement("strong");
    strong.textContent = t("Tip: ");

    const stop = document.createElement("button");
    stop.type = "button";
    // Under the tip on its own line: beside it, on a phone, it wraps badly next to the close button.
    stop.className = "btn btn-link btn-sm p-0 d-block mt-1";
    stop.textContent = t("Don't show tips");
    stop.addEventListener("click", () => {
      try {
        localStorage.setItem(OFF_KEY, "1");
      } catch {
        // Storage blocked: the tips cannot be turned off, but this one can still be closed.
      }
      box.classList.add("d-none");
    });

    const close = document.createElement("button");
    close.type = "button";
    close.className = "btn-close";
    close.setAttribute("aria-label", t("Close tip"));
    close.addEventListener("click", () => {
      save({ ...state, closed: true });
      box.classList.add("d-none");
    });

    const alert = document.createElement("div");
    alert.className = "alert alert-info alert-dismissible mt-3 mb-0 small";
    alert.setAttribute("role", "status");
    alert.append(strong, text, stop, close);

    box.replaceChildren(alert);
    box.classList.remove("d-none");
  });
})();
