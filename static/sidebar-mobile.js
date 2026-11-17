(() => {
  const body = document.body;
  const toggle = document.querySelector('.side-toggle');
  const panel = document.getElementById('sidePanel');
  const closeBtn = document.querySelector('.side-close');
  const backdrop = document.querySelector('.side-backdrop');
  if (!toggle || !panel) return;

  const mobile = window.matchMedia('(max-width: 900px)');
  const moreBtn = document.querySelector('.tab-more');
  const tabScreens = new Set([...document.querySelectorAll('.tabbar .nav')].map((b) => b.dataset.screen));
  if (backdrop) backdrop.hidden = false;

  const setOpen = (open) => {
    body.classList.toggle('side-open', open);
    toggle.setAttribute('aria-expanded', String(open));
    toggle.setAttribute('aria-label', open ? 'Close menu' : 'Open menu');
    moreBtn?.setAttribute('aria-expanded', String(open));
    if (open) {
      (panel.querySelector('.nav.active') || closeBtn)?.focus();
    }
  };

  toggle.addEventListener('click', () => setOpen(!body.classList.contains('side-open')));
  moreBtn?.addEventListener('click', () => setOpen(!body.classList.contains('side-open')));
  closeBtn?.addEventListener('click', () => setOpen(false));
  backdrop?.addEventListener('click', () => setOpen(false));

  // Delegated, so nav items added later (e.g. "My companion" from agents.js) also close the drawer
  panel.addEventListener('click', (e) => {
    if (mobile.matches && e.target.closest('.nav')) setOpen(false);
  });
  document.querySelectorAll('[data-home]').forEach((el) =>
    el.addEventListener('click', () => setOpen(false))
  );

  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && body.classList.contains('side-open')) {
      setOpen(false);
      (moreBtn && getComputedStyle(moreBtn).display !== 'none' ? moreBtn : toggle).focus();
    }
  });

  // Light up "More" when the current screen only lives in the sheet (Memories, Plan, Companion...)
  const syncMore = () => {
    const id = document.querySelector('.screen.active')?.id;
    moreBtn?.classList.toggle('active', !!id && !tabScreens.has(id) && id !== 'moment' && id !== 'result');
  };
  // Observe all of <main> so screens injected later (agents.js) are covered too
  new MutationObserver(syncMore).observe(document.querySelector('main'), {
    subtree: true, childList: true, attributes: true, attributeFilter: ['class'],
  });
  syncMore();

  // Rotating to a wide screen while open shouldn't leave the page scroll-locked
  mobile.addEventListener('change', (e) => { if (!e.matches) setOpen(false); });
})();
