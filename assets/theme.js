(() => {
  'use strict';
  let theme = 'light';
  try {
    const saved = localStorage.getItem('site-theme');
    if (saved === 'light' || saved === 'dark') theme = saved;
  } catch {
    // The page also works when browser storage is unavailable.
  }
  document.documentElement.dataset.theme = theme;
  document.documentElement.style.colorScheme = theme;
})();
