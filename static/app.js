const form = document.getElementById("session-form");
const rowsEl = document.getElementById("session-rows");
const emptyEl = document.getElementById("empty");
const errorEl = document.getElementById("error");

let subjectChart = null;
let dayChart = null;

// Default the date field to today
document.getElementById("study-date").valueAsDate = new Date();

// Helper so every request handles errors the same way
async function api(path, options) {
  const res = await fetch(path, options);
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail ? JSON.stringify(body.detail) : "Request failed");
  }
  return res.status === 204 ? null : res.json();
}

async function loadSessions() {
  const sessions = await api("/api/sessions");
  rowsEl.innerHTML = "";
  emptyEl.style.display = sessions.length ? "none" : "block";

  for (const s of sessions) {
    const tr = document.createElement("tr");

    // textContent (not innerHTML) so user input can never inject HTML/JS
    for (const value of [s.study_date, s.subject, s.minutes, s.notes]) {
      const td = document.createElement("td");
      td.textContent = value;
      tr.appendChild(td);
    }

    const actionTd = document.createElement("td");
    const btn = document.createElement("button");
    btn.textContent = "Delete";
    btn.className = "delete-btn";
    btn.addEventListener("click", () => deleteSession(s.id));
    actionTd.appendChild(btn);
    tr.appendChild(actionTd);

    rowsEl.appendChild(tr);
  }
}

async function loadStats() {
  const stats = await api("/api/stats");

  document.getElementById("total-hours").textContent =
    (stats.total_minutes / 60).toFixed(1);
  document.getElementById("total-sessions").textContent = stats.total_sessions;

  // Redraw charts from scratch each time
  if (subjectChart) subjectChart.destroy();
  if (dayChart) dayChart.destroy();

  subjectChart = new Chart(document.getElementById("subject-chart"), {
    type: "doughnut",
    data: {
      labels: stats.by_subject.map((r) => r.subject),
      datasets: [{ data: stats.by_subject.map((r) => r.minutes) }],
    },
  });

  dayChart = new Chart(document.getElementById("day-chart"), {
    type: "bar",
    data: {
      labels: stats.by_day.map((r) => r.study_date),
      datasets: [
        {
          label: "Minutes",
          data: stats.by_day.map((r) => r.minutes),
          backgroundColor: "#2f855a",
        },
      ],
    },
    options: { plugins: { legend: { display: false } } },
  });
}

async function refresh() {
  try {
    await Promise.all([loadSessions(), loadStats()]);
  } catch (err) {
    errorEl.textContent = err.message;
  }
}

async function deleteSession(id) {
  try {
    await api(`/api/sessions/${id}`, { method: "DELETE" });
    await refresh();
  } catch (err) {
    errorEl.textContent = err.message;
  }
}

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  errorEl.textContent = "";

  const payload = {
    subject: document.getElementById("subject").value,
    minutes: Number(document.getElementById("minutes").value),
    study_date: document.getElementById("study-date").value,
    notes: document.getElementById("notes").value,
  };

  try {
    await api("/api/sessions", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    form.reset();
    document.getElementById("study-date").valueAsDate = new Date();
    await refresh();
  } catch (err) {
    errorEl.textContent = err.message;
  }
});

refresh();