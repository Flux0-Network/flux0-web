'use strict';

const toggle = document.querySelector('.nav-toggle');
const navLinks = document.querySelector('.nav-links');
toggle?.addEventListener('click', () => navLinks.classList.toggle('open'));
navLinks?.querySelectorAll('a').forEach((link) =>
  link.addEventListener('click', () => navLinks.classList.remove('open'))
);
