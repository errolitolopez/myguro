// Students page (admin): select students (on any page, or every student matching the search)
// and change their grade and/or section at once. Works with users.js: it calls selectionBox()
// for each row and selectionShown() after each page loads.

const selected = new Set(); // ids picked one by one (kept when changing page or search)
let allMatching = null; // {q, grade, name, section, status, total}: every student matching that search, on all pages
let shownData = null; // the page on screen (from users.js)

const selectionBar = document.getElementById("selection-bar");
const selectPage = document.getElementById("select-page");
const selectMatching = document.getElementById("select-matching");
const batchModal = bootstrap.Modal.getOrCreateInstance(document.getElementById("batch-modal"));

// The search and filters on screen: {q, grade, name, section, status} (each only when used)
function currentSearch() {
  const search = { q: searchInput.value.trim() };
  if (gradeFilter.value !== "*") search.grade = gradeFilter.value;
  if (nameFilter.value.trim()) search.name = nameFilter.value.trim();
  if (sectionFilter.value.trim()) search.section = sectionFilter.value.trim();
  if (statusFilter.value) search.status = statusFilter.value;
  return search;
}

function selectedCount() {
  return allMatching ? allMatching.total : selected.size;
}

// The checkbox at the start of a row. Clicking it doesn't open the student.
function selectionBox(user) {
  const box = document.createElement("input");
  box.type = "checkbox";
  box.className = "form-check-input mt-0 flex-shrink-0";
  box.setAttribute("aria-label", `Select ${user.name}`);
  box.checked = Boolean(allMatching) || selected.has(user.id);
  box.disabled = Boolean(allMatching);
  box.addEventListener("click", (event) => event.stopPropagation());
  box.addEventListener("keydown", (event) => event.stopPropagation());
  box.addEventListener("change", () => {
    if (box.checked) selected.add(user.id);
    else selected.delete(user.id);
    showSelection();
  });
  return box;
}

function selectionShown(data) {
  shownData = data;
  showSelection();
}

// The bar, the "select all on this page" box, and the "Select all N matching" link.
function showSelection() {
  const count = selectedCount();
  selectionBar.classList.toggle("d-none", count === 0);
  document.getElementById("selection-text").textContent = allMatching
    ? `All ${plural(allMatching.total, "student")} matching the search are selected.`
    : `${plural(count, "student")} selected.`;

  const pageIds = shownData ? shownData.users.map((user) => user.id) : [];
  const onPage = pageIds.filter((id) => selected.has(id)).length;
  selectPage.checked = Boolean(allMatching) || (pageIds.length > 0 && onPage === pageIds.length);
  selectPage.indeterminate = !allMatching && onPage > 0 && onPage < pageIds.length;
  selectPage.disabled = Boolean(allMatching) || pageIds.length === 0;

  // Whole page selected and there are more on other pages: offer all of them.
  const more = shownData && !allMatching && onPage === pageIds.length && pageIds.length > 0
    && shownData.total > pageIds.length;
  selectMatching.classList.toggle("d-none", !more);
  if (more) selectMatching.textContent = `Select all ${shownData.total} matching`;
}

// Draws the rows again (from users.js) with their boxes checked or not.
function redrawChecks() {
  if (shownData) loadUsers();
}

selectPage.addEventListener("change", () => {
  for (const user of shownData.users) {
    if (selectPage.checked) selected.add(user.id);
    else selected.delete(user.id);
  }
  redrawChecks();
});

selectMatching.addEventListener("click", () => {
  allMatching = { ...currentSearch(), total: shownData.total };
  redrawChecks();
});

function clearSelection() {
  selected.clear();
  allMatching = null;
  redrawChecks();
}

document.getElementById("selection-clear").addEventListener("click", clearSelection);

// A different search: "all matching" no longer means the same students.
for (const box of [searchInput, nameFilter, sectionFilter]) {
  box.addEventListener("input", () => {
    if (allMatching) clearSelection();
  });
}
for (const select of [gradeFilter, statusFilter]) {
  select.addEventListener("change", () => {
    if (allMatching) clearSelection();
  });
}

// --- The popup --------------------------------------------------------------------

const batchForm = document.getElementById("batch-form");
const sectionInput = document.getElementById("batch-section");

document.getElementById("batch-modal").addEventListener("show.bs.modal", () => {
  batchForm.reset();
  hideError("batch-error");
  document.getElementById("batch-who").textContent = allMatching
    ? `Change all ${plural(allMatching.total, "student")} matching the search.`
    : `Change ${plural(selected.size, "selected student")}.`;
});

// Typing a section picks "Set to".
sectionInput.addEventListener("input", () => {
  document.getElementById("batch-section-set").checked = true;
});

batchForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  hideError("batch-error");
  const body = allMatching ? { match: {
    q: allMatching.q, grade: allMatching.grade, name: allMatching.name, section: allMatching.section,
    status: allMatching.status,
  } } : { user_ids: [...selected] };
  const grade = document.getElementById("batch-grade").value;
  if (grade !== "*") body.grade = grade;
  const mode = batchForm.querySelector('input[name="batch-section-mode"]:checked').value;
  if (mode === "set") {
    if (!sectionInput.value.trim()) {
      showError("batch-error", "Type the section, or choose another option.");
      sectionInput.focus();
      return;
    }
    body.section = sectionInput.value.trim();
  } else if (mode === "clear") {
    body.section = "";
  }
  if (!("grade" in body) && !("section" in body)) {
    showError("batch-error", "Choose a grade or section to change.");
    return;
  }

  const save = document.getElementById("batch-save");
  const stopLoading = startLoading(save);
  if (!stopLoading) return;
  try {
    const response = await apiFetch("/api/users/batch", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    if (!response) return;
    const data = await response.json();
    if (!response.ok) {
      showError("batch-error", data.error || "Could not save.");
      return;
    }
    batchModal.hide();
    const notice = document.getElementById("users-notice");
    notice.textContent = `${plural(data.updated, "student")} updated.`;
    notice.classList.remove("d-none");
    setTimeout(() => notice.classList.add("d-none"), 4000);
    clearSelection();
  } catch {
    showError("batch-error", "Cannot reach the server. Check your connection.");
  } finally {
    stopLoading();
  }
});

