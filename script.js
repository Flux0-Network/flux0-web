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

// ── Counter animation ──
(function () {
  function animateCounter(el) {
    const target = parseInt(el.dataset.target, 10);
    const suffix = el.dataset.suffix || '';
    const duration = 1400;
    const start = performance.now();
    function step(now) {
      const elapsed = now - start;
      const progress = Math.min(elapsed / duration, 1);
      const ease = 1 - Math.pow(1 - progress, 3);
      el.textContent = Math.round(ease * target).toLocaleString('de-DE') + suffix;
      if (progress < 1) requestAnimationFrame(step);
    }
    requestAnimationFrame(step);
  }

  const observer = new IntersectionObserver(function (entries) {
    entries.forEach(function (entry) {
      if (entry.isIntersecting) {
        animateCounter(entry.target);
        observer.unobserve(entry.target);
      }
    });
  }, { threshold: 0.3 });

  document.querySelectorAll('.stats-num').forEach(function (el) {
    observer.observe(el);
  });
})();

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
