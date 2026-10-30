// Eye button next to a password box: shows or hides what was typed.
// Markup: a button with data-toggle-password="<id of the input>".

document.querySelectorAll("[data-toggle-password]").forEach((button) => {
  const input = document.getElementById(button.dataset.togglePassword);
  const icon = button.querySelector("i");
  button.addEventListener("click", () => {
    const show = input.type === "password";
    input.type = show ? "text" : "password";
    icon.className = show ? "bi bi-eye-slash" : "bi bi-eye";
    button.setAttribute("aria-label", show ? t("Hide password") : t("Show password"));
    input.focus();
  });
});
