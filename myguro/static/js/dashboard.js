// Loads the dashboard numbers. Admins see totals for the whole school;
// teachers see their own students, activities and classes; students see their classes.

function setText(id, text) {
  const element = document.getElementById(id);
  if (element) element.textContent = text;
}

// Teachers' rows open the class page; students' rows are plain (activities come later).
function showClasses(classes, role) {
  const list = document.getElementById("class-list");
  list.replaceChildren();
  document.getElementById("no-classes").classList.toggle("d-none", classes.length > 0);

  for (const item of classes) {
    const row = document.createElement(role === "teacher" ? "a" : "div");
    row.className = "list-group-item";
    if (role === "teacher") {
      row.href = `/classes/${item.id}`;
      row.classList.add("list-group-item-action");
    }

    const name = document.createElement("div");
    name.className = "fw-semibold";
    name.textContent = classTitle(item);
    const details = document.createElement("div");
    details.className = "small text-body-secondary";
    details.textContent =
      role === "teacher"
        ? `${plural(item.students, "student")} · ${plural(item.activities, "activity", "activities")}`
        : `${item.teacher} · ${plural(item.activities, "activity", "activities")}`;

    row.append(name, details);
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
    } else if (data.role === "student") {
      setText("stat-classes", data.classes.length);
      setText("stat-submitted", data.submitted);
      setText("stat-to-do", data.to_do);
      showClasses(data.classes, "student");
    } else {
      setText("stat-students", data.students);
      setText("stat-published", data.published);
      setText("stat-drafts", data.drafts);
      setText("stat-submissions", data.submissions);
      showClasses(data.classes, "teacher");
    }
  } catch {
    showError("dashboard-error", "Cannot reach the server. Check your connection.");
  }
}

loadDashboard();
