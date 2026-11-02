// The bell in the student's top bar: shows the unread count, and the notes when it is opened.
// The count is checked again every 45 seconds while the page is on screen.

(function () {
  const list = document.getElementById("bell-list");
  if (!list) return;
  const count = document.getElementById("bell-count");
  const readAll = document.getElementById("bell-read-all");
  const CHECK_EVERY_MS = 45000;

  // timeAgo("2026-11-02 07:00:00") -> "5 min ago" (the time is UTC, from SQLite)
  const timeAgo = (utcText) => {
    const minutes = Math.floor((Date.now() - new Date(utcText.replace(" ", "T") + "Z").getTime()) / 60000);
    if (minutes < 1) return t("Just now");
    if (minutes < 60) return t("{count} min ago", { count: minutes });
    if (minutes < 60 * 24) return t("{count} h ago", { count: Math.floor(minutes / 60) });
    return formatDateTime(utcText);
  };

  // One note: unread ones are bold with a dot. Tapping it marks it read and opens the activity.
  const noteItem = (note) => {
    const item = document.createElement("a");
    item.className = "list-group-item list-group-item-action";
    item.href = note.link || "#";
    const text = document.createElement("div");
    text.className = note.read ? "small" : "small fw-semibold";
    text.textContent = note.text;
    const when = document.createElement("div");
    when.className = "small text-body-secondary";
    when.textContent = timeAgo(note.created_at);
    if (!note.read) {
      const dot = document.createElement("span");
      dot.className = "badge rounded-pill text-bg-primary me-1";
      dot.textContent = " ";
      dot.setAttribute("aria-label", t("Unread"));
      text.prepend(dot);
    }
    item.append(text, when);
    item.addEventListener("click", async (event) => {
      if (note.read) return;
      event.preventDefault(); // finish marking it read first, then go
      try {
        await apiFetch(`/api/notifications/${note.id}/read`, { method: "POST" });
      } catch {
        // going on to the activity matters more than the mark
      }
      if (note.link) window.location.href = note.link;
    });
    return item;
  };

  const show = (data) => {
    count.textContent = data.unread > 9 ? "9+" : String(data.unread);
    count.classList.toggle("d-none", data.unread === 0);
    readAll.classList.toggle("d-none", data.unread === 0);
    if (!data.notifications.length) {
      const empty = document.createElement("div");
      empty.className = "list-group-item small text-body-secondary";
      empty.textContent = t("No notifications yet.");
      list.replaceChildren(empty);
      return;
    }
    list.replaceChildren(...data.notifications.map(noteItem));
  };

  async function load() {
    try {
      const response = await apiFetch("/api/notifications");
      if (!response || !response.ok) return;
      show(await response.json());
    } catch {
      // a lost connection only means the bell is not updated this time
    }
  }

  readAll.addEventListener("click", async () => {
    const stop = startLoading(readAll);
    try {
      await apiFetch("/api/notifications/read-all", { method: "POST" });
      await load();
    } finally {
      stop();
    }
  });

  document.getElementById("bell-button").addEventListener("show.bs.dropdown", load);
  setInterval(() => {
    if (!document.hidden) load();
  }, CHECK_EVERY_MS);
  load();
})();
