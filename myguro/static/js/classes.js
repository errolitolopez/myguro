// Teacher's classes: list them (tap to open) and create new ones.

const list = document.getElementById("class-list");
const modalElement = document.getElementById("class-modal");
const modal = bootstrap.Modal.getOrCreateInstance(modalElement);
const form = document.getElementById("class-form");
const nameInput = document.getElementById("class-name");
const sectionInput = document.getElementById("class-section");
const subjectInput = document.getElementById("class-subject");
const saveButton = document.getElementById("class-save-button");

function classItem(item) {
  const row = document.createElement("a");
  row.href = `/classes/${item.id}`;
  row.className = "list-group-item list-group-item-action";

  const name = document.createElement("div");
  name.className = "fw-semibold";
  name.textContent = classTitle(item);
  const details = document.createElement("div");
  details.className = "small text-body-secondary";
  details.textContent =
    `${plural(item.students, "student")} · ${plural(item.activities, "activity", "activities")}`;

  row.append(name, details);
  return row;
}

async function loadClasses() {
  try {
    const response = await apiFetch("/api/classes");
    if (!response) return;
    if (!response.ok) {
      showError("classes-error", t("Could not load your classes."));
      return;
    }
    hideError("classes-error");
    const { classes } = await response.json();
    if (classes.length === 0) {
      const empty = document.createElement("div");
      empty.className = "list-group-item text-body-secondary";
      empty.textContent = t("No classes yet. Tap + New class to create one.");
      list.replaceChildren(empty);
    } else {
      list.replaceChildren(...classes.map(classItem));
    }
  } catch {
    showError("classes-error", t("Cannot reach the server. Check your connection."));
  }
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  hideError("class-form-error");

  const name = joinClassName(nameInput.value, sectionInput.value);
  if (!nameInput.value) {
    showError("class-form-error", t("Select a grade."));
    nameInput.focus();
    return;
  }
  if (!sectionInput.value.trim()) {
    showError("class-form-error", t("Section is required."));
    sectionInput.focus();
    return;
  }

  const stopLoading = startLoading(saveButton);
  if (!stopLoading) return;
  try {
    const response = await apiFetch("/api/classes", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name, subject: subjectInput.value.trim() }),
    });
    if (!response) return;
    const data = await response.json();
    if (!response.ok) {
      showError("class-form-error", data.error || t("Could not save the class."));
      return;
    }
    // Open the new class right away so the teacher can add students.
    window.location.href = `/classes/${data.class.id}`;
  } catch {
    showError("class-form-error", t("Cannot reach the server. Check your connection."));
  } finally {
    stopLoading();
  }
});

modalElement.addEventListener("show.bs.modal", () => {
  form.reset();
  hideError("class-form-error");
});
modalElement.addEventListener("shown.bs.modal", () => nameInput.focus());

loadClasses();
