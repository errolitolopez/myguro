// Teachers and Students pages (admin only, same page): list the accounts, add new ones,
// rename, reset password, deactivate / activate.

const role = document.querySelector("main").dataset.role; // "teacher", "student" or "supervisor"
const noun = role; // "teacher" / "student", used in messages
// One page at a time; search and filters are done on the server.
let page = 1; // the page shown
let pages = 1; // how many pages the current search has
let loadNumber = 0; // only the newest request updates the list (typing fast sends several)
let editing = null; // the person open in the edit popup
let confirmAction = null; // what "Yes" does in the confirm box

const list = document.getElementById("user-list");
const searchInput = document.getElementById("search");
// Advanced filter (students page only): full name, grade, section
const gradeFilter = document.getElementById("grade-filter");
const nameFilter = document.getElementById("name-filter");
const sectionFilter = document.getElementById("section-filter");
const statusFilter = document.getElementById("status-filter");

const addModalElement = document.getElementById("add-user-modal");
const addModal = bootstrap.Modal.getOrCreateInstance(addModalElement);
const addForm = document.getElementById("add-user-form");
const addUsername = document.getElementById("add-username");
const addPassword = document.getElementById("add-password");
const addButton = document.getElementById("add-user-button");

const editModalElement = document.getElementById("edit-user-modal");
const editModal = bootstrap.Modal.getOrCreateInstance(editModalElement);
const editNameButton = document.getElementById("edit-name-button");
const resetButton = document.getElementById("reset-button");
const activeButton = document.getElementById("active-button");
const confirmBox = document.getElementById("confirm-box");
const resetPasswordField = document.getElementById("reset-password-field");
const resetPassword = document.getElementById("reset-password");


// --- List --------------------------------------------------------------------

// One row: name and username on the left, status on the right. Tapping it opens the edit popup.
// textContent is used (not innerHTML) so names can't inject HTML.
function userItem(user) {
  // A div (not a button) so the students page can put a checkbox in it (batch-edit.js).
  const row = document.createElement("div");
  row.tabIndex = 0;
  row.setAttribute("role", "button");
  row.className =
    "list-group-item list-group-item-action d-flex justify-content-between align-items-center gap-2";
  if (!user.active) row.classList.add("text-body-secondary");

  const left = document.createElement("div");
  left.className = "me-auto";
  const name = document.createElement("div");
  name.textContent = user.name;
  // "msantos · 2 classes" (only the username in monospace)
  const details = document.createElement("div");
  details.className = "small text-body-secondary";
  const username = document.createElement("span");
  username.className = "font-monospace";
  username.textContent = user.username;
  const place = gradeSection(user);
  details.append(username, place ? ` · ${place}` : "", ` · ${plural(user.classes, "class", "classes")}`);
  left.append(name, details);

  const badge = document.createElement("span");
  if (!user.active) {
    badge.className = "badge text-bg-secondary";
    badge.textContent = "Deactivated";
  } else if (user.must_change_password) {
    badge.className = "badge text-bg-warning";
    badge.textContent = "Not logged in yet";
    badge.title = "Still using the temporary password";
  } else {
    badge.className = "badge text-bg-success";
    badge.textContent = "Active";
  }

  if (typeof selectionBox === "function") row.append(selectionBox(user)); // students page
  row.append(left, badge);
  row.addEventListener("click", () => openEdit(user));
  row.addEventListener("keydown", (event) => {
    if (event.target === row && (event.key === "Enter" || event.key === " ")) {
      event.preventDefault();
      openEdit(user);
    }
  });
  return row;
}

function messageItem(text) {
  const div = document.createElement("div");
  div.className = "list-group-item text-body-secondary";
  div.textContent = text;
  return div;
}

// How many advanced filter fields are filled in (students page).
function filtersInUse() {
  if (!gradeFilter) return 0;
  return [nameFilter.value.trim() !== "", gradeFilter.value !== "*", sectionFilter.value.trim() !== "",
    statusFilter.value !== ""]
    .filter(Boolean).length;
}

