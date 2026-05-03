// Section loader
async function loadSection(id, file) {
  try {
    const res = await fetch('sections/' + file);
    if (!res.ok) throw new Error('HTTP ' + res.status);
    document.getElementById(id).innerHTML = await res.text();
  } catch (e) {
    console.error('Failed to load section:', file, e);
  }
}

// Catalog renderer
async function loadCatalog() {
  try {
    const res = await fetch('data/catalog.json');
    const videos = await res.json();
    const grid = document.getElementById('catalog-grid');
    if (!grid) return;

    grid.innerHTML = videos.map(v => {
      const toolTags = v.tools.slice(0, 3).map(t =>
        '<span class="catalog-tag">' + escHtml(t) + '</span>'
      ).join('');

      if (v.status === 'published' && v.youtube_id) {
        const thumb = 'https://img.youtube.com/vi/' + v.youtube_id + '/hqdefault.jpg';
        return '<div class="catalog-card">' +
          '<a href="' + v.youtube_url + '" target="_blank" rel="noopener">' +
          '<img class="catalog-thumb" src="' + thumb + '" alt="' + escHtml(v.title) + '" loading="lazy">' +
          '</a>' +
          '<div class="catalog-body">' +
          '<h4>' + escHtml(v.title) + '</h4>' +
          '<p>' + escHtml(v.desc) + '</p>' +
          '<div class="catalog-tags">' + toolTags + '</div>' +
          '<a href="' + v.youtube_url + '" target="_blank" rel="noopener" class="catalog-watch">Watch Demo &rarr;</a>' +
          '</div></div>';
      } else {
        return '<div class="catalog-card" style="opacity:0.6;">' +
          '<div class="catalog-thumb-placeholder">&#9654;&#65039;</div>' +
          '<div class="catalog-body">' +
          '<h4>' + escHtml(v.title) + '</h4>' +
          '<p>' + escHtml(v.desc) + '</p>' +
          '<div class="catalog-tags">' + toolTags + '</div>' +
          '<span class="catalog-coming-soon">Coming soon</span>' +
          '</div></div>';
      }
    }).join('');
  } catch (e) {
    console.error('Failed to load catalog:', e);
  }
}

function escHtml(str) {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

// Modal logic (exposed globally for onclick attributes in sections)
window.openModal = function(modalId) {
  const el = document.getElementById('modal-' + modalId);
  if (el) { el.classList.add('active'); document.body.style.overflow = 'hidden'; }
};
window.closeModal = function(event) {
  if (event && event.target !== event.currentTarget) return;
  document.querySelectorAll('.modal-overlay').forEach(m => m.classList.remove('active'));
  document.body.style.overflow = '';
};

// FAQ accordion
function initFaq() {
  document.querySelectorAll('.faq-item').forEach(item => {
    const question = item.querySelector('.faq-question');
    const answer = item.querySelector('.faq-answer');
    if (!question || !answer) return;
    question.addEventListener('click', () => {
      const isOpen = answer.style.display === 'block';
      document.querySelectorAll('.faq-answer').forEach(a => a.style.display = 'none');
      document.querySelectorAll('.faq-question').forEach(q => q.classList.remove('open'));
      if (!isOpen) { answer.style.display = 'block'; question.classList.add('open'); }
    });
  });
}

// Keyboard close for modals
document.addEventListener('keydown', e => { if (e.key === 'Escape') window.closeModal(); });

// Boot — load all sections in parallel, then init interactive features
(async () => {
  await Promise.all([
    loadSection('nav', 'nav.html'),
    loadSection('hero', 'hero.html'),
    loadSection('stats', 'stats.html'),
    loadSection('problem', 'problem.html'),
    loadSection('transformation', 'transformation.html'),
    loadSection('testimonials', 'testimonials.html'),
    loadSection('process', 'process.html'),
    loadSection('services', 'services.html'),
    loadSection('portfolio', 'portfolio.html'),
    loadSection('catalog', 'catalog.html'),
    loadSection('guarantee', 'guarantee.html'),
    loadSection('faq', 'faq.html'),
    loadSection('comparison', 'comparison.html'),
    loadSection('cta', 'cta.html'),
    loadSection('footer', 'footer.html'),
  ]);

  // After all sections are in the DOM, load dynamic content and wire up interactions
  await loadCatalog();
  initFaq();
})();
