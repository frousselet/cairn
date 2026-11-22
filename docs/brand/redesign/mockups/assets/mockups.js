/*
 * Mockup behaviour, written the way Cairn's pages are : no inline handler,
 * an element names an action (data-on-click="name" data-arg="..."), and only
 * actions registered below can run. Theme : system, light or dark, applied as
 * Basecoat's `.dark` class plus Bootstrap's `data-bs-theme`.
 */
(function () {
  "use strict";

  var root = document.documentElement;
  var media = window.matchMedia("(prefers-color-scheme: dark)");

  function storedTheme() {
    try { return localStorage.getItem("cairn-mockup-theme") || "system"; } catch (e) { return "system"; }
  }

  // A host page (the artifact viewer) may state the reader's choice on the
  // root element ; "system" then follows it rather than the OS setting.
  function systemIsDark() {
    var host = root.getAttribute("data-theme");
    if (host === "dark") return true;
    if (host === "light") return false;
    return media.matches;
  }

  function applyTheme(pref) {
    var dark = pref === "dark" || (pref === "system" && systemIsDark());
    root.classList.toggle("dark", dark);
    root.setAttribute("data-bs-theme", dark ? "dark" : "light");
    root.setAttribute("data-theme-preference", pref);
    document.querySelectorAll("[data-theme-toggle]").forEach(function (btn) {
      btn.setAttribute("aria-label", dark ? "Use the light theme" : "Use the dark theme");
      btn.setAttribute("aria-pressed", dark ? "true" : "false");
    });
  }

  applyTheme(storedTheme());
  media.addEventListener("change", function () {
    if (storedTheme() === "system") applyTheme("system");
  });
  new MutationObserver(function () {
    if (storedTheme() === "system") applyTheme("system");
  }).observe(root, { attributes: true, attributeFilter: ["data-theme"] });

  var actions = {
    toggleTheme: function () {
      var next = root.classList.contains("dark") ? "light" : "dark";
      try { localStorage.setItem("cairn-mockup-theme", next); } catch (e) { /* private mode */ }
      applyTheme(next);
    },
    toggleSidebar: function () {
      var sidebar = document.querySelector(".sidebar");
      if (sidebar && typeof sidebar.toggle === "function") sidebar.toggle();
    },
    openDialog: function (id) {
      var dialog = document.getElementById(id);
      if (dialog && !dialog.open) dialog.showModal();
    },
    closeDialog: function (id, el) {
      var dialog = id ? document.getElementById(id) : el.closest("dialog");
      if (dialog) dialog.close();
    },
    setDensity: function (density, el) {
      var table = document.querySelector("[data-density-target]");
      if (!table) return;
      table.classList.toggle("is-compact", density === "compact");
      el.parentElement.querySelectorAll("button").forEach(function (b) {
        b.setAttribute("aria-pressed", b === el ? "true" : "false");
      });
    },
    removeChip: function (id, el) {
      var chip = el.closest(".chip");
      if (chip) chip.remove();
    },
    paletteState: function (state, el) {
      document.querySelectorAll("[data-palette-state]").forEach(function (section) {
        section.hidden = section.getAttribute("data-palette-state") !== state;
      });
      var input = document.querySelector("[data-palette-input]");
      if (input) input.setAttribute("aria-expanded", state === "results" ? "true" : "false");
      el.parentElement.querySelectorAll("button").forEach(function (b) {
        b.setAttribute("aria-pressed", b === el ? "true" : "false");
      });
    },
    noop: function () { return false; }
  };

  document.addEventListener("click", function (event) {
    var el = event.target.closest("[data-on-click]");
    if (!el) return;
    var fn = actions[el.getAttribute("data-on-click")];
    if (!fn) return;
    if (el.tagName === "A") event.preventDefault();
    fn.call(el, el.getAttribute("data-arg"), el, event);
  });

  document.addEventListener("DOMContentLoaded", function () {
    applyTheme(storedTheme());
    var open = document.body.getAttribute("data-open-dialog");
    if (open) actions.openDialog(open);
  });
})();
