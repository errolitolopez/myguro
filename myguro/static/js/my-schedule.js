// A teacher's own weekly schedule, once the admin has published it.

async function loadSchedule() {
  try {
    const response = await apiFetch("/api/my-schedule");
    if (!response) return;
    if (!response.ok) {
      showError("schedule-error", t("Could not load your schedule."));
      return;
    }
    const data = await response.json();
    const empty = document.getElementById("schedule-empty");
    document.getElementById("schedule-table").classList.toggle("d-none", !data.available);
    empty.classList.toggle("d-none", data.available);
    if (!data.available) {
      empty.textContent = t("Your schedule is not ready yet. The admin will publish it here.");
      return;
    }
    document.getElementById("schedule-details").textContent = data.details;
    scheduleGrid(data, teacherCell);
  } catch {
    showError("schedule-error", t("Cannot reach the server. Check your connection."));
  }
}

loadSchedule();
