/* ══════════════════════════════════════════
   GarageOS — Workshop Management
   app.js
   ══════════════════════════════════════════ */

/* ── ICONS ── */
function renderIcons() {
  if (typeof ICONS === 'undefined') {
    console.warn('ICONS library not loaded');
    return;
  }
  document.querySelectorAll('[data-icon]').forEach(el => {
    const iconName = el.getAttribute('data-icon');
    const svg = ICONS[iconName];
    if (svg) {
      el.innerHTML = svg;
    } else {
      console.warn(`Icon "${iconName}" not found`);
    }
  });
}

/* ── SIDEBAR TOGGLE ── */
function toggleSidebar() {
  const sidebar = document.querySelector('.sidebar');
  sidebar.classList.toggle('collapsed');
}

/* ── NAV DROPDOWN POSITIONING ── */
function positionDropdown(wrapId) {
  const wrap = document.getElementById(wrapId);
  const dropdown = wrap.querySelector('.nav-dropdown');
  const rect = wrap.getBoundingClientRect();

  // Position dropdown below the nav item
  const top = rect.bottom + 6; // 6px gap
  const left = rect.left;

  dropdown.style.top = `${top}px`;
  dropdown.style.left = `${left}px`;

  // Prevent right overflow
  const dropdownRect = dropdown.getBoundingClientRect();
  if (dropdownRect.right > window.innerWidth - 20) {
    dropdown.style.left = 'auto';
    dropdown.style.right = '20px';
  }
}

/* ── HOVER DROPDOWNS ── */
let hoverTimers = {};

function openDropdown(wrap) {
  const wrapId = wrap.id;
  // Clear any pending close timer
  if (hoverTimers[wrapId]) {
    clearTimeout(hoverTimers[wrapId]);
    delete hoverTimers[wrapId];
  }

  // Close others
  document.querySelectorAll('.nav-item-wrap.open').forEach(w => {
    if (w.id !== wrapId && !hoverTimers[w.id]) { // Don't close if it's the one we are entering
      w.classList.remove('open');
    }
  });

  wrap.classList.add('open');
  positionDropdown(wrapId);
}

function closeDropdown(wrap) {
  const wrapId = wrap.id;
  // Set timer to close
  hoverTimers[wrapId] = setTimeout(() => {
    wrap.classList.remove('open');
    delete hoverTimers[wrapId];
  }, 300); // 300ms delay to bridge the gap
}

function initHoverMenus() {
  document.querySelectorAll('.nav-item-wrap').forEach(wrap => {
    // Mouse enter: Open
    wrap.addEventListener('mouseenter', () => openDropdown(wrap));

    // Mouse leave: Close with delay
    wrap.addEventListener('mouseleave', () => closeDropdown(wrap));

    // Also handle focus for accessibility
    wrap.addEventListener('focusin', () => openDropdown(wrap));
    wrap.addEventListener('focusout', (e) => {
      // Only close if focus is moving outside the wrap
      if (!wrap.contains(e.relatedTarget)) {
        closeDropdown(wrap);
      }
    });
  });
}

function toggleDropdown(wrapId, page, navEl) {
  // Kept for click/touch support, but hover will be primary
  const wrap = document.getElementById(wrapId);
  if (wrap.classList.contains('open')) {
    wrap.classList.remove('open');
  } else {
    openDropdown(wrap);
  }
  // Optional: Auto-navigate on click if desired, but for now just toggle
  // _setActivePage(page, navEl); 
}

/* ── GLOBAL EVENT LISTENERS ── */
// Close dropdowns when clicking outside
document.addEventListener('click', (e) => {
  if (!e.target.closest('.nav-item-wrap')) {
    document.querySelectorAll('.nav-item-wrap.open').forEach(w => w.classList.remove('open'));
  }
});

// Close on Escape key
document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape') {
    document.querySelectorAll('.nav-item-wrap.open').forEach(w => w.classList.remove('open'));
    document.querySelectorAll('.modal-overlay.open').forEach(m => m.classList.remove('open'));
  }
});

// Reposition on scroll/resize
const reposition = () => {
  document.querySelectorAll('.nav-item-wrap.open').forEach(wrap => positionDropdown(wrap.id));
};
window.addEventListener('scroll', reposition, { passive: true });
window.addEventListener('resize', reposition);

/* ── NAVIGATION ── */
function navigate(el) {
  const page = el.dataset.page;
  _setActivePage(page, el);
}

