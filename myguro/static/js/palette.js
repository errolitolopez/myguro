// Quick jump (Ctrl+K, or / when no box is focused): a search box over the pages of the role and, for
// teachers and students, their classes and activities. Pick with the arrow keys and Enter, or tap.
// The lists come from the same APIs the pages use and are fetched once, the first time it opens.

(function () {
  const dialog = document.getElementById("palette");
  if (!dialog) return;
  const input = document.getElementById("palette-input");
  const list = document.getElementById("palette-list");
  const role = dialog.dataset.role;
  const pages = JSON.parse(dialog.dataset.pages);

  let items = pages.map((page) => ({ label: page.label, icon: page.icon, kind: "Page", href: page.href }));
  let loaded = false;
  let shown = [];
  let active = 0;

  // Fetches the person's own lists once; a failed fetch just leaves the pages.
  async function loadItems() {
    if (loaded) return;
    loaded = true;
    try {
      if (role === "teacher") {
        const [classes, activities] = await Promise.all([fetch("/api/classes"), fetch("/api/activities")]);
        if (classes.ok) {
          (await classes.json()).classes.forEach((item) =>
            items.push({ label: typeof classTitle === "function" ? classTitle(item) : item.name, icon: "bi-mortarboard", kind: "Class", href: `/classes/${item.id}` }));
        }
        if (activities.ok) {
          (await activities.json()).activities.forEach((item) =>
            items.push({ label: item.title, icon: "bi-journal-text", kind: "Activity", href: `/activities/${item.id}` }));
        }
      } else if (role === "student") {
        const response = await fetch("/api/my-activities");
        if (response.ok) {
          (await response.json()).activities.forEach((item) =>
            items.push({ label: item.title, icon: "bi-journal-text", kind: "Activity", href: `/my-activities/${item.id}` }));
        }
      }
    } catch {
      // Offline: the pages still work.
    }
    render();
  }

  function render() {
    const words = input.value.toLowerCase().split(/\s+/).filter(Boolean);
    shown = items.filter((item) => words.every((word) => item.label.toLowerCase().includes(word))).slice(0, 12);
    active = Math.min(active, Math.max(shown.length - 1, 0));
    if (shown.length === 0) {
      const empty = document.createElement("li");
      empty.className = "palette-empty";
      empty.textContent = "Nothing found.";
      list.replaceChildren(empty);
      return;
    }
    list.replaceChildren(...shown.map((item, index) => {
      const row = document.createElement("li");
      const link = document.createElement("a");
      link.className = `palette-item${index === active ? " active" : ""}`;
      link.href = item.href;
      const icon = document.createElement("i");
      icon.className = `bi ${item.icon}`;
      icon.setAttribute("aria-hidden", "true");
      const label = document.createElement("span");
      label.textContent = item.label;
      const kind = document.createElement("span");
      kind.className = "palette-kind";
      kind.textContent = item.kind;
      link.append(icon, label, kind);
      row.append(link);
      return row;
    }));
  }

  function open() {
    input.value = "";
    active = 0;
    render();
    dialog.showModal();
    input.focus();
    loadItems();
  }

  input.addEventListener("input", () => {
    active = 0;
    render();
  });
  input.addEventListener("keydown", (event) => {
    if (event.key === "ArrowDown" || event.key === "ArrowUp") {
      event.preventDefault();
      if (shown.length === 0) return;
      active = (active + (event.key === "ArrowDown" ? 1 : -1) + shown.length) % shown.length;
      render();
      list.querySelector(".active").scrollIntoView({ block: "nearest" });
    } else if (event.key === "Enter" && shown[active]) {
      window.location.href = shown[active].href;
    }
  });
  // A click outside the box closes it (the click lands on the dialog itself, the backdrop).
  dialog.addEventListener("click", (event) => {
    if (event.target === dialog) dialog.close();
  });

  document.addEventListener("keydown", (event) => {
    const typing = /^(INPUT|TEXTAREA|SELECT)$/.test(document.activeElement.tagName)
      || document.activeElement.isContentEditable;
    const wantsOpen = (event.key.toLowerCase() === "k" && (event.ctrlKey || event.metaKey))
      || (event.key === "/" && !typing && !event.ctrlKey && !event.metaKey);
    if (wantsOpen && !dialog.open) {
      event.preventDefault();
      open();
    }
  });
  const button = document.getElementById("palette-button");
  if (button) button.addEventListener("click", open);
})();
