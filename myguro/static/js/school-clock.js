// The school's clock, just under the top bar on the right of every page: Philippine Standard Time, "Thursday, November 5, 2026 at 1:44:42 PM".
// It starts from the server's time, not the device's, so a phone with a wrong clock still shows the school's time:
// the Date header of one small request gives the difference, and that difference is kept.

(() => {
  // Every .school-clock on the page
  const clocks = document.querySelectorAll(".school-clock");
  if (clocks.length === 0) return;
  const ZONE = "Asia/Manila";
  let offset = 0; // milliseconds to add to the device's time to get the server's time

  // schoolClockText(new Date(...)) -> "Thursday, November 5, 2026 at 1:44:42 PM"
  const schoolClockText = (date) => {
    const day = date.toLocaleDateString(undefined, { timeZone: ZONE, weekday: "long", year: "numeric", month: "long", day: "numeric" });
    const time = date.toLocaleTimeString(undefined, { timeZone: ZONE, hour: "numeric", minute: "2-digit", second: "2-digit", hour12: true });
    return `${day} at ${time}`; // the dates in the app are not translated (only the label is)
  };

  const tick = () => {
    const text = schoolClockText(new Date(Date.now() + offset));
    clocks.forEach((clock) => (clock.textContent = text));
  };

  // One request when the page opens. It needs no login (the manifest is open to everyone) and is never cached.
  async function syncWithServer() {
    try {
      const response = await fetch("/manifest.webmanifest", { method: "HEAD", cache: "no-store" });
      const serverTime = Date.parse(response.headers.get("Date"));
      if (!Number.isNaN(serverTime)) offset = serverTime - Date.now();
    } catch {
      // No network: the device's own clock is used
    }
    tick();
  }

  tick();
  syncWithServer();
  const timer = setInterval(tick, 1000);
  // A hidden tab does not need to redraw every second; it catches up when it is shown again.
  document.addEventListener("visibilitychange", () => {
    if (!document.hidden) tick();
  });
  window.addEventListener("pagehide", () => clearInterval(timer));
})();
