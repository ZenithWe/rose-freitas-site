(() => {
  const header = document.querySelector('[data-site-header]');
  const syncHeader = () => header?.classList.toggle('is-scrolled', window.scrollY > 12);
  syncHeader();
  addEventListener('scroll', syncHeader, {passive:true});

  const reduced = matchMedia('(prefers-reduced-motion: reduce)').matches;
  const revealEls = [...document.querySelectorAll('[data-reveal]')];
  if (reduced || !('IntersectionObserver' in window)) {
    revealEls.forEach(el => el.classList.add('is-visible'));
  } else {
    const io = new IntersectionObserver(entries => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          entry.target.classList.add('is-visible');
          io.unobserve(entry.target);
        }
      });
    }, {threshold:.12, rootMargin:'0px 0px -30px'});
    revealEls.forEach(el => io.observe(el));
  }

  if (!reduced && matchMedia('(hover:hover) and (pointer:fine)').matches) {
    document.addEventListener('pointermove', e => {
      const card = e.target.closest('.spotlight-card, .rf-bento-card');
      if (!card) return;
      const r = card.getBoundingClientRect();
      card.style.setProperty('--spot-x', (e.clientX - r.left) + 'px');
      card.style.setProperty('--spot-y', (e.clientY - r.top) + 'px');
    }, {passive:true});
  }
})();