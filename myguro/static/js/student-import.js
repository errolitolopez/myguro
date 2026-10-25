// Students page (admin): import students from an Excel file. Check file -> preview or the
// problems by row -> Import -> the new accounts with passwords, and a file to download.
// Uses page and loadUsers() from users.js to refresh the list afterwards.

const importModalElement = document.getElementById("import-modal");
const importFile = document.getElementById("import-file");
const checkButton = document.getElementById("import-check");
const confirmButton = document.getElementById("import-confirm");
let createdStudents = []; // after importing, for the login details download

function importPart(id, show) {
  document.getElementById(id).classList.toggle("d-none", !show);
}

function tableRow(values) {
  const row = document.createElement("tr");
  for (const value of values) {
    const cell = document.createElement("td");
    cell.textContent = value;
    row.append(cell);
  }
  return row;
}

// Sends the chosen file. dryRun = only check it.
async function sendFile(dryRun) {
  const form = new FormData();
  form.append("file", importFile.files[0]);
  form.append("dry_run", dryRun ? "1" : "0");
  const response = await apiFetch("/api/users/import", { method: "POST", body: form });
  if (!response) return null;
  const data = await response.json();
  if (!response.ok) {
    showError("import-error", data.error || "Could not read the file.");
    return null;
  }
  return data;
}

// The students who already exist (same name, grade and section): skipped, not created again.
function showExisting(existing) {
  importPart("import-existing", existing.length > 0);
  document.getElementById("import-existing-text").textContent =
    `${plural(existing.length, "student")} already exist${existing.length === 1 ? "s" : ""} ` +
    "(same name, grade and section) and will be skipped.";
  document.getElementById("import-existing-rows").replaceChildren(...existing.map((student) =>
    tableRow([student.row, student.name, student.username, student.grade, student.section])));
}

function showProblems(errors) {
  document.getElementById("import-problem-list").replaceChildren(...errors.map((problem) => {
    const item = document.createElement("li");
    item.textContent = `Row ${problem.row}: ${problem.message}`;
    return item;
  }));
  importPart("import-problems", true);
}

checkButton.addEventListener("click", async () => {
  hideError("import-error");
  importPart("import-problems", false);
  importPart("import-preview", false);
  confirmButton.classList.add("d-none");
  if (!importFile.files.length) {
    showError("import-error", "Choose the Excel file first.");
    return;
  }
  checkButton.disabled = true;
  try {
    const data = await sendFile(true);
    if (!data) return;
    if (data.errors.length) {
      showProblems(data.errors);
      return;
    }
    showExisting(data.existing);
    const hasNew = data.students.length > 0;
    importPart("import-new-table", hasNew);
    document.getElementById("import-preview-text").textContent = hasNew
      ? `${plural(data.students.length, "student")} will be added. Check the usernames, then press Import.`
      : "Nobody new to add. Every student in this file already exists.";
    document.getElementById("import-preview-rows").replaceChildren(...data.students.map((student) =>
      tableRow([student.row, student.name, student.username, student.grade, student.section,
        student.password_given ? "from the file" : "will be made"])));
    importPart("import-preview", true);
    if (hasNew) {
      confirmButton.textContent = `Import ${plural(data.students.length, "student")}`;
      confirmButton.classList.remove("d-none");
    }
  } catch {
    showError("import-error", "Cannot reach the server. Check your connection.");
  } finally {
    checkButton.disabled = false;
  }
});

confirmButton.addEventListener("click", async () => {
  hideError("import-error");
  confirmButton.disabled = true;
  try {
    const data = await sendFile(false);
    if (!data) return;
    if (data.errors.length) {
      // Something changed since the check (e.g. a username was taken meanwhile).
      importPart("import-preview", false);
      confirmButton.classList.add("d-none");
      showProblems(data.errors);
      return;
    }
    createdStudents = data.students;
    importPart("import-choose", false);
    importPart("import-preview", false);
    confirmButton.classList.add("d-none");
    document.getElementById("import-done-text").textContent =
      `${plural(data.students.length, "student")} added, disabled: enable them first so they can log in.` +
      (data.existing.length ? ` ${plural(data.existing.length, "student")} already existed and were skipped.` : "");
    document.getElementById("import-done-rows").replaceChildren(...data.students.map((student) =>
      tableRow([student.name, student.username, student.password, student.grade, student.section])));
    importPart("import-done", true);
    page = 1; // users.js: show the list from the start
    loadUsers();
  } catch {
    showError("import-error", "Cannot reach the server. Check your connection.");
  } finally {
    confirmButton.disabled = false;
  }
});

// Login details as a CSV file that opens in Excel (with ñ and other letters kept).
document.getElementById("import-download").addEventListener("click", () => {
  const quote = (value) => `"${String(value).replaceAll('"', '""')}"`;
  const lines = [["Name", "Username", "Password", "Grade", "Section"].map(quote).join(",")];
  for (const student of createdStudents) {
    lines.push([student.name, student.username, student.password, student.grade, student.section].map(quote).join(","));
  }
  const file = new Blob(["﻿" + lines.join("\r\n")], { type: "text/csv;charset=utf-8" });
  const link = document.createElement("a");
  link.href = URL.createObjectURL(file);
  link.download = `MyGURO login details ${new Date().toISOString().slice(0, 10)}.csv`;
  document.body.append(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(link.href);
});

// Each time the popup opens: start again at choosing a file.
importModalElement.addEventListener("show.bs.modal", () => {
  importFile.value = "";
  createdStudents = [];
  hideError("import-error");
  for (const id of ["import-problems", "import-preview", "import-done"]) importPart(id, false);
  importPart("import-choose", true);
  confirmButton.classList.add("d-none");
});

// A new file chosen: hide the old check.
importFile.addEventListener("change", () => {
  importPart("import-problems", false);
  importPart("import-preview", false);
  confirmButton.classList.add("d-none");
  hideError("import-error");
});
