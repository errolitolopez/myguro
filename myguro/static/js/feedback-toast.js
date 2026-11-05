// The feedback card at the lower right: it slides in a moment after the page loads, so it is noticed without
// blocking anything, and the X hides it. It is only on the page when the server decided to ask (once each login or
// once a day, as the admin chose), so it does not come back on the next page.

(() => {
  const toast = document.getElementById("feedback-toast");
  if (!toast) return;
  const SHOW_AFTER_MS = 1500;

  setTimeout(() => {
    toast.hidden = false;
    // The next frame, so the browser draws it hidden first and the slide-in plays
    requestAnimationFrame(() => toast.classList.add("feedback-toast-in"));
  }, SHOW_AFTER_MS);

  document.getElementById("feedback-toast-close").addEventListener("click", () => {
    toast.classList.remove("feedback-toast-in");
    setTimeout(() => (toast.hidden = true), 250); // after it has slid out
  });
})();
