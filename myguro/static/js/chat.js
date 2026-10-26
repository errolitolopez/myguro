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
  const leftLabel = document.getElementById("chat-left");
  let full = false;

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
  // The questions to tap in an empty chat; they come from the server with the history.
  let suggestions = [];

  // In an empty chat: the greeting and, under it, the suggestions. Tapping one sends it as the question.
  const showGreeting = () => {
    addMessage("Hi, I'm GuroBot! Ask me where a page is or how to do something in MyGuro.", false);
    if (!suggestions.length) return;
    const list = document.createElement("div");
    list.className = "chat-suggestions d-flex flex-wrap gap-2";
    for (const text of suggestions) {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "btn btn-sm btn-outline-success rounded-pill";
      button.textContent = text;
      button.addEventListener("click", () => sendMessage(text));
      list.append(button);
    }
    messages.append(list);
  };

  // The saved chat is loaded the first time the panel opens, not on every page.
  let historyLoaded = false;
  const loadHistory = async () => {
    historyLoaded = true;
    try {
      const response = await fetch("/api/chat/history");
      const data = response.ok ? await response.json() : { messages: [], questions_left: 5, suggestions: [] };
      suggestions = data.suggestions || [];
      messages.replaceChildren();
      if (!data.messages.length) showGreeting();
      for (const message of data.messages) {
        const bubble = addMessage(message.text, message.sender === "teacher");
        addLink(bubble, message.link);
      }
      setLeft(data.questions_left);
    } catch {
      historyLoaded = false; // try again the next time it opens
    }
  };

  // setLeft(2) -> "2 questions left". At 0 the chat is full: the box is turned off and a notice asks the
  // teacher to delete the chat and start a new one (the same as the trash button).
  const setLeft = (left) => {
    full = left === 0;
    leftLabel.textContent = full ? "Chat full" : `${left} ${left === 1 ? "question" : "questions"} left`;
    input.disabled = full;
    send.disabled = full;
    if (full && !messages.querySelector(".chat-full")) {
      const notice = addMessage("This chat is full. Delete it and start a new chat.", false);
      notice.classList.add("chat-full");
      const button = document.createElement("button");
      button.type = "button";
      button.className = "btn btn-sm btn-success bi bi-plus-circle d-block mt-2";
      button.textContent = " Delete and start a new chat";
      button.addEventListener("click", clearChat);
      notice.append(button);
    }
  };

  // The eyes follow the pointer: the distance and direction from the bubble to the pointer, held to a small
  // step, are saved as --look-x / --look-y for the CSS. Not for people who asked for less motion.
  const bubbleBox = document.getElementById("chat-bubble");
  if (!window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
    let waiting = false;
    document.addEventListener("pointermove", (event) => {
      if (waiting) return; // at most once a frame
      waiting = true;
      requestAnimationFrame(() => {
        waiting = false;
        const box = toggle.getBoundingClientRect();
        const dx = event.clientX - (box.left + box.width / 2);
        const dy = event.clientY - (box.top + box.height / 2);
        const distance = Math.hypot(dx, dy) || 1;
        const step = Math.min(1.6, distance / 80); // gets closer to full look as the pointer gets further away
        bubbleBox.style.setProperty("--look-x", ((dx / distance) * step).toFixed(2));
        bubbleBox.style.setProperty("--look-y", ((dy / distance) * step).toFixed(2));
      });
    });
  }

  // Keeps the bubble in the corner of what the person actually sees. A fixed element is anchored to the
  // page's layout width, so when something on a page is wider than the phone (the page then zooms out
  // or can be panned sideways) the bubble ends up at the far right of that wider page, off screen.
  // The visual viewport is the part of the page on the screen: the bubble is moved to its corner and
  // kept at its normal size when the page is zoomed. With nothing wider and no zoom, nothing changes.
  const keepInCorner = () => {
    const view = window.visualViewport;
    if (!view) return;
    const page = document.documentElement;
    const moveX = view.offsetLeft + view.width - page.clientWidth;
    const moveY = view.offsetTop + view.height - page.clientHeight;
    const scale = 1 / view.scale;
    const moved = Math.abs(moveX) > 0.5 || Math.abs(moveY) > 0.5 || Math.abs(scale - 1) > 0.01;
    bubbleBox.style.transformOrigin = "bottom right";
    bubbleBox.style.transform = moved ? `translate(${moveX}px, ${moveY}px) scale(${scale})` : "";
  };
  if (window.visualViewport) {
    let pending = false;
    const soon = () => {
      if (pending) return; // at most once a frame
      pending = true;
      requestAnimationFrame(() => {
        pending = false;
        keepInCorner();
      });
    };
    window.visualViewport.addEventListener("resize", soon);
    window.visualViewport.addEventListener("scroll", soon);
    window.addEventListener("resize", soon);
    window.addEventListener("load", soon);
    // Pages draw their tables after they load, which is when the page can become wider: look again a
    // little later, too.
    setTimeout(soon, 500);
    setTimeout(soon, 2000);
    keepInCorner();
  }

  // The window size is remembered in this browser; if the browser blocks storage it just starts small.
  const sizeButton = document.getElementById("chat-size");
  const setLarge = (large) => {
    panel.classList.toggle("chat-panel-large", large);
    sizeButton.classList.toggle("bi-arrows-angle-expand", !large);
    sizeButton.classList.toggle("bi-arrows-angle-contract", large);
    const label = large ? "Make the chat window smaller" : "Make the chat window bigger";
    sizeButton.setAttribute("aria-label", label);
    sizeButton.title = label;
    messages.scrollTop = messages.scrollHeight;
  };
  try {
    setLarge(localStorage.getItem("chat-large") === "1");
  } catch {
    setLarge(false);
  }
  sizeButton.addEventListener("click", () => {
    const large = !panel.classList.contains("chat-panel-large");
    setLarge(large);
    try {
      localStorage.setItem("chat-large", large ? "1" : "0");
    } catch {
      // not remembered
    }
  });

  const open = () => {
    if (!historyLoaded) loadHistory();
    panel.inert = false;
    panel.classList.add("chat-open");
    toggle.setAttribute("aria-expanded", "true");
    input.focus();
  };
  const close = () => {
    panel.classList.remove("chat-open");
    panel.inert = true; // a closed window can't be tabbed into
    toggle.setAttribute("aria-expanded", "false");
    toggle.focus();
  };

  toggle.addEventListener("click", () => (panel.classList.contains("chat-open") ? close() : open()));
  closeButton.addEventListener("click", close);
  panel.addEventListener("keydown", (event) => {
    if (event.key === "Escape") close();
  });

  showGreeting();

  // Deletes the whole chat; the next question starts a new one.
  async function clearChat() {
    const button = document.getElementById("chat-clear");
    button.disabled = true;
    try {
      const response = await fetch("/api/chat/history", { method: "DELETE" });
      if (response.ok) {
        messages.replaceChildren();
        showGreeting();
        setLeft((await response.json()).questions_left);
        input.focus();
      }
    } catch {
      // the chat stays; the teacher can try again
    } finally {
      button.disabled = false;
    }
  }
  document.getElementById("chat-clear").addEventListener("click", clearChat);

  // Sends one question and shows the reply. The text box and the suggestions both use it.
  async function sendMessage(text) {
    if (!text || send.disabled) return;
    messages.querySelector(".chat-suggestions")?.remove();
    addMessage(text, true);
    input.value = "";
    send.disabled = true;
    const waiting = addMessage("...", false);
    bubbleBox.classList.add("chat-thinking"); // the eyes look side to side while GuroBot thinks
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
        if (data.questions_left === 0) {
          waiting.remove();
          setLeft(0);
        }
        return;
      }
      waiting.textContent = data.reply;
      addLink(waiting, data.link);
      setLeft(data.questions_left);
    } catch {
      waiting.textContent = "Cannot reach the server. Check your connection.";
    } finally {
      bubbleBox.classList.remove("chat-thinking");
      send.disabled = full;
      messages.scrollTop = messages.scrollHeight;
    }
  }

  form.addEventListener("submit", (event) => {
    event.preventDefault();
    sendMessage(input.value.trim());
  });
})();
