'use strict';

// ── Theme toggle ──
(function () {
  const root = document.documentElement;
  const saved = localStorage.getItem('flux0-theme');
  const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
  if (saved) {
    root.setAttribute('data-theme', saved);
  } else if (prefersDark) {
    root.setAttribute('data-theme', 'dark');
  }

  document.addEventListener('DOMContentLoaded', function () {
    const btn = document.getElementById('themeToggle');
    if (!btn) return;
    btn.addEventListener('click', function () {
      const current = root.getAttribute('data-theme');
      const next = current === 'dark' ? 'light' : 'dark';
      root.setAttribute('data-theme', next);
      localStorage.setItem('flux0-theme', next);
    });
  });
})();

// ── Main nav mobile toggle ──
const navToggle = document.querySelector('.nav-toggle');
const navLinks  = document.querySelector('.nav-links');
navToggle?.addEventListener('click', () => navLinks.classList.toggle('open'));
navLinks?.querySelectorAll('a').forEach((l) =>
  l.addEventListener('click', () => navLinks.classList.remove('open'))
);

// ── Docs sidebar mobile drawer ──
const docsToggle  = document.getElementById('docsMobileToggle');
const docsOverlay = document.getElementById('docsOverlay');
const docsSidebar = document.querySelector('.docs-sidebar');
const docsClose   = document.getElementById('docsSidebarClose');

function openDocsSidebar() {
  docsSidebar?.classList.add('docs-sidebar--open');
  docsOverlay?.classList.add('docs-overlay--visible');
  document.body.style.overflow = 'hidden';
}
function closeDocsSidebar() {
  docsSidebar?.classList.remove('docs-sidebar--open');
  docsOverlay?.classList.remove('docs-overlay--visible');
  document.body.style.overflow = '';
}

docsToggle?.addEventListener('click', openDocsSidebar);
docsOverlay?.addEventListener('click', closeDocsSidebar);
docsClose?.addEventListener('click', closeDocsSidebar);

// Close sidebar when a nav link is clicked (navigates to section)
docsSidebar?.querySelectorAll('.docs-nav-link').forEach((l) =>
  l.addEventListener('click', closeDocsSidebar)
);