// --- Delete -----------------------------------------------------------------------

const deleteModal = bootstrap.Modal.getOrCreateInstance(document.getElementById("delete-modal"));

document.getElementById("delete-modal").addEventListener("show.bs.modal", () => {
  hideError("delete-error");
  document.getElementById("delete-who").textContent = allMatching
    ? `Delete all ${plural(allMatching.total, "student")} matching the search?`
    : `Delete ${plural(selected.size, "selected student")}?`;
});

document.getElementById("delete-confirm").addEventListener("click", async (event) => {
  hideError("delete-error");
  const body = allMatching ? { match: {
    q: allMatching.q, grade: allMatching.grade, name: allMatching.name, section: allMatching.section,
    status: allMatching.status,
  } } : { user_ids: [...selected] };
  const button = event.target;
  const stopLoading = startLoading(button);
  if (!stopLoading) return;
  try {
    const response = await apiFetch("/api/users/batch-delete", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    if (!response) return;
    const data = await response.json();
    if (!response.ok) {
      showError("delete-error", data.error || "Could not delete.");
      return;
    }
    deleteModal.hide();
    const notice = document.getElementById("users-notice");
    notice.textContent = `${plural(data.deleted, "student")} deleted.` +
      (data.skipped ? ` ${plural(data.skipped, "student")} skipped: already activated once.` : "");
    notice.classList.remove("d-none");
    setTimeout(() => notice.classList.add("d-none"), 6000);
    clearSelection();
  } catch {
    showError("delete-error", "Cannot reach the server. Check your connection.");
  } finally {
    stopLoading();
  }
});

// --- Activate ---------------------------------------------------------------------

document.getElementById("batch-activate").addEventListener("click", async (event) => {
  const body = allMatching ? { match: {
    q: allMatching.q, grade: allMatching.grade, name: allMatching.name, section: allMatching.section,
    status: allMatching.status,
  } } : { user_ids: [...selected] };
  const button = event.target;
  const notice = document.getElementById("users-notice");
  const stopLoading = startLoading(button);
  if (!stopLoading) return;
  try {
    const response = await apiFetch("/api/users/batch-activate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    if (!response) return;
    const data = await response.json();
    if (!response.ok) {
      showError("users-error", data.error || "Could not activate.");
      return;
    }
    hideError("users-error");
    notice.textContent = `${plural(data.activated, "student")} activated.` +
      (data.skipped ? ` ${plural(data.skipped, "student")} skipped: already active.` : "");
    notice.classList.remove("d-none");
    setTimeout(() => notice.classList.add("d-none"), 6000);
    clearSelection();
  } catch {
    showError("users-error", "Cannot reach the server. Check your connection.");
  } finally {
    stopLoading();
  }
});

// --- New passwords ----------------------------------------------------------------

const passwordModal = document.getElementById("password-modal");
const passwordConfirmButton = document.getElementById("password-confirm");
let newPasswords = []; // the students and their new passwords, kept only while the popup is open

// Each time it opens: ask first.
passwordModal.addEventListener("show.bs.modal", () => {
  hideError("password-error");
  newPasswords = [];
  document.getElementById("password-confirm-part").classList.remove("d-none");
  document.getElementById("password-done-part").classList.add("d-none");
  passwordConfirmButton.classList.remove("d-none");
  document.getElementById("password-who").textContent = allMatching
    ? `Make new passwords for all ${plural(allMatching.total, "student")} matching the search?`
    : `Make new passwords for ${plural(selected.size, "selected student")}?`;
});

passwordConfirmButton.addEventListener("click", async () => {
  hideError("password-error");
  const body = allMatching ? { match: {
    q: allMatching.q, grade: allMatching.grade, name: allMatching.name, section: allMatching.section,
    status: allMatching.status,
  } } : { user_ids: [...selected] };
  const stopLoading = startLoading(passwordConfirmButton);
  if (!stopLoading) return;
  try {
    const response = await apiFetch("/api/users/batch-reset-passwords", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    if (!response) return;
    const data = await response.json();
    if (!response.ok) {
      showError("password-error", data.error || "Could not make new passwords.");
      return;
    }
    newPasswords = data.students;
    document.getElementById("password-done-text").textContent =
      `${plural(newPasswords.length, "new password")} made.`;
    document.getElementById("password-done-rows").replaceChildren(...newPasswords.map((student) => {
      const row = document.createElement("tr");
      for (const value of [student.name, student.username, student.password, student.grade, student.section]) {
        const cell = document.createElement("td");
        cell.textContent = value;
        row.append(cell);
      }
      return row;
    }));
    document.getElementById("password-confirm-part").classList.add("d-none");
    document.getElementById("password-done-part").classList.remove("d-none");
    passwordConfirmButton.classList.add("d-none");
  } catch {
    showError("password-error", "Cannot reach the server. Check your connection.");
  } finally {
    stopLoading();
  }
});

document.getElementById("password-download").addEventListener("click", () => downloadLoginDetails(newPasswords));

// The passwords are gone once the popup closes (the server never keeps them).
passwordModal.addEventListener("hidden.bs.modal", () => {
  newPasswords = [];
  document.getElementById("password-done-rows").replaceChildren();
});
