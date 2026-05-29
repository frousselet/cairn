/* split-pane.js
 *
 * Keyboard navigation + URL sync for split-pane list ↔ detail layouts.
 *
 * Markup contract:
 *   <div class="split-pane" data-split-param="focus">
 *     <div class="split-pane__list" role="listbox">
 *       <a class="split-pane__row"
 *          data-split-id="<uuid>"
 *          hx-get="<detail partial url>"
 *          hx-target=".split-pane__detail"
 *          hx-swap="innerHTML"
 *          hx-push-url="<list url>?focus=<uuid>">
 *          ...
 *       </a>
 *       ...
 *     </div>
 *     <div class="split-pane__detail" role="region" aria-live="polite">
 *       <!-- empty by default; populated via HTMX when a row is activated -->
 *     </div>
 *   </div>
 *
 * Behaviour:
 *   - j / ArrowDown: select next row
 *   - k / ArrowUp:   select previous row
 *   - Enter:         open the selected row in full screen (its inner <a href>)
 *   - Escape:        clear the detail panel (removes ?focus from the URL)
 *   - On load, if the URL has ?<split-param>=<id>, that row is activated.
 *
 * No-op if no .split-pane is present on the page. Safe to load globally.
 */
(function () {
  'use strict';

  function activate(panel, row) {
    if (!row) return;
    panel.querySelectorAll('.split-pane__row.active').forEach(function (el) {
      el.classList.remove('active');
      el.setAttribute('aria-selected', 'false');
    });
    row.classList.add('active');
    row.setAttribute('aria-selected', 'true');
    row.scrollIntoView({ block: 'nearest' });
    // HTMX is in charge of fetching the detail; we just trigger its event.
    if (window.htmx) window.htmx.trigger(row, 'split:activate');
    else row.click();
  }

  function focusedRow(panel) {
    return panel.querySelector('.split-pane__row.active');
  }

  function siblings(panel) {
    return Array.prototype.slice.call(
      panel.querySelectorAll('.split-pane__row')
    );
  }

  function clearDetail(panel) {
    var detail = panel.querySelector('.split-pane__detail');
    if (detail) detail.innerHTML = '';
    panel.querySelectorAll('.split-pane__row.active').forEach(function (el) {
      el.classList.remove('active');
      el.setAttribute('aria-selected', 'false');
    });
    // Strip the focus param from the URL without reloading.
    var url = new URL(window.location.href);
    var param = panel.dataset.splitParam || 'focus';
    url.searchParams.delete(param);
    window.history.replaceState({}, '', url.toString());
  }

  function init(panel) {
    var rows = siblings(panel);
    if (!rows.length) return;

    // Activate the row matching ?<split-param>=<id> on load.
    var url = new URL(window.location.href);
    var param = panel.dataset.splitParam || 'focus';
    var focusId = url.searchParams.get(param);
    if (focusId) {
      var target = panel.querySelector(
        '.split-pane__row[data-split-id="' + CSS.escape(focusId) + '"]'
      );
      if (target) activate(panel, target);
    }

    // Click on a row → activate it (in addition to whatever HTMX is wired to do).
    panel.addEventListener('click', function (e) {
      var row = e.target.closest('.split-pane__row');
      if (!row || !panel.contains(row)) return;
      activate(panel, row);
    });

    // Keyboard navigation: j/k, ArrowUp/ArrowDown, Enter, Escape.
    document.addEventListener('keydown', function (e) {
      // Skip when typing in an input
      var tag = e.target.tagName;
      if (tag === 'INPUT' || tag === 'TEXTAREA' || e.target.isContentEditable) {
        return;
      }
      if (!document.contains(panel)) return;
      var rows = siblings(panel);
      if (!rows.length) return;
      var current = focusedRow(panel);
      var index = current ? rows.indexOf(current) : -1;

      if (e.key === 'j' || e.key === 'ArrowDown') {
        e.preventDefault();
        activate(panel, rows[Math.min(index + 1, rows.length - 1)]);
      } else if (e.key === 'k' || e.key === 'ArrowUp') {
        e.preventDefault();
        activate(panel, rows[Math.max(index - 1, 0)]);
      } else if (e.key === 'Enter' && current) {
        var link = current.querySelector('a[href]');
        if (link) {
          e.preventDefault();
          window.location.href = link.href;
        }
      } else if (e.key === 'Escape' && current) {
        e.preventDefault();
        clearDetail(panel);
      }
    });
  }

  function bootstrap() {
    document.querySelectorAll('.split-pane').forEach(init);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', bootstrap);
  } else {
    bootstrap();
  }
  document.body.addEventListener('htmx:afterSettle', bootstrap);
})();
