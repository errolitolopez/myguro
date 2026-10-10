// Teachers and Students pages (admin only, same page): list the accounts, add new ones,
// rename, reset password, deactivate / activate.

const role = document.querySelector("main").dataset.role; // "teacher" or "student"
const noun = role; // "teacher" / "student", used in messages
let users = []; // all accounts of this role from the server; the search filters them here
let editing = null; // the person open in the edit popup
let confirmAction = null; // what "Yes" does in the confirm box

const list = document.getElementById("user-list");
const searchInput = document.getElementById("search");
const gradeFilter = document.getElementById("grade-filter"); // students page only

const addModalElement = document.getElementById("add-user-modal");
const addModal = bootstrap.Modal.getOrCreateInstance(addModalElement);
const addForm = document.getElementById("add-user-form");
const addName = document.getElementById("add-name");
const addUsername = document.getElementById("add-username");
const addPassword = document.getElementById("add-password");
const addButton = document.getElementById("add-user-button");

const editModalElement = document.getElementById("edit-user-modal");
const editModal = bootstrap.Modal.getOrCreateInstance(editModalElement);
const editName = document.getElementById("edit-name");
const editNameButton = document.getElementById("edit-name-button");
const resetButton = document.getElementById("reset-button");
const activeButton = document.getElementById("active-button");
const confirmBox = document.getElementById("confirm-box");


// --- List --------------------------------------------------------------------

// One row: name and username on the left, status on the right. Tapping it opens the edit popup.
// textContent is used (not innerHTML) so names can't inject HTML.
function userItem(user) {
  const row = document.createElement("button");
  row.type = "button";
  row.className =
    "list-group-item list-group-item-action d-flex justify-content-between align-items-center";
  if (!user.active) row.classList.add("text-body-secondary");

  const left = document.createElement("div");
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

  row.append(left, badge);
  row.addEventListener("click", () => openEdit(user));
  return row;
}

function messageItem(text) {
  const div = document.createElement("div");
  div.className = "list-group-item text-body-secondary";
  div.textContent = text;
  return div;
}

function render() {
  const query = searchInput.value.trim().toLowerCase();
  const grade = gradeFilter ? gradeFilter.value : "*"; // "*" = all grades, "" = no grade
  const shown = users.filter(
    (user) =>
      (grade === "*" || user.grade === grade) &&
      (user.name.toLowerCase().includes(query) ||
        user.username.includes(query) ||
        user.section.toLowerCase().includes(query)),
  );

  if (users.length === 0) {
    list.replaceChildren(messageItem(`No ${noun}s yet. Tap + Add ${noun} to create an account.`));
  } else if (shown.length === 0) {
    list.replaceChildren(messageItem(`No ${noun} matches your search.`));
  } else {
    list.replaceChildren(...shown.map(userItem));
  }

  const active = users.filter((user) => user.active).length;
  document.getElementById("user-summary").textContent = query || grade !== "*"
    ? `${shown.length} found`
    : `${users.length} total · ${active} active`;
}

async function loadUsers() {
  try {
    const response = await apiFetch(`/api/users?role=${role}`);
    if (!response) return;
    if (!response.ok) {
      showError("users-error", `Could not load the ${noun}s.`);
      return;
    }
    hideError("users-error");
    users = (await response.json()).users;
    render();
  } catch {
    showError("users-error", "Cannot reach the server. Check your connection.");
  }
}

searchInput.addEventListener("input", render);
if (gradeFilter) gradeFilter.addEventListener("change", render);

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

addName.addEventListener("input", () => {
  if (!usernameTyped) addUsername.value = suggestUsername(addName.value);
});
addUsername.addEventListener("input", () => {
  usernameTyped = addUsername.value !== "";
});

addForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  hideError("add-user-error");

  const name = addName.value.trim();
  const username = addUsername.value.trim().toLowerCase();
  const password = addPassword.value;
  if (!name) {
    showError("add-user-error", "Full name is required.");
    addName.focus();
    return;
  }
  if (!/^[a-z0-9._-]{3,30}$/.test(username)) {
    showError("add-user-error",
      "Username must be 3 to 30 letters, numbers, dots, dashes or underscores, with no spaces.");
    addUsername.focus();
    return;
  }
  if (password && password.length < 8) {
    showError("add-user-error", "Password must be at least 8 characters, or leave it empty.");
    addPassword.focus();
    return;
  }

  addButton.disabled = true;
  try {
    const response = await apiFetch("/api/users", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ role, name, username, password, ...gradeSectionValues("add") }),
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
    addButton.disabled = false;
  }
});

// Start each popup with an empty form, and put the cursor in the name field.
addModalElement.addEventListener("show.bs.modal", () => {
  addForm.reset();
  usernameTyped = false;
  hideError("add-user-error");
});
addModalElement.addEventListener("shown.bs.modal", () => addName.focus());

// --- Edit account ------------------------------------------------------------

function openEdit(user) {
  editing = user;
  document.getElementById("edit-user-title").textContent = user.name;
  document.getElementById("edit-username").textContent = user.username;
  editName.value = user.name;
  if (role === "student") {
    document.getElementById("edit-grade").value = user.grade;
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
  const name = editName.value.trim();
  if (!name) {
    showError("edit-user-error", "Full name is required.");
    return;
  }
  editNameButton.disabled = true;
  const data = await updateUser({ name, ...gradeSectionValues("edit") });
  editNameButton.disabled = false;
  if (data) editModal.hide();
});

function askConfirm(text, yesLabel, action) {
  document.getElementById("confirm-text").textContent = text;
  document.getElementById("confirm-yes").textContent = yesLabel;
  confirmAction = action;
  confirmBox.classList.remove("d-none");
}

resetButton.addEventListener("click", () => {
  askConfirm(
    `Make a new temporary password for ${editing.name}? Their current password will stop working.`,
    "Reset password",
    async () => {
      const data = await updateUser({ reset_password: true });
      if (!data) return;
      editModal.hide();
      showLoginDetails(data.user, data.temp_password);
    },
  );
});

activeButton.addEventListener("click", () => {
  if (!editing.active) {
    activeButton.disabled = true;
    updateUser({ active: true }).then((data) => {
      activeButton.disabled = false;
      if (data) editModal.hide();
    });
    return;
  }
  askConfirm(
    `Deactivate ${editing.name}? They won't be able to log in. ` +
      (role === "teacher" ? "Their classes and activities are kept." : "Their classes and answers are kept."),
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
  event.target.disabled = true;
  await confirmAction();
  event.target.disabled = false;
  confirmBox.classList.add("d-none");
});

loadUsers();
