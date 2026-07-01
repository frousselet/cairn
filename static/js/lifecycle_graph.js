/*
 * Shared lifecycle graph renderer (dagre + d3).
 *
 * Lays out and draws a lifecycle as a directed graph into an <svg>. Used by both
 * the detail-page stepper and the admin editor.
 *
 * "From any state" transitions (source "*") are NOT exploded into one edge per
 * step (that produces a cobweb): the target is detached BELOW the main flow and
 * fed by a single arrow starting from a small dot that stands for "any state".
 *
 * window.CairnLifecycleGraph.render(svgEl, nodes, edges, opts)
 *   nodes: [{id, label, kind:'draft'|'intermediate'|'archived', tone, state, number, actionable, requires_comment, action_label}]
 *   edges: [{source, target, label, kind:'forward'|'loop'|'restore'|'exit'}]  (source may be "*")
 *   opts:  {rankdir, containerWidth, mode:'display'|'editor', selected, connectFrom, onNodeClick}
 */
(function () {
  var SVGNS = "http://www.w3.org/2000/svg";
  var mctx = document.createElement("canvas").getContext("2d");

  function token(name, fb) {
    var v = getComputedStyle(document.documentElement).getPropertyValue(name);
    return (v || "").trim() || fb;
  }
  function measure(t) {
    mctx.font = '600 13px "GitLab Sans", system-ui, sans-serif';
    return mctx.measureText(t || "").width;
  }
  function pillWidth(n) {
    return Math.max(72, Math.round(measure(n.label || n.id) + 36) + (n.number ? 18 : 0));
  }

  function layout(nodes, edges, rankdir) {
    var H = 40, byId = {};
    nodes.forEach(function (n) { byId[n.id] = n; });

    var wildcard = [], normal = [];
    edges.forEach(function (e) {
      if (!byId[e.target]) { return; }
      if (e.source === "*" || e.source === "any") { wildcard.push(e); }
      else if (byId[e.source] && e.source !== e.target) { normal.push(e); }
    });
    // Targets fed only from "any" hang below the spine.
    var detached = {};
    wildcard.forEach(function (e) { detached[e.target] = 1; });

    var mainNodes = nodes.filter(function (n) { return !detached[n.id]; });
    var mainEdges = normal.filter(function (e) { return !detached[e.source] && !detached[e.target]; });
    var incident = normal.filter(function (e) { return detached[e.source] || detached[e.target]; });

    var g = new dagre.graphlib.Graph({ multigraph: true });
    g.setGraph({ rankdir: rankdir, nodesep: 26, ranksep: 62, edgesep: 18, marginx: 20, marginy: 22, ranker: "network-simplex" });
    g.setDefaultEdgeLabel(function () { return {}; });
    mainNodes.forEach(function (n) { g.setNode(n.id, { width: pillWidth(n), height: H }); });
    mainEdges.forEach(function (e, i) { g.setEdge(e.source, e.target, {}, "e" + i); });
    try { dagre.layout(g); } catch (e) { return null; }

    var pos = {}, minX = 1e9, maxX = -1e9, maxY = -1e9, minY = 1e9;
    mainNodes.forEach(function (n) {
      var p = g.node(n.id);
      pos[n.id] = { x: p.x, y: p.y, w: p.width, h: H };
      minX = Math.min(minX, p.x - p.width / 2); maxX = Math.max(maxX, p.x + p.width / 2);
      minY = Math.min(minY, p.y - H / 2); maxY = Math.max(maxY, p.y + H / 2);
    });
    if (!mainNodes.length) { minX = 0; maxX = 200; minY = 0; maxY = H; }

    // Detached (any-fed) targets in a row below the spine, centred under it.
    var detIds = Object.keys(detached).filter(function (id) { return byId[id]; });
    var rowY = maxY + 78, total = 0;
    detIds.forEach(function (id) { total += pillWidth(byId[id]) + 34; });
    var cx = (minX + maxX) / 2, x = cx - total / 2;
    detIds.forEach(function (id) { var w = pillWidth(byId[id]); pos[id] = { x: x + w / 2, y: rowY, w: w, h: H }; x += w + 34; });

    var outEdges = [], dots = [];
    mainEdges.forEach(function (e, i) {
      var de = g.edge(e.source, e.target, "e" + i);
      outEdges.push({ points: (de && de.points) ? de.points : [pos[e.source], pos[e.target]], kind: e.kind, label: e.label });
    });
    // One dot -> target per "any" transition (the dot is the arrow's origin).
    wildcard.forEach(function (e) {
      var t = pos[e.target]; if (!t) { return; }
      var dot = { x: t.x, y: t.y - t.h / 2 - 26 };
      dots.push({ x: dot.x, y: dot.y, label: e.label });
      outEdges.push({ points: [dot, { x: t.x, y: t.y - t.h / 2 }], kind: "exit", label: "" });
    });
    // Edges touching a detached node (e.g. restore archived -> draft) as a curve.
    incident.forEach(function (e) {
      var s = pos[e.source], t = pos[e.target]; if (!s || !t) { return; }
      outEdges.push({ points: [{ x: s.x, y: s.y }, { x: (s.x + t.x) / 2, y: Math.max(s.y, t.y) + 26 }, { x: t.x, y: t.y }], kind: e.kind || "restore", label: e.label });
    });

    // Normalize so nothing sits at a negative coordinate.
    var pad = 16, allX = [], allY = [];
    Object.keys(pos).forEach(function (id) { allX.push(pos[id].x - pos[id].w / 2, pos[id].x + pos[id].w / 2); allY.push(pos[id].y - H / 2, pos[id].y + H / 2); });
    dots.forEach(function (d) { allX.push(d.x - 6, d.x + 6); allY.push(d.y - 6); });
    var gMinX = Math.min.apply(null, allX), gMinY = Math.min.apply(null, allY);
    var dx = pad - gMinX, dy = pad - gMinY;
    Object.keys(pos).forEach(function (id) { pos[id].x += dx; pos[id].y += dy; });
    dots.forEach(function (d) { d.x += dx; d.y += dy; });
    outEdges.forEach(function (e) { e.points = e.points.map(function (p) { return { x: p.x + dx, y: p.y + dy }; }); });

    var w = Math.max.apply(null, allX) + dx + pad;
    var h = Math.max.apply(null, allY) + dy + pad;
    return { pos: pos, edges: outEdges, dots: dots, width: w, height: h, detached: detached };
  }

  function styleNode(n, opts) {
    var accent = token("--accent", "#1E3A8A"), muted = token("--text-muted", "#64748b");
    var border = token("--border-color", "#e2e8f0"), surface = token("--surface", "#ffffff");
    var s = { fill: surface, text: token("--text", "#0f172a"), stroke: border, dash: null, weight: 1 };
    if (n.kind === "archived") { s.dash = "5 4"; s.stroke = muted; s.text = muted; }
    if (opts.mode === "editor") {
      if (n.kind === "draft") { s.fill = accent; s.text = "#ffffff"; s.stroke = accent; }
      if (n.id === opts.selected || n.id === opts.connectFrom) { s.stroke = token("--bs-success", "#16a34a"); s.weight = 2.5; }
    } else {
      if (n.state === "done") { s.fill = "color-mix(in srgb, " + accent + " 10%, " + surface + ")"; }
      if (n.state === "current") { s.fill = accent; s.text = "#ffffff"; s.stroke = accent; s.weight = 2; }
      if (n.state === "future") { s.text = muted; }
      if (n.actionable) { s.stroke = token("--bs-success", "#16a34a"); s.weight = 2; }
    }
    return s;
  }

  function render(svg, nodes, edges, opts) {
    opts = opts || {};
    while (svg.firstChild) { svg.removeChild(svg.firstChild); }
    if (!window.dagre || !window.d3 || !nodes || !nodes.length) { return; }
    var rankdir = opts.rankdir || ((opts.containerWidth && opts.containerWidth < 640) ? "TB" : "LR");
    var L = layout(nodes, edges, rankdir);
    if (!L) { return; }
    var byId = {}; nodes.forEach(function (n) { byId[n.id] = n; });
    svg.setAttribute("viewBox", "0 0 " + L.width + " " + L.height);
    svg.setAttribute("width", "100%"); svg.style.height = "auto";

    var accent = token("--accent", "#1E3A8A"), muted = token("--text-muted", "#94a3b8");
    var uid = "lg" + Math.floor(L.width) + "x" + Math.floor(L.height);
    var line = d3.line().x(function (p) { return p.x; }).y(function (p) { return p.y; }).curve(d3.curveBasis);
    var defs = document.createElementNS(SVGNS, "defs");
    [[uid + "a", accent], [uid + "m", muted]].forEach(function (p) {
      var m = document.createElementNS(SVGNS, "marker");
      m.setAttribute("id", p[0]); m.setAttribute("viewBox", "0 -5 10 10"); m.setAttribute("refX", "9");
      m.setAttribute("refY", "0"); m.setAttribute("markerWidth", "6.5"); m.setAttribute("markerHeight", "6.5"); m.setAttribute("orient", "auto");
      var pa = document.createElementNS(SVGNS, "path"); pa.setAttribute("d", "M0,-4.5L9,0L0,4.5"); pa.setAttribute("fill", p[1]);
      m.appendChild(pa); defs.appendChild(m);
    });
    svg.appendChild(defs);

    L.edges.forEach(function (e) {
      if (!e.points || e.points.length < 2) { return; }
      var loop = e.kind === "loop" || e.kind === "restore";
      var path = document.createElementNS(SVGNS, "path");
      path.setAttribute("d", line(e.points)); path.setAttribute("fill", "none");
      path.setAttribute("stroke", loop ? muted : accent); path.setAttribute("stroke-width", "1.6"); path.setAttribute("opacity", "0.85");
      if (loop) { path.setAttribute("stroke-dasharray", "5 4"); }
      path.setAttribute("marker-end", "url(#" + (loop ? uid + "m" : uid + "a") + ")");
      // Transition labels are not drawn (they clutter tight loops); kept as a
      // hover tooltip so the verb is still discoverable.
      if (e.label) { var tt = document.createElementNS(SVGNS, "title"); tt.textContent = e.label; path.appendChild(tt); }
      svg.appendChild(path);
    });
    // "any state" origin dots (no visible label).
    L.dots.forEach(function (d) {
      var c = document.createElementNS(SVGNS, "circle");
      c.setAttribute("cx", d.x); c.setAttribute("cy", d.y); c.setAttribute("r", "4"); c.setAttribute("fill", accent);
      if (d.label) { var tt = document.createElementNS(SVGNS, "title"); tt.textContent = d.label; c.appendChild(tt); }
      svg.appendChild(c);
    });

    nodes.forEach(function (n) {
      var p = L.pos[n.id]; if (!p) { return; }
      var st = styleNode(n, opts);
      var g = document.createElementNS(SVGNS, "g");
      g.setAttribute("transform", "translate(" + (p.x - p.w / 2) + "," + (p.y - p.h / 2) + ")");
      var clickable = opts.onNodeClick && (opts.mode === "editor" || n.actionable);
      if (clickable) {
        g.style.cursor = "pointer"; g.setAttribute("role", "button"); g.setAttribute("tabindex", "0");
        g.addEventListener("click", function () { opts.onNodeClick(n.id, n); });
        g.addEventListener("keydown", function (ev) { if (ev.key === "Enter" || ev.key === " ") { ev.preventDefault(); opts.onNodeClick(n.id, n); } });
      }
      var rect = document.createElementNS(SVGNS, "rect");
      rect.setAttribute("width", p.w); rect.setAttribute("height", p.h); rect.setAttribute("rx", p.h / 2);
      rect.setAttribute("fill", st.fill); rect.setAttribute("stroke", st.stroke); rect.setAttribute("stroke-width", st.weight);
      if (st.dash) { rect.setAttribute("stroke-dasharray", st.dash); }
      g.appendChild(rect);
      var tx = document.createElementNS(SVGNS, "text");
      tx.setAttribute("x", p.w / 2); tx.setAttribute("y", p.h / 2); tx.setAttribute("text-anchor", "middle");
      tx.setAttribute("dominant-baseline", "central"); tx.setAttribute("font-size", "13"); tx.setAttribute("font-weight", "600"); tx.setAttribute("fill", st.text);
      tx.textContent = (n.number ? n.number + "  " : "") + (n.label || n.id);
      g.appendChild(tx);
      if (n.actionable && n.action_label) { var tit = document.createElementNS(SVGNS, "title"); tit.textContent = n.action_label; g.appendChild(tit); }
      svg.appendChild(g);
    });
  }

  function ensureLibs(d3src, dagresrc, cb) {
    function load(id, src, done) {
      if (document.getElementById(id)) { return done(); }
      var s = document.createElement("script"); s.id = id; s.src = src; s.onload = done; document.head.appendChild(s);
    }
    (window.d3 ? function (c) { c(); } : function (c) { load("d3-lib", d3src, c); })(function () {
      (window.dagre ? function (c) { c(); } : function (c) { load("dagre-lib", dagresrc, c); })(cb);
    });
  }

  window.CairnLifecycleGraph = { render: render, layout: layout, ensureLibs: ensureLibs };
})();
