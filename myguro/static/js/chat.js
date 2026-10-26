// Navigation chat bubble (teachers): the teacher types where they want to go and gets a button to the page.
// It uses plain fetch, not common.js, so it works on every page whether or not that file is loaded.

(() => {
  const toggle = document.getElementById("chat-toggle");
  const panel = document.getElementById("chat-panel");
  const closeButton = document.getElementById("chat-close");
  const messages = document.getElementById("chat-messages");
  const form = document.getElementById("chat-form");
  const input = document.getElementById("chat-input");
  const send = document.getElementById("chat-send");

  // addMessage("Hello", true) -> a bubble on the right (the teacher's); false -> on the left (MyGuro's)
  const addMessage = (text, mine) => {
    const bubble = document.createElement("div");
    bubble.className = `chat-message ${mine ? "chat-message-mine" : "chat-message-reply"}`;
    bubble.textContent = text;
    messages.append(bubble);
    messages.scrollTop = messages.scrollHeight;
    return bubble;
  };

  // addLink({ label: "Open Classes", url: "/classes" }) -> a button under the reply. The address always
  // comes from the server's own page list; one that is not a path on this site is ignored.
  const addLink = (bubble, link) => {
    if (!link || !link.url.startsWith("/") || link.url.startsWith("//")) return;
    const button = document.createElement("a");
    button.className = "btn btn-sm btn-success bi bi-arrow-right-circle d-block mt-2";
    button.href = link.url;
    button.textContent = ` ${link.label}`;
    bubble.append(button);
  };

  // The greeting is the first thing in an empty chat, so it is never an empty box.
  const showGreeting = () => addMessage("Hi! Tell me which page you are looking for.", false);

  // The saved chat is loaded the first time the panel opens, not on every page.
  let historyLoaded = false;
  const loadHistory = async () => {
    historyLoaded = true;
    try {
      const response = await fetch("/api/chat/history");
      const data = response.ok ? await response.json() : { messages: [] };
      messages.replaceChildren();
      if (!data.messages.length) showGreeting();
      for (const message of data.messages) {
        const bubble = addMessage(message.text, message.sender === "teacher");
        addLink(bubble, message.link);
      }
    } catch {
      historyLoaded = false; // try again the next time it opens
    }
  };

  const open = () => {
    if (!historyLoaded) loadHistory();
    panel.classList.remove("d-none");
    toggle.setAttribute("aria-expanded", "true");
    input.focus();
  };
  const close = () => {
    panel.classList.add("d-none");
    toggle.setAttribute("aria-expanded", "false");
    toggle.focus();
  };

  toggle.addEventListener("click", () => (panel.classList.contains("d-none") ? open() : close()));
  closeButton.addEventListener("click", close);
  panel.addEventListener("keydown", (event) => {
    if (event.key === "Escape") close();
  });

  showGreeting();

  document.getElementById("chat-clear").addEventListener("click", async () => {
    const button = document.getElementById("chat-clear");
    button.disabled = true;
    try {
      const response = await fetch("/api/chat/history", { method: "DELETE" });
      if (response.ok) {
        messages.replaceChildren();
        showGreeting();
      }
    } catch {
      // the history stays; the teacher can try again
    } finally {
      button.disabled = false;
    }
  });

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const text = input.value.trim();
    if (!text || send.disabled) return;
    addMessage(text, true);
    input.value = "";
    send.disabled = true;
    const waiting = addMessage("...", false);
    try {
      const response = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: text }),
      });
      if (response.status === 401) {
        window.location.href = "/login";
        return;
      }
      const data = await response.json().catch(() => ({}));
      if (!response.ok) {
        waiting.textContent = data.error || "The chatbot is not available right now.";
        return;
      }
      waiting.textContent = data.reply;
      addLink(waiting, data.link);
    } catch {
      waiting.textContent = "Cannot reach the server. Check your connection.";
    } finally {
      send.disabled = false;
      messages.scrollTop = messages.scrollHeight;
    }
  });
})();
