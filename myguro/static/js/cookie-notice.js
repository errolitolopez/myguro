// The cookie notice: shown until the person taps OK. The choice is kept in this browser only (localStorage, not a
// cookie, so the notice does not need a cookie of its own).

(() => {
  const KEY = "myguro-cookie-notice";
  const notice = document.getElementById("cookie-notice");
  if (!notice) return;

  let seen = false;
  try {
    seen = localStorage.getItem(KEY) === "1";
  } catch {
    seen = false; // storage blocked: the notice shows on every page, and OK just hides it for this page
  }
  if (seen) return;

  notice.classList.remove("d-none");
  document.getElementById("cookie-ok").addEventListener("click", () => {
    notice.classList.add("d-none");
    try {
      localStorage.setItem(KEY, "1");
    } catch {
      // not remembered
    }
  });
})();
