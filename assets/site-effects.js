(() => {
  'use strict';
  const motion = matchMedia('(prefers-reduced-motion: reduce)');
  const root = document.documentElement;
  const themeButtons = [...document.querySelectorAll('[data-theme-toggle]')];
  const currentTheme = () => root.dataset.theme === 'dark' ? 'dark' : 'light';
  const updateThemeButtons = () => {
    const dark = currentTheme() === 'dark';
    themeButtons.forEach((button) => {
      const label = dark ? 'Switch to light mode' : 'Switch to dark mode';
      button.setAttribute('aria-label', label);
      button.setAttribute('aria-pressed', String(dark));
      button.title = label;
      const icon = button.querySelector('[data-theme-icon]');
      if (icon) {
        icon.textContent = dark ? '☀' : '☾';
        icon.setAttribute('aria-hidden', 'true');
      }
    });
  };
  const applyTheme = (theme, remember = false) => {
    root.dataset.theme = theme === 'dark' ? 'dark' : 'light';
    root.style.colorScheme = root.dataset.theme;
    if (remember) {
      try { localStorage.setItem('site-theme', root.dataset.theme); } catch { /* Storage is optional. */ }
    }
    updateThemeButtons();
    drawNetwork();
  };
  themeButtons.forEach((button) => {
    button.addEventListener('click', () => applyTheme(currentTheme() === 'dark' ? 'light' : 'dark', true));
  });
  addEventListener('storage', (event) => {
    if (event.key === 'site-theme' || event.key === null) applyTheme(event.newValue);
  });
  updateThemeButtons();

  // The network is decorative: its elements never receive pointer or keyboard input.
  const canvas = document.createElement('canvas');
  canvas.className = 'ambient-network';
  canvas.setAttribute('aria-hidden', 'true');
  canvas.style.pointerEvents = 'none';
  const context = canvas.getContext('2d', {alpha: true});
  let nodes = [];
  let width = 1;
  let height = 1;
  let networkFrame = 0;
  let previousFrame = 0;
  let resizeFrame = 0;
  let pageActive = true;
  const palettes = {
    light: {line: '109,79,214', dots: ['153,96,0', '109,79,214', '10,116,152'], lineAlpha: 0.15, dotAlpha: 0.32},
    dark: {line: '158,134,241', dots: ['207,163,94', '158,134,241', '74,171,201'], lineAlpha: 0.17, dotAlpha: 0.42}
  };
  function drawNetwork() {
    if (!context) return;
    const palette = palettes[currentTheme()];
    const reach = Math.min(210, Math.max(110, width * 0.24));
    context.clearRect(0, 0, width, height);
    context.lineWidth = 0.7;
    nodes.forEach((node, index) => {
      const x = node.x * width;
      const y = node.y * height;
      for (let next = index + 1; next < nodes.length; next++) {
        const other = nodes[next];
        const dx = x - other.x * width;
        const dy = y - other.y * height;
        const distance = Math.hypot(dx, dy);
        if (distance >= reach) continue;
        context.strokeStyle = `rgba(${palette.line},${palette.lineAlpha * (1 - distance / reach)})`;
        context.beginPath();
        context.moveTo(x, y);
        context.lineTo(other.x * width, other.y * height);
        context.stroke();
      }
      context.fillStyle = `rgba(${palette.dots[index % palette.dots.length]},${palette.dotAlpha})`;
      context.beginPath();
      context.arc(x, y, index % 4 === 0 ? 1.8 : 1.2, 0, Math.PI * 2);
      context.fill();
    });
  }
  const resizeNetwork = () => {
    resizeFrame = 0;
    if (!context) return;
    width = Math.max(1, innerWidth);
    height = Math.max(1, innerHeight);
    const ratio = Math.min(2, devicePixelRatio || 1, Math.sqrt(4000000 / (width * height)));
    canvas.width = Math.round(width * ratio);
    canvas.height = Math.round(height * ratio);
    canvas.style.width = `${width}px`;
    canvas.style.height = `${height}px`;
    context.setTransform(ratio, 0, 0, ratio, 0, 0);
    const count = Math.min(40, Math.max(16, Math.round(width * height / 35000)));
    nodes = nodes.slice(0, count);
    while (nodes.length < count) {
      nodes.push({x: Math.random(), y: Math.random(), vx: (Math.random() - 0.5) * 5, vy: (Math.random() - 0.5) * 5});
    }
    drawNetwork();
  };
  const animateNetwork = (now) => {
    networkFrame = 0;
    if (motion.matches || document.hidden || !pageActive || !context) return;
    const elapsed = now - previousFrame;
    if (!previousFrame || elapsed >= 1000 / 30) {
      const seconds = previousFrame ? Math.min(elapsed, 80) / 1000 : 0;
      previousFrame = now;
      nodes.forEach((node) => {
        node.x += node.vx * seconds / width;
        node.y += node.vy * seconds / height;
        if (node.x < 0 || node.x > 1) node.vx *= -1;
        if (node.y < 0 || node.y > 1) node.vy *= -1;
        node.x = Math.min(1, Math.max(0, node.x));
        node.y = Math.min(1, Math.max(0, node.y));
      });
      drawNetwork();
    }
    networkFrame = requestAnimationFrame(animateNetwork);
  };
  const updateNetworkMotion = () => {
    cancelAnimationFrame(networkFrame);
    networkFrame = 0;
    previousFrame = 0;
    if (!context || document.hidden || !pageActive) return;
    drawNetwork();
    if (!motion.matches) networkFrame = requestAnimationFrame(animateNetwork);
  };
  if (context) {
    document.body.prepend(canvas);
    resizeNetwork();
    updateNetworkMotion();
    addEventListener('resize', () => {
      if (!resizeFrame) resizeFrame = requestAnimationFrame(resizeNetwork);
    }, {passive: true});
    document.addEventListener('visibilitychange', updateNetworkMotion);
    addEventListener('pagehide', () => { pageActive = false; updateNetworkMotion(); });
    addEventListener('pageshow', () => { pageActive = true; updateNetworkMotion(); });
    motion.addEventListener('change', updateNetworkMotion);
  }

  const progress = document.createElement('div');
  progress.className = 'scroll-progress';
  progress.setAttribute('aria-hidden', 'true');
  document.body.prepend(progress);

  const topButton = document.createElement('button');
  topButton.type = 'button';
  topButton.className = 'back-to-top';
  topButton.setAttribute('aria-label', 'Back to top');
  topButton.title = 'Back to top';
  topButton.textContent = '↑';
  topButton.hidden = true;
  document.body.append(topButton);
  topButton.addEventListener('click', () => {
    window.scrollTo({top: 0, behavior: motion.matches ? 'auto' : 'smooth'});
    const title = document.querySelector('h1');
    if (title) {
      title.setAttribute('tabindex', '-1');
      title.focus({preventScroll: true});
    }
  });

  const header = document.querySelector('.topbar, .archive-header');
  const navigation = [...document.querySelectorAll('.topbar .nav a[href^="#"]')]
    .map((link) => ({link, section: document.getElementById(link.getAttribute('href').slice(1))}))
    .filter((item) => item.section);
  let scheduled = false;
  const updateScroll = () => {
    scheduled = false;
    const distance = document.documentElement.scrollHeight - innerHeight;
    const fraction = distance > 0 ? Math.min(1, Math.max(0, scrollY / distance)) : 0;
    progress.style.transform = `scaleX(${fraction})`;
    header?.classList.toggle('is-scrolled', scrollY > 24);
    topButton.hidden = scrollY < 700;
    if (navigation.length) {
      const offset = (header?.getBoundingClientRect().height || 80) + 50;
      let active = navigation[0];
      navigation.forEach((item) => {
        if (item.section.getBoundingClientRect().top <= offset) active = item;
      });
      navigation.forEach((item) => {
        if (item === active) item.link.setAttribute('aria-current', 'location');
        else item.link.removeAttribute('aria-current');
      });
    }
  };
  const requestUpdate = () => {
    if (!scheduled) {
      scheduled = true;
      requestAnimationFrame(updateScroll);
    }
  };
  addEventListener('scroll', requestUpdate, {passive: true});
  addEventListener('resize', requestUpdate, {passive: true});
  addEventListener('load', requestUpdate, {once: true});
  updateScroll();

  // Elements remain visible in the document. Animation is applied only when
  // they enter the viewport, so unavailable JS/observers never hide content.
  const animations = new Map();
  let observer;
  const targets = [...document.querySelectorAll(
    '.hero-copy, .hero-portrait, .hero-current, #personal, #education, #experience, #research, .skills-panel, #media, #contact, .section-heading, .project-card, .preview-item, .archive-masthead, .coverage-notice, .archive-entry'
  )];
  const startReveals = () => {
    observer?.disconnect();
    animations.forEach((animation) => animation.cancel());
    animations.clear();
    if (motion.matches || !('IntersectionObserver' in window) || !Element.prototype.animate) return;
    observer = new IntersectionObserver((observations) => {
      observations.forEach(({target, isIntersecting, boundingClientRect}) => {
        if (!isIntersecting) return;
        observer.unobserve(target);
        if (target.dataset.revealed || boundingClientRect.bottom < 0) return;
        target.dataset.revealed = 'true';
        const siblings = [...target.parentElement.children];
        const stagger = target.matches('.project-card, .preview-item, .archive-entry')
          ? (siblings.indexOf(target) % 3) * 55 : 0;
        const animation = target.animate(
          [{opacity: 0.35, transform: 'translateY(14px)'}, {opacity: 1, transform: 'translateY(0)'}],
          {duration: 620, delay: stagger, easing: 'cubic-bezier(.2,.65,.25,1)', fill: 'none'}
        );
        animations.set(target, animation);
        animation.finished.then(() => animations.delete(target), () => animations.delete(target));
      });
    }, {threshold: 0.04, rootMargin: '0px 0px -4% 0px'});
    targets.forEach((target) => observer.observe(target));
  };
  document.addEventListener('focusin', (event) => {
    animations.forEach((animation, target) => {
      if (target.contains(event.target)) animation.cancel();
    });
  });
  motion.addEventListener('change', startReveals);
  startReveals();
})();
