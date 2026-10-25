// Colour theme. Loaded in <head> so the theme is set before the page is drawn (no flash).
// "auto" follows the device; a person's choice is kept in this browser only.
// Every theme is built on Bootstrap's light or dark mode (data-bs-theme); the named themes
// (Darcula, Solarized) then change the colours on top of it (data-myguro-theme, see glass.css).

(function () {
  const KEY = "myguro-theme";
  const CHOICES = ["auto", "light", "dark", "darcula", "solarized"];
  // Which Bootstrap mode each named theme starts from.
  const BASE = { light: "light", dark: "dark", darcula: "dark", solarized: "light" };
  const dark = window.matchMedia("(prefers-color-scheme: dark)");

  function saved() {
    try {
      const value = localStorage.getItem(KEY);
      return CHOICES.includes(value) ? value : "auto";
    } catch {
      return "auto";
    }
  }

  function apply(choice) {
    const theme = choice === "auto" ? (dark.matches ? "dark" : "light") : choice;
    document.documentElement.setAttribute("data-bs-theme", BASE[theme]);
    document.documentElement.setAttribute("data-myguro-theme", theme);
  }

  // No colour animation while the first theme is applied (removed once the page has loaded).
  document.documentElement.classList.add("preload");
  window.addEventListener("load", () => {
    requestAnimationFrame(() => document.documentElement.classList.remove("preload"));
  });

  apply(saved());
  dark.addEventListener("change", () => apply(saved()));

  document.addEventListener("DOMContentLoaded", () => {
    document.querySelectorAll("[data-theme-select]").forEach((select) => {
      select.value = saved();
      select.addEventListener("change", () => {
        const choice = CHOICES.includes(select.value) ? select.value : "auto";
        try {
          localStorage.setItem(KEY, choice);
        } catch {
          // Private window or blocked storage: the choice only lasts for this page.
        }
        apply(choice);
      });
    });
  });
})();
