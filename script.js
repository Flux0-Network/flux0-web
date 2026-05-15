'use strict';
const observer = new IntersectionObserver((entries) => {
  entries.forEach((entry) => {
    if (!entry.isIntersecting) return;
    const delay = parseInt(entry.target.dataset.delay || '0', 10);
    setTimeout(() => entry.target.classList.add('visible'), delay);
    observer.unobserve(entry.target);
  });
}, { threshold: 0.12 });
document.querySelectorAll('.card, .team-card').forEach((el) => observer.observe(el));
const toggle = document.querySelector('.nav-toggle');
const navLinks = document.querySelector('.nav-links');
toggle?.addEventListener('click', () => navLinks.classList.toggle('open'));
navLinks?.querySelectorAll('a').forEach((link) => link.addEventListener('click', () => navLinks.classList.remove('open')));
const navbar = document.querySelector('.navbar');
window.addEventListener('scroll', () => { navbar.style.background = window.scrollY > 40 ? 'rgba(6,6,15,0.92)' : 'rgba(6,6,15,0.7)'; }, { passive: true });