// The weekly timetable table, shared by the admin's page and the teacher's own page.

// scheduleGrid(grid, makeCell) fills #schedule-head and #schedule-body from the server's grid
// ({periods: [{label, break_after}], days: [...], rows: [[cell or null x days] per period]}).
// makeCell(cell, day, period) returns the <td> for one period; a null cell is a free period.
function scheduleGrid(grid, makeCell) {
  const head = document.getElementById("schedule-head");
  const body = document.getElementById("schedule-body");
  const headRow = document.createElement("tr");
  const corner = document.createElement("th");
  corner.textContent = "Time";
  headRow.append(corner);
  grid.days.forEach((day) => {
    const th = document.createElement("th");
    th.textContent = day;
    headRow.append(th);
  });
  head.replaceChildren(headRow);

  const rows = [];
  grid.rows.forEach((cells, period) => {
    const row = document.createElement("tr");
    const time = document.createElement("th");
    time.className = "text-nowrap fw-normal";
    time.textContent = grid.periods[period].label;
    row.append(time);
    cells.forEach((cell, day) => row.append(makeCell(cell, day, period)));
    rows.push(row);
    if (grid.periods[period].break_after) {
      // The health break is not a period: one thin row across the week
      const pause = document.createElement("tr");
      const label = document.createElement("td");
      label.colSpan = grid.days.length + 1;
      label.className = "text-body-secondary small py-0";
      label.textContent = "Health break";
      pause.append(label);
      rows.push(pause);
    }
  });
  body.replaceChildren(...rows);
}

// teacherCell({subject, section, room}) -> a <td> with the subject, and the section and room under it
function teacherCell(cell) {
  const td = document.createElement("td");
  if (!cell) return td;
  const subject = document.createElement("div");
  subject.className = "fw-semibold";
  subject.textContent = cell.subject;
  const where = document.createElement("div");
  where.className = "text-body-secondary";
  where.textContent = [cell.section, cell.room && `Room ${cell.room}`].filter(Boolean).join(" · ");
  td.append(subject, where);
  return td;
}