function render(data) {
  const inUse = filtersInUse();
  const searching = searchInput.value.trim() !== "" || inUse > 0;
  const filterCount = document.getElementById("filter-count");
  if (filterCount) {
    filterCount.textContent = inUse;
    filterCount.classList.toggle("d-none", inUse === 0);
  }
  if (data.all_count === 0) {
    list.replaceChildren(messageItem(`No ${noun}s yet. Tap + Add ${noun} to create an account.`));
  } else if (data.users.length === 0) {
    list.replaceChildren(messageItem(`No ${noun} matches your search.`));
  } else {
    list.replaceChildren(...data.users.map(userItem));
  }

  document.getElementById("user-summary").textContent = searching
    ? `${data.total} found`
    : `${data.all_count} total · ${data.active_count} active`;

  // ‹ Prev · Page 2 of 3 · Next ›
  page = data.page;
  pages = data.pages;
  document.getElementById("pager").classList.toggle("d-none", pages <= 1);
  document.getElementById("page-info").textContent = `Page ${page} of ${pages}`;
  document.getElementById("prev-page").disabled = page <= 1;
  document.getElementById("next-page").disabled = page >= pages;
  if (typeof selectionShown === "function") selectionShown(data); // students page
}

// Loads the current page of the search from the server.
async function loadUsers() {
  const thisLoad = ++loadNumber;
  const params = new URLSearchParams({ role, page, q: searchInput.value.trim() });
  if (gradeFilter) {
    if (gradeFilter.value !== "*") params.set("grade", gradeFilter.value);
    if (nameFilter.value.trim()) params.set("name", nameFilter.value.trim());
    if (sectionFilter.value.trim()) params.set("section", sectionFilter.value.trim());
    if (statusFilter.value) params.set("status", statusFilter.value);
  }
  try {
    const response = await apiFetch(`/api/users?${params}`);
    if (!response || thisLoad !== loadNumber) return; // a newer search is on its way
    if (!response.ok) {
      showError("users-error", `Could not load the ${noun}s.`);
      return;
    }
    hideError("users-error");
    render(await response.json());
  } catch {
    showError("users-error", "Cannot reach the server. Check your connection.");
  }
}

function goToPage(newPage) {
  page = newPage;
  loadUsers();
  window.scrollTo({ top: 0 });
}

document.getElementById("prev-page").addEventListener("click", () => goToPage(page - 1));
document.getElementById("next-page").addEventListener("click", () => goToPage(page + 1));

// Search after a short pause in typing, from page 1 again.
let searchTimer = null;
function searchSoon() {
  clearTimeout(searchTimer);
  searchTimer = setTimeout(() => goToPage(1), 250);
}
searchInput.addEventListener("input", searchSoon);
if (gradeFilter) {
  nameFilter.addEventListener("input", searchSoon);
  sectionFilter.addEventListener("input", searchSoon);
  gradeFilter.addEventListener("change", () => goToPage(1));
  statusFilter.addEventListener("change", () => goToPage(1));
  document.getElementById("filter-clear").addEventListener("click", () => {
    nameFilter.value = "";
    sectionFilter.value = "";
    gradeFilter.value = "*";
    statusFilter.value = "";
    // Same events the boxes send, so batch-edit.js drops "all matching" too.
    gradeFilter.dispatchEvent(new Event("change"));
  });
}

// --- Add account -------------------------------------------------------------

// { grade, section } from the add or edit form (students only; teachers have none).
function gradeSectionValues(prefix) {
  if (role !== "student") return {};
  return {
    grade: document.getElementById(`${prefix}-grade`).value,
    section: document.getElementById(`${prefix}-section`).value.trim(),
  };
}

// The username is suggested from the name until the admin types their own.
let usernameTyped = false;

// While typing the name, suggest a username (until the admin types their own).
for (const box of ["add-last", "add-first"]) {
  document.getElementById(box).addEventListener("input", () => {
    if (!usernameTyped) {
      const name = personNameValues("add");
      addUsername.value = suggestUsername(name.first_name, name.last_name);
    }
  });
}
addUsername.addEventListener("input", () => {
  usernameTyped = addUsername.value !== "";
});

addForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  hideError("add-user-error");

  const name = personNameValues("add");
  const username = addUsername.value.trim().toLowerCase();
  const password = addPassword.value;
  const nameProblem = personNameProblem(name);
  if (nameProblem) {
    showError("add-user-error", nameProblem);
    document.getElementById(name.last_name ? "add-first" : "add-last").focus();
    return;
  }
  if (!/^[a-z0-9._-]{3,30}$/.test(username)) {
    showError("add-user-error",
      "Username must be 3 to 30 letters, numbers, dots, dashes or underscores, with no spaces.");
    addUsername.focus();
    return;
  }
  if (password && password.length < 6) {
    showError("add-user-error", "Password must be at least 6 characters, or leave it empty.");
    addPassword.focus();
    return;
  }

  const stopLoading = startLoading(addButton);
  if (!stopLoading) return;
  try {
    const response = await apiFetch("/api/users", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ role, ...name, username, password, ...gradeSectionValues("add") }),
    });
    if (!response) return;
    const data = await response.json();
    if (!response.ok) {
      showError("add-user-error", data.error || "Could not create the account.");
      return;
    }
    addModal.hide();
    searchInput.value = "";
    await loadUsers();
    showLoginDetails(data.user, data.temp_password);
  } catch {
    showError("add-user-error", "Cannot reach the server. Check your connection.");
  } finally {
    stopLoading();
  }
});

