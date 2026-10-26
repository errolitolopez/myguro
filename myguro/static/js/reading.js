// Display settings: text size, text alignment, line spacing and whether phones get the menu bar at the bottom. Loaded in <head> so they are set
// before the page is drawn (no jump). A person's choices are kept in this browser only, like the theme.
// They become attributes on <html> (data-text-size, data-text-align, data-line-spacing, data-tab-bar); glass.css
// does the rest.

(function () {
  const OPTIONS = {
    size: { key: "myguro-text-size", attribute: "data-text-size", choices: ["small", "normal", "large", "xlarge"], fallback: "normal" },
    align: { key: "myguro-text-align", attribute: "data-text-align", choices: ["left", "justify"], fallback: "left" },
    spacing: { key: "myguro-line-spacing", attribute: "data-line-spacing", choices: ["normal", "relaxed"], fallback: "normal" },
    tabbar: { key: "myguro-tab-bar", attribute: "data-tab-bar", choices: ["bottom", "top"], fallback: "bottom" },
  };

  // saved(OPTIONS.size) -> "large" (or the fallback when nothing valid is saved)
  function saved(option) {
    try {
      const value = localStorage.getItem(option.key);
      return option.choices.includes(value) ? value : option.fallback;
    } catch {
      return option.fallback;
    }
  }

  function apply(option, value) {
    document.documentElement.setAttribute(option.attribute, value);
  }

  Object.values(OPTIONS).forEach((option) => apply(option, saved(option)));

  document.addEventListener("DOMContentLoaded", () => {
    // A switch is a choice between two values: on = the first of the option's choices.
    document.querySelectorAll("[data-reading-switch]").forEach((box) => {
      const option = OPTIONS[box.dataset.readingSwitch];
      if (!option) return;
      const [on, off] = option.choices;
      box.checked = saved(option) === on;
      box.addEventListener("change", () => {
        const value = box.checked ? on : off;
        try {
          localStorage.setItem(option.key, value);
        } catch {
          // Private window or blocked storage: the choice only lasts for this page.
        }
        apply(option, value);
      });
    });

    document.querySelectorAll("[data-reading-select]").forEach((select) => {
      const option = OPTIONS[select.dataset.readingSelect];
      if (!option) return;
      select.value = saved(option);
      select.addEventListener("change", () => {
        const value = option.choices.includes(select.value) ? select.value : option.fallback;
        try {
          localStorage.setItem(option.key, value);
        } catch {
          // Private window or blocked storage: the choice only lasts for this page.
        }
        apply(option, value);
      });
    });
  });
})();
