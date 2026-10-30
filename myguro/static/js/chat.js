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

  // The round button can be dragged anywhere on the screen and the place is remembered in this browser.
  // The box is anchored by the button's nearest corner (left or right, top or bottom), so the button stays
  // where it is when the window opens: the window grows away from that corner, toward the middle.
  // A press that moves less than DRAG_DISTANCE pixels is still a click that opens the window.
  const DRAG_DISTANCE = 6;
  const EDGE = 8; // the button never goes closer than this to the edge of the screen
  const POSITION_KEY = "chat-position";
  let justDragged = false;

  // place({ h: "right", v: "bottom", x: 16, y: 16 }) -> the button 16px from the right and bottom edges
  const place = ({ h, v, x, y }) => {
    const page = document.documentElement;
    const size = toggle.offsetWidth || 56;
    x = Math.min(Math.max(x, EDGE), page.clientWidth - size - EDGE);
    y = Math.min(Math.max(y, EDGE), page.clientHeight - size - EDGE);
    bubbleBox.style.left = h === "left" ? `${x}px` : "auto";
    bubbleBox.style.right = h === "right" ? `${x}px` : "auto";
    bubbleBox.style.top = v === "top" ? `${y}px` : "auto";
    bubbleBox.style.bottom = v === "bottom" ? `${y}px` : "auto";
    bubbleBox.classList.toggle("chat-left", h === "left");
    bubbleBox.classList.toggle("chat-top", v === "top");
    // The window gets the room that is left on its side of the button.
    const room = page.clientHeight - y - size;
    bubbleBox.style.setProperty("--chat-room", `${room - EDGE * 2}px`);
    return { h, v, x, y };
  };

  // Turns where the button is now into the nearest corner and offsets, and saves them.
  const settle = () => {
    const page = document.documentElement;
    const box = toggle.getBoundingClientRect();
    const h = box.left + box.width / 2 > page.clientWidth / 2 ? "right" : "left";
    const v = box.top + box.height / 2 > page.clientHeight / 2 ? "bottom" : "top";
    const spot = place({
      h,
      v,
      x: h === "left" ? box.left : page.clientWidth - box.right,
      y: v === "top" ? box.top : page.clientHeight - box.bottom,
    });
    try {
      localStorage.setItem(POSITION_KEY, JSON.stringify(spot));
    } catch {
      // not remembered
    }
    return spot;
  };

  let saved = null;
  try {
    saved = JSON.parse(localStorage.getItem(POSITION_KEY));
  } catch {
    saved = null;
  }
  const valid = saved && ["left", "right"].includes(saved.h) && ["top", "bottom"].includes(saved.v)
    && Number.isFinite(saved.x) && Number.isFinite(saved.y);
  if (valid) place(saved);
  // A smaller screen (or a turned phone) must not leave the button outside it.
  window.addEventListener("resize", () => {
    if (bubbleBox.style.left) settle(); // only once the button has been moved
  });

  let drag = null;
  toggle.addEventListener("pointerdown", (event) => {
    if (event.button !== 0) return;
    const box = toggle.getBoundingClientRect();
    drag = { startX: event.clientX, startY: event.clientY, offsetX: event.clientX - box.left,
      offsetY: event.clientY - box.top, moving: false };
    toggle.setPointerCapture(event.pointerId);
  });
  toggle.addEventListener("pointermove", (event) => {
    if (!drag) return;
    if (!drag.moving && Math.hypot(event.clientX - drag.startX, event.clientY - drag.startY) < DRAG_DISTANCE) return;
    drag.moving = true;
    // While dragging the box hangs from the top left; settle() picks the nearest corner on release.
    place({ h: "left", v: "top", x: event.clientX - drag.offsetX, y: event.clientY - drag.offsetY });
  });
  const endDrag = () => {
    if (!drag) return;
    if (drag.moving) {
      settle();
      justDragged = true; // the click that follows the release must not open or close the window
      setTimeout(() => (justDragged = false), 0);
    }
    drag = null;
  };
  toggle.addEventListener("pointerup", endDrag);
  toggle.addEventListener("pointercancel", endDrag);

  // Account menu → Hide / Show GuroBot. Hidden, the bubble and its window are gone from every page until the
  // teacher shows it again (it starts hidden); the choice is kept in this browser only (a hidden chat keeps its history).
  const HIDDEN_KEY = "chat-hidden";
  const visibilityItem = document.getElementById("chat-visibility");
  const setHidden = (hidden) => {
    if (hidden && panel.classList.contains("chat-open")) close();
    bubbleBox.hidden = hidden;
    if (!visibilityItem) return;
    visibilityItem.classList.toggle("bi-eye-slash", !hidden);
    visibilityItem.classList.toggle("bi-eye", hidden);
    visibilityItem.textContent = hidden ? " Show GuroBot" : " Hide GuroBot";
  };
  // Hidden until the teacher chooses Show GuroBot: only a saved "0" (shown) keeps it on the page.
  let startHidden = true;
  try {
    startHidden = localStorage.getItem(HIDDEN_KEY) !== "0";
  } catch {
    startHidden = true;
  }
  visibilityItem?.addEventListener("click", () => {
    const hidden = !bubbleBox.hidden;
    setHidden(hidden);
    try {
      localStorage.setItem(HIDDEN_KEY, hidden ? "1" : "0");
    } catch {
      // not remembered
    }
  });

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

  toggle.addEventListener("click", () => {
    if (justDragged) return;
    panel.classList.contains("chat-open") ? close() : open();
  });
  closeButton.addEventListener("click", close);
  panel.addEventListener("keydown", (event) => {
    if (event.key === "Escape") close();
  });

  setHidden(startHidden);
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
