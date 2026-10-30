// Language setting: English or Taglish. The choice is a cookie in this browser (never the database): the server
// reads it to draw the page in that language, and common.js t() reads the dictionary the page carries.
// Choosing saves the cookie and reloads, so two languages never mix on one screen.

(function () {
  const COOKIE = "myguro-lang";
  const ONE_YEAR = 31536000; // seconds
  const CHOICES = ["en", "tl"];

  function current() {
    const match = document.cookie.match(new RegExp(`(?:^|; )${COOKIE}=([^;]*)`));
    return match && CHOICES.includes(match[1]) ? match[1] : "en";
  }

  function choose(choice) {
    if (!CHOICES.includes(choice) || choice === current()) return;
    document.cookie = `${COOKIE}=${choice}; max-age=${ONE_YEAR}; path=/; SameSite=Lax`;
    location.reload();
  }

  document.addEventListener("DOMContentLoaded", () => {
    const chosen = current();
    document.querySelectorAll("[data-language-select]").forEach((select) => {
      select.value = chosen;
      select.addEventListener("change", () => choose(select.value));
    });
    // The quick menu in the navbar: one button per language.
    document.querySelectorAll("[data-language-choice]").forEach((button) => {
      const isCurrent = button.dataset.languageChoice === chosen;
      button.classList.toggle("active", isCurrent);
      button.setAttribute("aria-current", isCurrent ? "true" : "false");
      button.addEventListener("click", () => choose(button.dataset.languageChoice));
    });
  });
})();
