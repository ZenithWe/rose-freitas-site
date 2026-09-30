(() => {
  'use strict';
  const toggle = document.querySelector('.menu-btn');
  const nav = document.querySelector('.site-menu');
  const setMenu = (open) => {
    document.body.classList.toggle('menu-open', open);
    toggle?.setAttribute('aria-expanded', String(open));
    toggle?.setAttribute('aria-label', open ? 'Fechar menu' : 'Abrir menu');
  };
  toggle?.addEventListener('click', () => setMenu(toggle.getAttribute('aria-expanded') !== 'true'));
  nav?.querySelectorAll('a').forEach(link => link.addEventListener('click', () => setMenu(false)));
  document.addEventListener('keydown', event => { if (event.key === 'Escape' && document.body.classList.contains('menu-open')) { setMenu(false); toggle?.focus(); } });
  document.addEventListener('click', event => { if (!nav?.contains(event.target) && !toggle?.contains(event.target)) setMenu(false); });
  window.matchMedia('(min-width: 1101px)').addEventListener('change', event => { if (event.matches) setMenu(false); });
  document.querySelectorAll('[data-dismiss-message]').forEach(button => button.addEventListener('click', () => button.closest('.flash')?.remove()));
  const catalog = document.querySelector('[data-catalog]');
  if (catalog) {
    const cards = [...catalog.querySelectorAll('[data-catalog-card]')];
    const search = catalog.querySelector('input[type="search"]');
    const buttons = [...catalog.querySelectorAll('[data-filter]')];
    let kind = 'all';
    const normalize = value => value.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase();
    const filter = () => {
      const term = normalize(search?.value || '');
      let visible = 0;
      cards.forEach(card => { const show = (kind === 'all' || card.dataset.kind === kind) && normalize(card.dataset.title).includes(term); card.hidden = !show; if (show) visible++; });
      catalog.querySelector('[data-catalog-empty]').hidden = visible !== 0;
    };
    buttons.forEach(button => button.addEventListener('click', () => { kind = button.dataset.filter; buttons.forEach(item => item.setAttribute('aria-pressed', String(item === button))); filter(); }));
    search?.addEventListener('input', filter);
    filter();
  }
  document.querySelectorAll('[data-copy-pix]').forEach(button => button.addEventListener('click', async () => {
    const target = document.getElementById(button.dataset.copyTarget);
    const status = button.parentElement.querySelector('[data-copy-status]');
    try { await navigator.clipboard.writeText(target.textContent.trim()); status.textContent = 'Chave copiada.'; }
    catch { const selection = window.getSelection(); const range = document.createRange(); range.selectNodeContents(target); selection.removeAllRanges(); selection.addRange(range); status.textContent = 'Selecione e copie a chave acima.'; }
  }));
})();