function _setActivePage(page, navEl) {
  // Update active nav item
  document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
  navEl.classList.add('active');

  // Update active page
  document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
  document.getElementById('page-' + page).classList.add('active');

}

/* ── MODALS ── */
function openModal(id) { document.getElementById(id).classList.add('open'); }
function closeModal(id) { document.getElementById(id).classList.remove('open'); }
function openJobCard() { openModal('jobModal'); }

/* ── THEME TOGGLE ── */
function toggleTheme() {
  const html = document.documentElement;
  const isDark = html.dataset.theme === 'dark';
  html.dataset.theme = isDark ? 'light' : 'dark';

  const icon = document.getElementById('themeIcon');
  if (typeof ICONS !== 'undefined') {
    icon.innerHTML = !isDark ? ICONS.moon : ICONS.theme;
  } else {
    // Fallback if ICONS not loaded
    if (!isDark) {
      // Switch to moon icon
      icon.innerHTML = '<path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/>';
    } else {
      // Switch to sun icon
      icon.innerHTML = '<circle cx="12" cy="12" r="5"/><line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/><line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/>';
    }
  }
  localStorage.setItem('theme', html.dataset.theme);

}

/* ── TOAST ── */
function showToast(msg) {
  const toast = document.getElementById('toast');
  document.getElementById('toastMsg').textContent = msg;
  toast.classList.add('show');
  setTimeout(() => toast.classList.remove('show'), 2800);
}

/* ══════════════════════════════════════════
   CHARTS  (Chart.js)
   ══════════════════════════════════════════ */
let revenueChart, statusChart;

function getColor(varName) {
  return getComputedStyle(document.documentElement).getPropertyValue(varName).trim();
}

function buildCharts() {
  const isDark = document.documentElement.dataset.theme === 'dark';
  const textColor = getColor('--text3');
  const borderColor = getColor('--border');

  Chart.defaults.color = textColor;
  Chart.defaults.borderColor = borderColor;
  Chart.defaults.font.family = "'Instrument Sans', sans-serif";
  Chart.defaults.font.size = 11;

  /* ── Revenue Line Chart ── */
  const rCtx = document.getElementById('revenueChart');
  if (rCtx) {
    const ctx = rCtx.getContext('2d');
    const months = ['Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec', 'Jan', 'Feb'];
    const values = [320000, 285000, 410000, 365000, 442000, 398000, 490000, 520000, 388000, 460000, 512000, 482350];

    const gradient = ctx.createLinearGradient(0, 0, 0, 220);
    gradient.addColorStop(0, isDark ? 'rgba(249,115,22,.25)' : 'rgba(194,65,12,.15)');
    gradient.addColorStop(1, 'rgba(0,0,0,0)');

    revenueChart = new Chart(ctx, {
      type: 'line',
      data: {
        labels: months,
        datasets: [{
          data: values,
          borderColor: getColor('--accent'),
          borderWidth: 2,
          backgroundColor: gradient,
          fill: true,
          tension: 0.4,
          pointRadius: 3,
          pointBackgroundColor: getColor('--accent'),
          pointHoverRadius: 5
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: {
            callbacks: { label: ctx => (ctx.raw / 1000).toFixed(0) + 'k' }
          }
        },
        scales: {
          x: { grid: { display: false }, border: { display: false } },
          y: {
            grid: { color: borderColor },
            border: { display: false },
            ticks: { callback: v => (v / 1000) + 'k' }
          }
        }
      }
    });
  }

  /* ── Job Status Doughnut Chart ── */
  const sCtx = document.getElementById('statusChart');
  if (sCtx) {
    const ctx = sCtx.getContext('2d');
    statusChart = new Chart(ctx, {
      type: 'doughnut',
      data: {
        labels: ['Pending', 'In Progress', 'Done'],
        datasets: [{
          data: [8, 11, 5],
          backgroundColor: ['#f59e0b', '#3b82f6', '#22c55e'],
          borderWidth: 2,
          borderColor: getColor('--surface')
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        cutout: '72%',
        plugins: {
          legend: { display: false },
          tooltip: {
            callbacks: { label: ctx => ' ' + ctx.label + ': ' + ctx.raw }
          }
        }
      }
    });
  }
}

function rebuildCharts() {
  if (revenueChart) revenueChart.destroy();
  if (statusChart) statusChart.destroy();
  setTimeout(buildCharts, 50);
}

/* ── INIT ── */
window.addEventListener('load', () => {
  renderIcons();
  buildCharts();
  initHoverMenus();
});
