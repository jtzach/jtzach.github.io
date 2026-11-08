(() => {
  'use strict';
  const motion = matchMedia('(prefers-reduced-motion: reduce)');
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
          [{opacity: 0.18, transform: 'translateY(20px)'}, {opacity: 1, transform: 'translateY(0)'}],
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
