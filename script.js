'use strict';

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
