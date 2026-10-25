/* School Hack: German → English at display time.
 *
 * The app is written in German. When English is selected (cookie "lang=en"),
 * base.html loads the dictionary (/static/i18n/en.js) and this file, which
 * replaces what the page shows: text, placeholders, titles, aria-labels,
 * alert/confirm texts and Chart.js labels, also for content added later by JS.
 *
 * Only what is displayed changes. Form values, data attributes and the data
 * the scripts compare (e.g. radio values used for grading) stay German.
 * Exception: the tutor's ready-made questions (data-q, data-quick) are
 * translated, because they are sent to the model as the student's message.
 *
 * Add a translation: put the exact German text into "words" in en.js, or a
 * pattern for text with numbers/names. Missing German text is listed by
 * running  SH_I18N.missing()  in the browser console.
 */
(function () {
  'use strict';
  const D = window.SH_EN || { words: {}, patterns: [] };
  const words = new Map(Object.entries(D.words));
  const patterns = D.patterns || [];
  const missing = new Set();
  const GERMAN = /[äöüßÄÖÜ]|\b(der|die|das|und|ist|nicht|eine?|mit|zu|du|von|für|auf|noch|wie|was|bitte|oder|zum|zur|dein|deine)\b/;

  const norm = s => s.replace(/\s+/g, ' ').trim();
  // English decimal point in numbers that were written with a German comma.
  const decimals = s => /^[\d\s.,−+\-–/·]+$/.test(s) ? s.replace(/(\d),(\d)/g, '$1.$2') : s;
  // A formula line such as "n = m / M = 58,5 g / 58,5 g/mol = 1 mol" has no
  // words to translate, only decimal commas.
  const formula = s => /\d,\d/.test(s) && !/[a-zäöüß]{3,}/i.test(s.replace(/\b(mol|log|g\/mol|mol\/L)\b/g, ''))
    ? s.replace(/(\d),(\d)/g, '$1.$2') : null;

  function lookup(s, depth) {
    if (words.has(s)) return words.get(s);
    for (const [re, out] of patterns) {
      const m = re.exec(s);
      if (!m) continue;
      return typeof out === 'function'
        ? out(m, x => part(x, depth))
        : out.replace(/\$(\d)/g, (_, i) => part(m[+i] || '', depth));
    }
    return formula(s);
  }
  // A captured piece of a pattern: translate it if known, else keep it.
  function part(x, depth) {
    if (depth > 4) return x;
    const r = lookup(norm(x), depth + 1);
    return r == null ? decimals(x) : r;
  }
  const cache = new Map();
  function t(s) {
    if (typeof s !== 'string') return s;
    const n = norm(s);
    if (!n) return s;
    let r = cache.get(n);
    if (r === undefined) {
      r = lookup(n, 0);
      if (r == null && GERMAN.test(n)) missing.add(n);
      if (cache.size > 5000) cache.clear();
      cache.set(n, r);
    }
    if (r == null) return s;
    return (/^\s/.test(s) ? ' ' : '') + r + (/\s$/.test(s) ? ' ' : '');
  }

  window.SH_I18N = { t, missing: () => [...missing].sort() };
  if (typeof document === 'undefined') return;   // used by the Node coverage check

  // ---- page text -----------------------------------------------------------
  const SKIP = new Set(['SCRIPT', 'STYLE', 'TEXTAREA', 'CODE', 'PRE', 'NOSCRIPT']);
  const ATTRS = ['placeholder', 'title', 'aria-label', 'alt', 'data-q', 'data-quick'];
  const written = new WeakMap();   // text node -> value we last wrote

  const skipped = el => !el || SKIP.has(el.tagName) || el.isContentEditable || (el.closest && el.closest('[data-no-i18n]'));
  function text(node) {
    if (written.get(node) === node.nodeValue || skipped(node.parentElement)) return;
    const r = t(node.nodeValue);
    if (r !== node.nodeValue) node.nodeValue = r;
    written.set(node, node.nodeValue);
  }
  function attrs(el) {
    for (const a of ATTRS) {
      const v = el.getAttribute(a);
      if (v) { const r = t(v); if (r !== v) el.setAttribute(a, r); }
    }
    if (el.tagName === 'INPUT' && /^(button|submit|reset)$/i.test(el.type) && el.value) {
      const r = t(el.value); if (r !== el.value) el.value = r;
    }
  }
  function walk(root) {
    if (root.nodeType === 3) return text(root);
    if (root.nodeType !== 1 || skipped(root)) return;
    attrs(root);
    const w = document.createTreeWalker(root, NodeFilter.SHOW_ELEMENT | NodeFilter.SHOW_TEXT, {
      acceptNode: n => n.nodeType === 1 && skipped(n) ? NodeFilter.FILTER_REJECT : NodeFilter.FILTER_ACCEPT,
    });
    for (let n = w.nextNode(); n; n = w.nextNode()) n.nodeType === 3 ? text(n) : attrs(n);
  }

  new MutationObserver(records => {
    for (const r of records) {
      if (r.type === 'childList') r.addedNodes.forEach(walk);
      else if (r.type === 'characterData') text(r.target);
      else if (r.type === 'attributes') attrs(r.target);
    }
  }).observe(document.documentElement, {
    childList: true, subtree: true, characterData: true, attributes: true, attributeFilter: ATTRS,
  });
  document.addEventListener('DOMContentLoaded', () => { walk(document.body); document.title = t(document.title); });

  // ---- popups --------------------------------------------------------------
  for (const name of ['alert', 'confirm', 'prompt']) {
    const orig = window[name].bind(window);
    window[name] = (msg, ...rest) => orig(t(String(msg ?? '')), ...rest);
  }

  // ---- canvas text (chart plugins that draw their own labels) ---------------
  const fillText = CanvasRenderingContext2D.prototype.fillText;
  CanvasRenderingContext2D.prototype.fillText = function (s, ...rest) {
    return fillText.call(this, typeof s === 'string' ? t(s) : s, ...rest);
  };

  // ---- Chart.js (labels are drawn on a canvas, not in the DOM) --------------
  const tl = l => Array.isArray(l) ? l.map(t) : t(l);
  const chartPlugin = {
    id: 'sh-i18n',
    beforeUpdate(chart) {
      const d = chart.data || {};
      if (Array.isArray(d.labels)) d.labels = d.labels.map(tl);
      (d.datasets || []).forEach(ds => { if (ds.label) ds.label = t(ds.label); });
      const o = chart.options || {};
      if (o.plugins && o.plugins.title && o.plugins.title.text) o.plugins.title.text = tl(o.plugins.title.text);
      Object.values(o.scales || {}).forEach(sc => {
        if (sc.title && sc.title.text) sc.title.text = tl(sc.title.text);
        const cb = sc.ticks && sc.ticks.callback;
        if (cb && !cb.__shI18n) {
          sc.ticks.callback = function (...a) { return tl(cb.apply(this, a)); };
          sc.ticks.callback.__shI18n = true;
        }
      });
    },
    beforeTooltipDraw(chart, { tooltip }) {
      tooltip.title = (tooltip.title || []).map(t);
      (tooltip.body || []).forEach(b => { b.lines = b.lines.map(t); });
      tooltip.footer = (tooltip.footer || []).map(t);
    },
  };
  let ChartRef = window.Chart;
  const hook = C => { try { C.register(chartPlugin); } catch (e) { /* older Chart.js */ } };
  if (ChartRef) hook(ChartRef);
  else Object.defineProperty(window, 'Chart', {
    configurable: true,
    get: () => ChartRef,
    set: v => { ChartRef = v; if (v && v.register) hook(v); },
  });
})();
