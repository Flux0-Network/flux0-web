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
  function formatNum(n, raw) {
    if (raw) return String(n);
    return n.toLocaleString('de-DE');
  }

  function animateCounter(el, target) {
    const suffix = el.dataset.suffix || '';
    const raw    = !!el.dataset.raw;
    const duration = 1400;
    const start = performance.now();
    function step(now) {
      const elapsed  = now - start;
      const progress = Math.min(elapsed / duration, 1);
      const ease     = 1 - Math.pow(1 - progress, 3);
      el.textContent = formatNum(Math.round(ease * target), raw) + suffix;
      if (progress < 1) requestAnimationFrame(step);
    }
    requestAnimationFrame(step);
  }

  // Animate static counters on scroll-in
  const observer = new IntersectionObserver(function (entries) {
    entries.forEach(function (entry) {
      if (!entry.isIntersecting) return;
      const el = entry.target;
      if (el.dataset.target) {
        animateCounter(el, parseInt(el.dataset.target, 10));
        observer.unobserve(el);
      }
    });
  }, { threshold: 0.3 });

  document.querySelectorAll('.stats-num[data-target]').forEach(function (el) {
    observer.observe(el);
  });

  // Live Discord server stats via public invite API
  var INVITE = 'D9GwqWpwHT';
  var elMembers = document.getElementById('stat-members');
  var elOnline  = document.getElementById('stat-online');
  if (elMembers || elOnline) {
    fetch('https://discord.com/api/v9/invites/' + INVITE + '?with_counts=true')
      .then(function (r) { return r.json(); })
      .then(function (data) {
        var members = data.approximate_member_count;
        var online  = data.approximate_presence_count;
        if (elMembers && members) animateCounter(elMembers, members);
        if (elOnline  && online)  animateCounter(elOnline, online);
      })
      .catch(function () {
        if (elMembers) elMembers.textContent = '1.200+';
        if (elOnline)  elOnline.textContent  = '—';
      });
  }
})();

// ── Discord partner avatars ──
(function () {
  var partners = [
    { invite: 'busbahnhof', imgId: 'busbahnhof-avatar', fallbackId: 'busbahnhof-fallback' }
  ];
  partners.forEach(function (p) {
    fetch('https://discord.com/api/v9/invites/' + p.invite)
      .then(function (r) { return r.json(); })
      .then(function (data) {
        var guild = data.guild;
        if (!guild || !guild.icon) return;
        var img = document.getElementById(p.imgId);
        if (!img) return;
        img.src = 'https://cdn.discordapp.com/icons/' + guild.id + '/' + guild.icon + '.webp?size=64';
        img.style.display = '';
        var fb = document.getElementById(p.fallbackId);
        if (fb) fb.style.display = 'none';
      })
      .catch(function () {});
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
