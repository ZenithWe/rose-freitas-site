(() => {
  document.querySelectorAll('[data-photo-upload]').forEach(root => {
    const input = root.querySelector('input[type="file"]');
    const remove = root.querySelector('input[type="checkbox"]');
    const image = root.querySelector('[data-photo-image]');
    const placeholder = root.querySelector('[data-photo-placeholder]');
    const feedback = root.querySelector('[data-photo-feedback]');
    const original = root.querySelector('[data-photo-preview]').dataset.original;
    let objectUrl;
    const release = () => { if (objectUrl) URL.revokeObjectURL(objectUrl); objectUrl = undefined; };
    const show = url => { image.hidden = !url; placeholder.hidden = !!url; if (url) image.src = url; else image.removeAttribute('src'); };
    input.addEventListener('change', () => {
      release(); input.setCustomValidity('');
      const file = input.files[0];
      if (!file) { show(original); feedback.textContent = 'Escolha uma foto e salve o cadastro para publicá-la.'; return; }
      if (file.size > 5 * 1024 * 1024) { show(original); input.setCustomValidity('Escolha uma foto de até 5 MB.'); feedback.textContent = 'Esta foto excede 5 MB. Escolha um arquivo menor.'; return; }
      if (file.type && !['image/jpeg', 'image/png', 'image/webp'].includes(file.type)) { show(original); input.setCustomValidity('Escolha uma imagem JPG, PNG ou WebP.'); feedback.textContent = 'Use uma imagem JPG, PNG ou WebP.'; return; }
      if (remove) remove.checked = false;
      objectUrl = URL.createObjectURL(file); show(objectUrl);
      feedback.textContent = `${file.name} selecionada. Salve o cadastro para confirmar a foto.`;
    });
    if (remove) remove.addEventListener('change', () => {
      if (remove.checked) { release(); input.value = ''; input.setCustomValidity(''); show(''); feedback.textContent = 'A foto enviada será removida ao salvar. Uma capa por link existente continuará disponível.'; }
      else { show(original); feedback.textContent = 'A foto atual será mantida.'; }
    });
    window.addEventListener('pagehide', release, { once: true });
  });
})();
