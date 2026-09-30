(() => {
  "use strict";
  document.body.classList.add("panel-has-js");

  const sidebar = document.getElementById("panel-sidebar");
  const layout = document.getElementById("panel-layout");
  const toggle = document.querySelector("[data-panel-toggle]");
  const backdrop = document.querySelector(".panel-backdrop");
  const mobile = window.matchMedia("(max-width: 1024px)");
  let lastFocus = null;

  const setNavigation = (open, restoreFocus = true) => {
    if (!sidebar || !toggle || !layout || !backdrop) return;
    const visible = open && mobile.matches;
    document.body.classList.toggle("panel-nav-open", visible);
    toggle.setAttribute("aria-expanded", String(visible));
    toggle.setAttribute("aria-label", visible ? "Fechar menu administrativo" : "Abrir menu administrativo");
    backdrop.hidden = !visible;
    sidebar.inert = mobile.matches && !visible;
    layout.inert = visible;
    if (visible) {
      lastFocus = document.activeElement;
      sidebar.querySelector("[data-panel-close]")?.focus();
    } else if (restoreFocus && lastFocus && mobile.matches) {
      lastFocus.focus();
      lastFocus = null;
    }
  };

  if (sidebar && toggle) {
    setNavigation(false, false);
    toggle.addEventListener("click", () => setNavigation(!document.body.classList.contains("panel-nav-open")));
    document.querySelectorAll("[data-panel-close]").forEach(button => button.addEventListener("click", () => setNavigation(false)));
    mobile.addEventListener("change", () => {
      const focusWasInSidebar = sidebar.contains(document.activeElement);
      setNavigation(false, false);
      if (mobile.matches && focusWasInSidebar) toggle.focus();
    });
    document.addEventListener("keydown", event => {
      if (!document.body.classList.contains("panel-nav-open")) return;
      if (event.key === "Escape") {
        event.preventDefault();
        setNavigation(false);
      } else if (event.key === "Tab") {
        const controls = [...sidebar.querySelectorAll("a[href], button:not([disabled]), input:not([type='hidden'])")].filter(element => element.getClientRects().length);
        const first = controls[0];
        const last = controls[controls.length - 1];
        if (event.shiftKey && document.activeElement === first) {
          event.preventDefault();
          last?.focus();
        } else if (!event.shiftKey && document.activeElement === last) {
          event.preventDefault();
          first?.focus();
        }
      }
    });
  }

  const normalize = value => value.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLocaleLowerCase("pt-BR").trim();
  document.querySelectorAll("[data-panel-list]").forEach(list => {
    const input = list.querySelector("[data-search-input]");
    if (!input) return;
    const rows = [...list.querySelectorAll("[data-record]")];
    const empty = list.querySelector("[data-search-empty]");
    const count = list.querySelector("[data-result-count]");
    const recordWord = list.querySelector("[data-record-word]");
    const note = list.querySelector("[data-search-note]");
    const table = list.querySelector(".panel-table-wrap");
    const searchable = rows.map(row => ({ row, text: normalize(row.dataset.search || row.textContent) }));
    list.querySelector("[data-search-ui]").hidden = false;
    const filter = () => {
      const terms = normalize(input.value).split(/\s+/).filter(Boolean);
      let visibleCount = 0;
      searchable.forEach(({ row, text }) => {
        const matches = terms.every(term => text.includes(term));
        row.hidden = !matches;
        if (matches) visibleCount++;
      });
      if (count) count.textContent = String(visibleCount);
      if (recordWord) recordWord.textContent = visibleCount === 1 ? "registro" : "registros";
      if (note) {
        note.hidden = !terms.length;
        note.textContent = visibleCount === 1 ? " encontrado" : " encontrados";
      }
      if (empty) empty.hidden = visibleCount !== 0;
      if (table) table.hidden = visibleCount === 0;
    };
    input.addEventListener("input", filter);
    list.querySelector("[data-search-clear]")?.addEventListener("click", () => {
      input.value = "";
      filter();
      input.focus();
    });
    filter();
  });

  document.querySelectorAll("form[data-confirm]").forEach(form => {
    form.addEventListener("submit", event => {
      if (!window.confirm(form.dataset.confirm)) event.preventDefault();
    });
  });

  document.querySelectorAll("[data-password-toggle]").forEach(button => {
    const input = document.getElementById(button.getAttribute("aria-controls"));
    if (!input) return;
    button.hidden = false;
    button.addEventListener("click", () => {
      const visible = input.type === "password";
      input.type = visible ? "text" : "password";
      button.setAttribute("aria-pressed", String(visible));
      button.setAttribute("aria-label", visible ? "Ocultar senha" : "Mostrar senha");
      button.querySelector("[data-password-show]").hidden = visible;
      button.querySelector("[data-password-hide]").hidden = !visible;
    });
  });

  document.querySelectorAll("[data-panel-image]").forEach(image => {
    const fallback = () => { image.hidden = true; };
    image.addEventListener("error", fallback);
    if (image.complete && image.naturalWidth === 0) fallback();
  });
})();
