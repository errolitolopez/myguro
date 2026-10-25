// Activities page: import an activity sheet from a Word file. Check file -> preview or the
// problems by item -> Import -> the new draft sheet opens in the editor.

const sheetModalElement = document.getElementById("import-sheet-modal");
const sheetFile = document.getElementById("import-sheet-file");
const sheetTitle = document.getElementById("import-sheet-title-input");
const sheetSubject = document.getElementById("import-sheet-subject");
const sheetCheckButton = document.getElementById("import-sheet-check");
const sheetConfirmButton = document.getElementById("import-sheet-confirm");

function sheetPart(id, show) {
  document.getElementById(id).classList.toggle("d-none", !show);
}

function resetSheetCheck() {
  sheetPart("import-sheet-problems", false);
  sheetPart("import-sheet-preview", false);
  sheetConfirmButton.classList.add("d-none");
  hideError("import-sheet-error");
}

// Sends the chosen file with the title and subject. dryRun = only check it.
async function sendSheet(dryRun) {
  const form = new FormData();
  form.append("file", sheetFile.files[0]);
  form.append("title", sheetTitle.value);
  form.append("subject", sheetSubject.value);
  form.append("dry_run", dryRun ? "1" : "0");
  const response = await apiFetch("/api/activities/import", { method: "POST", body: form });
  if (!response) return null;
  const data = await response.json();
  if (!response.ok) {
    showError("import-sheet-error", data.error || "Could not read the file.");
    return null;
  }
  return data;
}

function showSheetProblems(errors) {
  document.getElementById("import-sheet-problem-list").replaceChildren(...errors.map((problem) => {
    const item = document.createElement("li");
    item.textContent = `${problem.where}: ${problem.message}`;
    return item;
  }));
  sheetPart("import-sheet-problems", true);
}

function sheetRow(values) {
  const row = document.createElement("tr");
  for (const value of values) {
    const cell = document.createElement("td");
    cell.textContent = value;
    row.append(cell);
  }
  return row;
}

sheetCheckButton.addEventListener("click", async () => {
  resetSheetCheck();
  if (!sheetFile.files.length) {
    showError("import-sheet-error", "Choose the Word file first.");
    return;
  }
  if (!sheetTitle.value.trim()) {
    showError("import-sheet-error", "Type the title of the activity.");
    return;
  }
  const stopLoading = startLoading(sheetCheckButton);
  if (!stopLoading) return;
  try {
    const data = await sendSheet(true);
    if (!data) return;
    if (data.errors.length) {
      showSheetProblems(data.errors);
      return;
    }
    const questions = data.sections.reduce((sum, section) => sum + section.questions, 0);
    document.getElementById("import-sheet-preview-text").textContent =
      `${plural(data.sections.length, "section")} and ${plural(questions, "question")} will be added. ` +
      "Check them, then press Import.";
    document.getElementById("import-sheet-preview-rows").replaceChildren(...data.sections.map((section, index) =>
      sheetRow([index + 1, section.title, section.kind,
        section.kind === "activity" ? section.questions : "", section.kind === "activity" ? section.points : ""])));
    sheetPart("import-sheet-preview", true);
    sheetConfirmButton.classList.remove("d-none");
  } catch {
    showError("import-sheet-error", "Cannot reach the server. Check your connection.");
  } finally {
    stopLoading();
  }
});

sheetConfirmButton.addEventListener("click", async () => {
  hideError("import-sheet-error");
  const stopLoading = startLoading(sheetConfirmButton);
  if (!stopLoading) return;
  try {
    const data = await sendSheet(false);
    if (!data) return;
    if (data.errors.length) {
      sheetPart("import-sheet-preview", false);
      sheetConfirmButton.classList.add("d-none");
      showSheetProblems(data.errors);
      return;
    }
    window.location.href = `/activities/${data.activity.id}`;
  } catch {
    showError("import-sheet-error", "Cannot reach the server. Check your connection.");
  } finally {
    stopLoading();
  }
});

// Each time the popup opens: start again.
sheetModalElement.addEventListener("show.bs.modal", () => {
  sheetFile.value = "";
  sheetTitle.value = "";
  sheetSubject.value = "";
  resetSheetCheck();
});

// A file chosen: suggest the title from the file name; hide the old check.
sheetFile.addEventListener("change", () => {
  resetSheetCheck();
  if (sheetFile.files.length && !sheetTitle.value.trim()) {
    sheetTitle.value = sheetFile.files[0].name.replace(/\.docx$/i, "").trim();
  }
});
