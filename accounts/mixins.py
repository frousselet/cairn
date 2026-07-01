from django.urls import reverse

from context.models import Scope


class HistoryUrlMixin:
    """Expose the lazy-loaded history panel URL on a detail view.

    Replaces the per-app ``HistoryMixin`` copies: the (potentially expensive)
    timeline diff computation moves to
    :class:`core.history_views.HistoryPartialView` and runs only when the
    off-canvas history panel is opened, not on every detail page load.
    """

    def get_context_data(self, **kwargs):
        from context.models.base import BaseModel

        ctx = super().get_context_data(**kwargs)
        obj = self.object
        if isinstance(obj, BaseModel) and hasattr(obj, "history"):
            ctx["history_available"] = True
            ctx["history_url"] = reverse(
                "history:partial",
                kwargs={
                    "app_label": obj._meta.app_label,
                    "model": obj._meta.model_name,
                    "pk": obj.pk,
                },
            )
        else:
            ctx["history_available"] = False
        return ctx


class LifecycleStepperMixin:
    """Build the stepper context for an entity on the standardised engine.

    For a DetailView whose object runs a ``core.lifecycle`` Lifecycle (i.e.
    ``get_lifecycle()`` is not ``None``). Produces ``lc_steps`` (every step in
    declaration order, marked done / current / future and flagged actionable
    when it is the target of a transition available to the user) plus the data
    the ``includes/lifecycle_stepper.html`` partial needs. Transitions post to
    the shared ``workflow:transition`` endpoint by default; a view whose bespoke
    transition endpoint carries extra side effects (required-fields gating,
    audit rows, recalculations) sets ``lifecycle_transition_url_name``.
    """

    lifecycle_transition_url_name = None

    def get_lifecycle_transition_url(self, obj):
        from django.urls import reverse

        if self.lifecycle_transition_url_name:
            return reverse(self.lifecycle_transition_url_name, kwargs={"pk": obj.pk})
        return reverse(
            "workflow:transition",
            kwargs={
                "app_label": obj._meta.app_label,
                "model": obj._meta.model_name,
                "pk": obj.pk,
            },
        )

    def get_context_data(self, **kwargs):
        from core.lifecycle import StepKind

        ctx = super().get_context_data(**kwargs)
        obj = self.object
        lifecycle = obj.get_lifecycle() if hasattr(obj, "get_lifecycle") else None
        if lifecycle is None:
            return ctx

        from core.lifecycle import ANY

        current = obj.workflow_state or lifecycle.initial_step.code
        # Graceful degradation : a row left on a step code that no longer exists
        # in the lifecycle (e.g. a stale value from before a lifecycle rebuild)
        # must not crash the detail page. Treat it as "off the lifecycle" : no
        # current step (all steps render future) and no available transitions.
        if not lifecycle.has_step(current):
            available = ()
        else:
            available = obj.available_transitions(user=self.request.user)
        target_to_label = {t.target: t.label for t in available}
        target_to_requires_comment = {t.target: t.requires_comment for t in available}
        # Explicit step-to-step edges (a wildcard "from any state" is not a flow
        # edge): the inter-step arrow is drawn only where a real transition links
        # two consecutive steps - so the arrows reflect the schema, not the
        # declaration order.
        edges = {(t.source, t.target) for t in lifecycle.transitions if t.source != ANY}

        # The main flow (Draft + intermediate steps) is drawn as a connected
        # line; the Archived exit(s) are detached (an exit is reachable from any
        # state, not the n-th step on the line).
        main_steps = [s for s in lifecycle.steps if s.kind != StepKind.ARCHIVED]
        exit_steps = [s for s in lifecycle.steps if s.kind == StepKind.ARCHIVED]
        main_codes = [s.code for s in main_steps]
        current_idx = main_codes.index(current) if current in main_codes else None

        def describe(step, state):
            return {
                "value": step.code,
                "label": step.label,
                "tone": step.tone,
                "state": state,
                "actionable": step.code in target_to_label,
                "action_label": target_to_label.get(step.code, step.label),
                "requires_comment": bool(target_to_requires_comment.get(step.code, False)),
            }

        # Branch detection : when a single intermediate step forwards (to a
        # later intermediate) into two or more intermediate successors, those
        # successors form a terminal branch and share one stage number with a /
        # b / c suffixes (e.g. compliant=4a, non_compliant=4b). All other
        # intermediates get a plain sequential number.
        inter_codes = [s.code for s in lifecycle.steps if s.kind == StepKind.INTERMEDIATE]
        inter_pos = {code: i for i, code in enumerate(inter_codes)}
        forward_targets: dict[str, list[str]] = {code: [] for code in inter_codes}
        for src, tgt in edges:
            # A forward edge between two intermediates : target sits later.
            if (
                src in inter_pos
                and tgt in inter_pos
                and inter_pos[tgt] > inter_pos[src]
            ):
                forward_targets[src].append(tgt)
        branch_groups: dict[str, int] = {}  # code -> 0-based index within its branch
        for src in inter_codes:
            tgts = sorted(forward_targets[src], key=lambda c: inter_pos[c])
            if len(tgts) >= 2:
                for idx, tgt in enumerate(tgts):
                    branch_groups[tgt] = idx

        steps = []
        stage_number = 0
        for i, step in enumerate(main_steps):
            if current_idx is None:
                state = "future"
            elif i < current_idx:
                state = "done"
            elif i == current_idx:
                state = "current"
            else:
                state = "future"
            node = describe(step, state)
            node["flow_from_prev"] = i > 0 and (main_steps[i - 1].code, step.code) in edges
            # Number only the operational (intermediate) stages; the Draft entry
            # and the Archived exit stay unnumbered bookends. Branch members
            # share the same number, distinguished by an a / b / c suffix.
            if step.kind == StepKind.INTERMEDIATE:
                if step.code in branch_groups:
                    branch_idx = branch_groups[step.code]
                    if branch_idx == 0:
                        stage_number += 1
                    node["number"] = f"{stage_number}{chr(ord('a') + branch_idx)}"
                else:
                    stage_number += 1
                    node["number"] = stage_number
            steps.append(node)

        exits = [
            describe(step, "current" if step.code == current else "future")
            for step in exit_steps
        ]

        ctx.update({
            "lc_enabled": True,
            "lc_layout": lifecycle.layout,
            "lc_steps": steps,
            "lc_exits": exits,
            "lc_current": current,
            "lc_current_label": obj.lifecycle_label,
            "lc_entity_label": str(obj._meta.verbose_name),
            "lc_container_id": f"lifecycle-stepper-{obj.pk}",
            "lc_transition_url": self.get_lifecycle_transition_url(obj),
        })
        if lifecycle.layout in ("cycle", "graph"):
            import json

            # Position of every intermediate step on the spine. A transition
            # between two intermediates is a LOOP back-edge when its target sits
            # earlier than (or level with) its source, and a forward edge
            # otherwise. The lifecycle may carry several loops (e.g. each branch
            # outcome looping back to an earlier step) - all of them are drawn.
            inter = [s.code for s in lifecycle.steps if s.kind == StepKind.INTERMEDIATE]
            pos = {code: i for i, code in enumerate(inter)}
            # A single representative loop (longest span) kept for the legacy
            # cycle layout + as a convenience for any consumer of lc_loop_*.
            loop_from = loop_to = None
            best = -1
            for t in lifecycle.transitions:
                if t.source in pos and t.target in pos and pos[t.target] < pos[t.source]:
                    span = pos[t.source] - pos[t.target]
                    if span > best:
                        best, loop_from, loop_to = span, t.source, t.target
            ctx["lc_loop_from"] = loop_from
            ctx["lc_loop_to"] = loop_to

            # ---- Schema-driven directed-graph payload (dagre+D3 renderer) ----
            # Nodes = every step (draft + intermediates + archived). Edges =
            # every transition; a wildcard source (ANY) becomes a single
            # "from-any" edge into its target (the archive exit). The diagram is
            # entirely derived here, so editing assets/lifecycles.py regenerates
            # it with no template change.
            state_by_code = {}
            for node in steps:
                state_by_code[node["value"]] = node["state"]
            for node in exits:
                state_by_code[node["value"]] = node["state"]

            kind_by_code = {s.code: s.kind.value for s in lifecycle.steps}

            graph_nodes = []
            for s in lifecycle.steps:
                code = s.code
                graph_nodes.append({
                    "id": code,
                    "label": str(s.label),
                    "tone": s.tone,
                    "kind": kind_by_code[code],          # draft|intermediate|archived
                    "state": state_by_code.get(code, "future"),
                    "actionable": code in target_to_label,
                    "action_label": str(target_to_label.get(code, s.label)),
                    "requires_comment": bool(target_to_requires_comment.get(code, False)),
                })

            graph_edges = []
            for t in lifecycle.transitions:
                if t.source == ANY:
                    kind = "exit"                         # any -> archived
                    source = ANY
                elif t.source == "archived":
                    kind = "restore"                      # archived -> draft
                    source = t.source
                elif (
                    t.source in pos
                    and t.target in pos
                    and pos[t.target] <= pos[t.source]
                ):
                    # Any back-edge among the intermediates is a loop. There may
                    # be several (e.g. each terminal branch outcome loops back to
                    # an earlier step) - they are all classified and drawn.
                    kind = "loop"
                    source = t.source
                else:
                    # Forward edge along the spine, including the divergence into
                    # a terminal branch (one source -> several later targets).
                    kind = "forward"
                    source = t.source
                graph_edges.append({
                    "source": source,
                    "target": t.target,
                    "kind": kind,
                    "label": str(t.label),
                })

            ctx["lc_layout"] = "graph"   # route the template to the new branch
            ctx["lc_graph_nodes"] = json.dumps(graph_nodes)
            ctx["lc_graph_edges"] = json.dumps(graph_edges)
        return ctx


class ScopeFilterMixin:
    """Filter queryset by the user's allowed scopes (UI views).

    Works for:
    - Views with ``scope_parent_lookup`` attribute → filter via parent FK path
    - ScopedModel subclasses (have a ``scopes`` M2M) → filter on scopes__id
    - Scope model itself → filter on id
    """

    scope_parent_lookup = None

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user

        if user.is_superuser:
            return qs

        scope_ids = user.get_allowed_scope_ids()
        if scope_ids is None:
            return qs

        model = qs.model
        if model is Scope or (hasattr(model, "_meta") and model._meta.label == "context.Scope"):
            return qs.filter(id__in=scope_ids)
        parent_lookup = getattr(self, "scope_parent_lookup", None)
        if parent_lookup:
            return qs.filter(**{f"{parent_lookup}__id__in": scope_ids}).distinct()
        if any(f.name == "scopes" for f in model._meta.many_to_many):
            return qs.filter(scopes__id__in=scope_ids).distinct()
        return qs
