/* ─────────────────────────────────────────────────────────────────────────
   Clinical Documentation System — Shared JS Utilities
   ─────────────────────────────────────────────────────────────────────────*/

// ── Toast Notifications ───────────────────────────────────────────────────
function showToast(message, type = "info") {
  const container = document.getElementById("toast-container") || (() => {
    const d = document.createElement("div");
    d.id = "toast-container";
    document.body.appendChild(d);
    return d;
  })();

  const icons = { success: "✓", error: "✗", warning: "⚠", info: "ℹ" };
  const toast = document.createElement("div");
  toast.className = `toast ${type}`;
  toast.innerHTML = `<span>${icons[type] || "ℹ"}</span><span>${message}</span>`;
  container.appendChild(toast);
  setTimeout(() => toast.remove(), 4000);
}

// ── API helpers ───────────────────────────────────────────────────────────
async function api(method, path, body = null) {
  const opts = {
    method,
    headers: { "Content-Type": "application/json" },
  };
  if (body) opts.body = JSON.stringify(body);
  const res = await fetch(path, opts);
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "Request failed");
  }
  return res.json();
}

// ── Badge HTML ────────────────────────────────────────────────────────────
function statusBadge(status) {
  return `<span class="badge badge-${status}">${status}</span>`;
}

function severityBadge(sev) {
  return `<span class="badge badge-${sev}">${sev}</span>`;
}

// ── Score Bar HTML ─────────────────────────────────────────────────────────
function scoreBar(score) {
  if (score == null) return `<span class="text-muted text-sm">Not scored</span>`;
  const cls  = score >= 75 ? "high" : score >= 50 ? "medium" : "low";
  const color= score >= 75 ? "#0e9f6e" : score >= 50 ? "#d97706" : "#e02424";
  return `
    <div class="score-bar">
      <div class="score-bar-track">
        <div class="score-bar-fill ${cls}" style="width:${score}%"></div>
      </div>
      <span class="score-label" style="color:${color}">${score}</span>
    </div>`;
}

// ── Format dates ──────────────────────────────────────────────────────────
function fmtDate(iso) {
  if (!iso) return "—";
  return new Date(iso).toLocaleDateString("en-US", {
    year: "numeric", month: "short", day: "numeric"
  });
}

// ── Pagination renderer ───────────────────────────────────────────────────
function renderPagination(container, page, pages, onChange) {
  container.innerHTML = "";
  if (pages <= 1) return;

  const btn = (label, p, disabled = false, active = false) => {
    const b = document.createElement("button");
    b.className = `page-btn${active ? " active" : ""}`;
    b.textContent = label;
    b.disabled = disabled;
    b.addEventListener("click", () => onChange(p));
    return b;
  };

  container.appendChild(btn("‹", page - 1, page === 1));
  const start = Math.max(1, page - 2);
  const end   = Math.min(pages, page + 2);
  for (let p = start; p <= end; p++) {
    container.appendChild(btn(p, p, false, p === page));
  }
  container.appendChild(btn("›", page + 1, page === pages));
}

// ── Modal helpers ─────────────────────────────────────────────────────────
function openModal(id)  { document.getElementById(id).classList.add("open"); }
function closeModal(id) { document.getElementById(id).classList.remove("open"); }

// Close on overlay click
document.addEventListener("click", e => {
  if (e.target.classList.contains("modal-overlay")) {
    e.target.classList.remove("open");
  }
});

// ── Spinner HTML ──────────────────────────────────────────────────────────
function spinnerHTML() {
  return `<div style="text-align:center;padding:32px"><div class="spinner"></div></div>`;
}

// ── Highlight active nav ──────────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", () => {
  const path = window.location.pathname;
  document.querySelectorAll(".nav-link").forEach(a => {
    if (a.getAttribute("href") === path || (path === "/" && a.getAttribute("href") === "/")) {
      a.classList.add("active");
    }
  });
});