// Start each popup with an empty form, and put the cursor in the name field.
addModalElement.addEventListener("show.bs.modal", () => {
  addForm.reset();
  usernameTyped = false;
  hideError("add-user-error");
});
addModalElement.addEventListener("shown.bs.modal", () => document.getElementById("add-last").focus());

// --- Edit account ------------------------------------------------------------

function openEdit(user) {
  editing = user;
  document.getElementById("edit-user-title").textContent = user.name;
  document.getElementById("edit-username").textContent = user.username;
  setPersonName("edit", user);
  if (role === "student") {
    const gradeSelect = document.getElementById("edit-grade");
    gradeSelect.querySelectorAll("[data-kept]").forEach((option) => option.remove());
    // A disabled grade is not in the list, but the student keeps it unless it is changed.
    if (user.grade && ![...gradeSelect.options].some((option) => option.value === user.grade)) {
      const kept = new Option(`${user.grade} (disabled)`, user.grade);
      kept.dataset.kept = "1";
      gradeSelect.append(kept);
    }
    gradeSelect.value = user.grade;
    document.getElementById("edit-section").value = user.section;
  }
  activeButton.textContent = user.active ? "Deactivate" : "Activate";
  activeButton.className = user.active ? "btn btn-outline-danger" : "btn btn-outline-success";
  resetButton.disabled = !user.active;
  confirmBox.classList.add("d-none");
  hideError("edit-user-error");
  editModal.show();
}

// Sends changes for the person being edited. Returns the server's answer, or null on error.
async function updateUser(changes) {
  hideError("edit-user-error");
  try {
    const response = await apiFetch(`/api/users/${editing.id}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(changes),
    });
    if (!response) return null;
    const data = await response.json();
    if (!response.ok) {
      showError("edit-user-error", data.error || "Could not save.");
      return null;
    }
    await loadUsers();
    return data;
  } catch {
    showError("edit-user-error", "Cannot reach the server. Check your connection.");
    return null;
  }
}

document.getElementById("edit-name-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const name = personNameValues("edit");
  const nameProblem = personNameProblem(name);
  if (nameProblem) {
    showError("edit-user-error", nameProblem);
    return;
  }
  const stopLoading = startLoading(editNameButton);
  if (!stopLoading) return;
  const data = await updateUser({ ...name, ...gradeSectionValues("edit") });
  stopLoading();
  if (data) editModal.hide();
});

function askConfirm(text, yesLabel, action, withPassword = false) {
  document.getElementById("confirm-text").textContent = text;
  resetPasswordField.classList.toggle("d-none", !withPassword);
  resetPassword.value = "";
  document.getElementById("confirm-yes").textContent = yesLabel;
  confirmAction = action;
  confirmBox.classList.remove("d-none");
}

resetButton.addEventListener("click", () => {
  askConfirm(
    `Set a new temporary password for ${editing.name}? Their current password will stop working.`,
    "Reset password",
    async () => {
      const data = await updateUser({ reset_password: true, password: resetPassword.value });
      if (!data) return;
      editModal.hide();
      showLoginDetails(data.user, data.temp_password);
    },
    true,
  );
  resetPassword.focus();
});

activeButton.addEventListener("click", () => {
  if (!editing.active) {
    const stopLoading = startLoading(activeButton);
    if (!stopLoading) return;
    updateUser({ active: true }).then((data) => {
      stopLoading();
      if (data) editModal.hide();
    });
    return;
  }
  askConfirm(
    `Deactivate ${editing.name}? They won't be able to log in. ` +
      (role === "teacher" ? "Their classes and activities are kept."
        : role === "supervisor" ? "They can be enabled again later." : "Their classes and answers are kept."),
    "Deactivate",
    async () => {
      if (await updateUser({ active: false })) editModal.hide();
    },
  );
});

document.getElementById("confirm-no").addEventListener("click", () => {
  confirmBox.classList.add("d-none");
});
document.getElementById("confirm-yes").addEventListener("click", async (event) => {
  const stopLoading = startLoading(event.currentTarget);
  if (!stopLoading) return;
  await confirmAction();
  stopLoading();
  confirmBox.classList.add("d-none");
});

loadUsers();
