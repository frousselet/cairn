/* SPDX-License-Identifier: AGPL-3.0-or-later
 * SPDX-FileCopyrightText: 2026 François Rousselet
 *
 * Declarative actions : what an inline event handler did, without one.
 *
 * The Content Security Policy (core/csp.py) refuses inline handlers
 * (onclick="...") : they are script written into the markup, which is exactly
 * what an injection writes. An element names an action instead :
 *
 *     <button data-on-click="deletePasskey" data-arg="{{ pk.id }}">
 *
 * and the page registers the function once :
 *
 *     window.cairnActions.deletePasskey = function (id, element, event) { ... };
 *
 * The action receives data-arg, data-arg2 and data-arg3 (those present, as
 * strings), then the element and the event; `this` is the element. Returning
 * false cancels the event's default action. Events : click, change, input,
 * keyup, submit (data-on-change="...", and so on).
 *
 * Only a function registered in window.cairnActions can be named : markup
 * cannot reach an arbitrary global (fetch, open...), so content that carried
 * a data-on-click attribute past the sanitiser could still call nothing a
 * page did not offer.
 *
 * Two attributes need no function :
 *     data-confirm="Question ?"   on a form, a button or a link : ask first.
 *     data-on-change="submitForm" and the other built-ins at the end of
 *     this file.
 */
(function () {
  'use strict';

  var actions = window.cairnActions = window.cairnActions || {};
  var EVENTS = ['click', 'change', 'input', 'keyup', 'submit'];
  var ARGUMENTS = ['data-arg', 'data-arg2', 'data-arg3'];

  function argumentsOf(element) {
    var values = [];
    ARGUMENTS.forEach(function (name) {
      if (element.hasAttribute(name)) values.push(element.getAttribute(name));
    });
    return values;
  }

  EVENTS.forEach(function (type) {
    var attribute = 'data-on-' + type;
    document.addEventListener(type, function (event) {
      var origin = event.target;
      if (!origin || !origin.closest) return;
      var element = origin.closest('[' + attribute + ']');
      if (!element) return;
      var action = actions[element.getAttribute(attribute)];
      if (typeof action !== 'function') return;
      /* A link used as a button does not follow its href. */
      if (type === 'click' && element.tagName === 'A') event.preventDefault();
      var result = action.apply(element, argumentsOf(element).concat([element, event]));
      if (result === false) event.preventDefault();
    });
  });

  /* Confirmation, asked before anything else hears the event (capture) : a
     refusal stops the submission, the HTMX request and any action. */
  function confirmed(element, event) {
    if (window.confirm(element.getAttribute('data-confirm'))) return;
    event.preventDefault();
    event.stopImmediatePropagation();
  }
  document.addEventListener('submit', function (event) {
    var form = event.target;
    if (form && form.matches && form.matches('form[data-confirm]')) confirmed(form, event);
  }, true);
  document.addEventListener('click', function (event) {
    var origin = event.target;
    var element = origin && origin.closest && origin.closest('button[data-confirm], a[data-confirm]');
    if (element) confirmed(element, event);
  }, true);

  /* ── Built-in actions ─────────────────────────────── */

  /* A select or a checkbox that submits its form when changed. */
  actions.submitForm = function (element) {
    var form = element.form || element.closest('form');
    if (form) form.submit();
  };

  /* The help of a page (templates/includes/help_modal.html) : hide it, or
     bring it back. The choice is kept for the reader; focus follows what is
     shown, so a keyboard or a screen reader lands on it. */
  function csrfToken() {
    var field = document.querySelector('[name=csrfmiddlewaretoken]');
    if (field) return field.value;
    return (document.cookie.match(/csrftoken=([^;]+)/) || [])[1] || '';
  }
  function setPageHelp(element, hidden) {
    var block = element.closest('[data-help]');
    if (!block) return;
    var banner = block.querySelector('.help-banner');
    var opener = block.querySelector('.page-help__open');
    if (!banner || !opener) return;
    banner.hidden = hidden;
    opener.hidden = !hidden;
    (hidden ? opener : banner).focus();
    fetch(block.getAttribute('data-help-url'), {
      method: 'POST',
      headers: {'X-CSRFToken': csrfToken(), 'Content-Type': 'application/json'},
      body: JSON.stringify({key: block.getAttribute('data-helper-key'), dismissed: hidden})
    }).catch(function () { /* offline : the choice holds for this page only */ });
  }
  actions.hidePageHelp = function (element) { setPageHelp(element, true); };
  actions.showPageHelp = function (element) { setPageHelp(element, false); };

  actions.historyBack = function () { window.history.back(); };
  actions.reloadPage = function () { window.location.reload(); };

  /* Copy the value of the field whose id is given, and show a tick on the
     button for a moment. */
  actions.copyValue = function (id, button) {
    var field = document.getElementById(id);
    if (!field || !navigator.clipboard) return;
    navigator.clipboard.writeText(field.value).then(function () {
      var icon = button.querySelector('.bi');
      if (!icon) return;
      var previous = icon.className;
      icon.className = 'bi bi-check';
      setTimeout(function () { icon.className = previous; }, 1500);
    });
  };
})();
