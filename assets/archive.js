(() => {
  'use strict';
  document.documentElement.classList.add('js');
  const videoObjectUrls = new Set();
  document.querySelectorAll('.saved-video').forEach((figure) => {
    const button = figure.querySelector('.load-saved-video');
    const video = figure.querySelector('video');
    const status = figure.querySelector('.saved-video-status');
    const download = figure.querySelector('.saved-video-download');
    if (!button || !video || !status || !download) return;
    const initialLabel = button.textContent;
    button.addEventListener('click', async () => {
      if (button.disabled) return;
      button.disabled = true;
      figure.setAttribute('aria-busy', 'true');
      status.textContent = 'Loading the saved video…';
      let objectUrl;
      try {
        const parts = JSON.parse(figure.dataset.videoParts);
        const expectedBytes = Number(figure.dataset.videoBytes);
        const expectedHash = figure.dataset.videoSha256;
        if (!Array.isArray(parts) || !parts.length || !Number.isSafeInteger(expectedBytes)
            || expectedBytes <= 0 || expectedBytes > 1_000_000_000
            || !/^[0-9a-f]{64}$/.test(expectedHash || '')) throw new Error('Invalid saved video record.');
        const assetRoot = new URL('../assets/', document.baseURI);
        const urls = parts.map((part) => {
          if (typeof part !== 'string' || !part.startsWith('../assets/')
              || /[\\%?#:]/.test(part) || part.slice(3).split('/').some((segment) => !segment || segment === '.' || segment === '..')) {
            throw new Error('Invalid saved video address.');
          }
          const url = new URL(part, document.baseURI);
          if (url.origin !== location.origin || !url.pathname.startsWith(assetRoot.pathname)) throw new Error('Invalid saved video address.');
          return url;
        });
        const buffers = [];
        let received = 0;
        for (const url of urls) {
          const controller = new AbortController();
          const timeout = setTimeout(() => controller.abort(), 120000);
          try {
            const response = await fetch(url, {signal: controller.signal, credentials: 'same-origin'});
            if (!response.ok) throw new Error('A saved video file could not be loaded.');
            const buffer = await response.arrayBuffer();
            received += buffer.byteLength;
            if (received > expectedBytes) throw new Error('The saved video size does not match its record.');
            buffers.push(buffer);
            status.textContent = `Loading the saved video… ${Math.round(received / expectedBytes * 100)}%`;
          } finally {
            clearTimeout(timeout);
          }
        }
        if (received !== expectedBytes) throw new Error('The saved video download is incomplete.');
        if (!globalThis.crypto?.subtle) throw new Error('This browser cannot verify the saved video. Use the recovery instructions below.');
        const blob = new Blob(buffers, {type: 'video/mp4'});
        const digest = await crypto.subtle.digest('SHA-256', await blob.arrayBuffer());
        const hash = [...new Uint8Array(digest)].map((byte) => byte.toString(16).padStart(2, '0')).join('');
        if (hash !== expectedHash) throw new Error('The saved video failed its integrity check. Please retry.');
        objectUrl = URL.createObjectURL(blob);
        videoObjectUrls.add(objectUrl);
        video.src = objectUrl;
        video.load();
        download.href = objectUrl;
        download.download = figure.dataset.videoFilename;
        download.hidden = false;
        button.hidden = true;
        status.textContent = 'Video ready. Press play or download your saved copy.';
      } catch (error) {
        if (objectUrl) {
          URL.revokeObjectURL(objectUrl);
          videoObjectUrls.delete(objectUrl);
        }
        status.textContent = error.name === 'AbortError'
          ? 'The download timed out. Please retry when your connection is ready.'
          : `Could not load the saved video. ${error.message || 'Check your connection and retry.'}`;
        button.textContent = `Retry — ${initialLabel}`;
      } finally {
        button.disabled = false;
        figure.removeAttribute('aria-busy');
      }
    });
  });
  window.addEventListener('pagehide', (event) => {
    if (!event.persisted) videoObjectUrls.forEach((url) => URL.revokeObjectURL(url));
  });
  const search = document.getElementById('archive-search');
  const category = document.getElementById('archive-category');
  if (!search || !category) return;
  const entries = [...document.querySelectorAll('.archive-entry')];
  const result = document.getElementById('result-count');
  const empty = document.getElementById('no-results');
  const normalize = (value) => value.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLocaleLowerCase();
  const haystacks = entries.map((entry) => normalize(entry.textContent));
  const applyFilters = () => {
    const terms = normalize(search.value.trim()).split(/\s+/).filter(Boolean);
    let count = 0;
    entries.forEach((entry, index) => {
      const visible = (!category.value || entry.dataset.category === category.value)
        && terms.every((term) => haystacks[index].includes(term));
      entry.hidden = !visible;
      if (visible) count++;
    });
    result.textContent = `${count} of ${entries.length} entries`;
    empty.hidden = count !== 0;
  };
  search.addEventListener('input', applyFilters);
  category.addEventListener('change', applyFilters);
  document.getElementById('clear-filters').addEventListener('click', () => {
    search.value = '';
    category.value = '';
    applyFilters();
    search.focus();
  });
  const openLinkedEntry = () => {
    let id;
    try { id = decodeURIComponent(location.hash.slice(1)); } catch { return; }
    const entry = document.getElementById(id);
    if (!entry || !entry.classList.contains('archive-entry')) return;
    if (entry.hidden) {
      search.value = '';
      category.value = '';
      applyFilters();
    }
    const detail = entry.querySelector('details');
    if (detail) detail.open = true;
    entry.scrollIntoView({block: 'start'});
  };
  window.addEventListener('hashchange', openLinkedEntry);
  applyFilters();
  openLinkedEntry();
})();
