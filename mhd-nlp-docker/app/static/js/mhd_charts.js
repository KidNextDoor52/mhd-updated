// app/static/js/mhd_charts.js

// Re-usable colors (subtle, not neon)
const MHD_COLORS = {
  primary: "rgba(11, 27, 59, 0.9)",
  primarySoft: "rgba(11, 27, 59, 0.25)",
  green: "rgba(46, 204, 113, 0.9)",
  greenSoft: "rgba(46, 204, 113, 0.25)",
  orange: "rgba(243, 156, 18, 0.9)",
  orangeSoft: "rgba(243, 156, 18, 0.25)",
  red: "rgba(231, 76, 60, 0.9)",
  redSoft: "rgba(231, 76, 60, 0.25)",
};

// Tiny line chart for trends
function renderSparkline(id, labels, data) {
  const el = document.getElementById(id);
  if (!el || !labels || !data || !labels.length) return;

  new Chart(el.getContext("2d"), {
    type: "line",
    data: {
      labels,
      datasets: [
        {
          data,
          fill: false,
          borderColor: MHD_COLORS.primary,
          backgroundColor: MHD_COLORS.primary,
          borderWidth: 2,
          tension: 0.3,
          pointRadius: 0,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: false }, tooltip: { enabled: true } },
      scales: {
        x: { display: false },
        y: { display: false },
      },
    },
  });
}

// Donut chart for status breakdowns
function renderDonut(id, labels, data, colors) {
  const el = document.getElementById(id);
  if (!el || !labels || !data || !labels.length) return;

  const bg = colors || [
    MHD_COLORS.primary,
    MHD_COLORS.green,
    MHD_COLORS.orange,
    MHD_COLORS.red,
  ].slice(0, data.length);

  new Chart(el.getContext("2d"), {
    type: "doughnut",
    data: {
      labels,
      datasets: [
        {
          data,
          backgroundColor: bg,
          borderWidth: 0,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      cutout: "68%",
    },
  });
}

window.MHDCharts = { renderSparkline, renderDonut, MHD_COLORS };
