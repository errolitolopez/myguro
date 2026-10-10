// Loads the dashboard numbers. Admins see totals for the whole school;
// teachers see their own students, activities and classes.

function setText(id, text) {
  const element = document.getElementById(id);
  if (element) element.textContent = text;
}

function showClasses(classes) {
  const list = document.getElementById("class-list");
  list.replaceChildren();
  document.getElementById("no-classes").classList.toggle("d-none", classes.length > 0);

  for (const item of classes) {
    const row = document.createElement("div");
    row.className = "list-group-item d-flex justify-content-between align-items-center";

    const left = document.createElement("div");
    const name = document.createElement("div");
    name.className = "fw-semibold";
    name.textContent = item.name;
    const details = document.createElement("div");
    details.className = "small text-body-secondary";
    details.textContent = `${item.students} students · ${item.activities} activities`;
    left.append(name, details);

    const code = document.createElement("span");
    code.className = "badge text-bg-light font-monospace fs-6";
    code.textContent = item.code;
    code.title = "Class code";

    row.append(left, code);
    list.append(row);
  }
}

async function loadDashboard() {
  hideError("dashboard-error");
  try {
    const response = await apiFetch("/api/dashboard");
    if (!response) return;
    const data = await response.json();
    if (!response.ok) {
      showError("dashboard-error", data.error || "Could not load the dashboard.");
      return;
    }

    if (data.role === "admin") {
      setText("stat-teachers", data.teachers);
      setText("stat-active-teachers", `${data.active_teachers} active`);
      setText("stat-classes", data.classes);
      setText("stat-students", data.students);
      setText("stat-activities", data.activities);
    } else {
      setText("stat-students", data.students);
      setText("stat-published", data.published);
      setText("stat-drafts", data.drafts);
      setText("stat-submissions", data.submissions);
      showClasses(data.classes);
    }
  } catch {
    showError("dashboard-error", "Cannot reach the server. Check your connection.");
  }
}

loadDashboard();
