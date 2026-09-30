/* 21st.dev spotlight pattern: one delegated listener, native CSS variables. */
(() => {
  if (!matchMedia('(hover: hover) and (pointer: fine)').matches || matchMedia('(prefers-reduced-motion: reduce)').matches) return;
  let frame = 0, pending;
  document.getElementById('main-content')?.addEventListener('pointermove', event => {
    const card = event.target.closest('.hero-feature, .vip-card');
    if (!card) return;
    pending = { card, x: event.clientX, y: event.clientY };
    if (frame) return;
    frame = requestAnimationFrame(() => {
      const { card, x, y } = pending;
      const rect = card.getBoundingClientRect();
      card.style.setProperty('--spot-x', `${x - rect.left}px`);
      card.style.setProperty('--spot-y', `${y - rect.top}px`);
      frame = 0;
    });
  }, { passive: true });
})();
