# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
from django.urls import reverse

from context.models import Scope
from core.scoping import filter_queryset_by_scopes


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


# Number of steps past which the lifecycle bar folds the completed ones.
LIFECYCLE_BAR_DENSE_FROM = 6


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
        from helpers.templatetags.workflow_tags import _TONE_CLASSES

        ctx = super().get_context_data(**kwargs)
        # A form view shared by the creation and the edit of a record (the
        # rows of an EBIOS RM workshop) has no record yet when it creates one.
        obj = getattr(self, "object", None)
        lifecycle = obj.get_lifecycle() if obj is not None and hasattr(obj, "get_lifecycle") else None
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
        # (source, target) pairs the caller may perform right now : an edge is
        # "possible" iff it is one of these (drawn solid; the rest dashed / muted).
        available_pairs = {(t.source, t.target) for t in available}
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
            confirm = step.confirm_trigger
            return {
                "value": step.code,
                "label": step.label,
                "tone": step.tone,
                # Same dot-pill class as {% workflow_badge %}, so the current
                # step of the bar reads as the status badge it is.
                "badge_class": _TONE_CLASSES.get(step.tone, "secondary"),
                "state": state,
                "actionable": step.code in target_to_label,
                "action_label": target_to_label.get(step.code, step.label),
                "requires_comment": bool(target_to_requires_comment.get(step.code, False)),
                # A "confirm" trigger on the target step asks "Are you sure?"
                # before the move (the message is optional, blank -> default).
                "confirm": confirm is not None,
                "confirm_message": str(confirm.config.get("message", "")) if confirm else "",
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

        # Path-aware reading of the main flow, for the compact lifecycle bar.
        # ``state`` above follows the declaration order, which reads a branch
        # that was never taken as "done" (an accepted risk would show its
        # treatment steps ticked). ``path`` follows the schema instead : a step
        # is "done" when the current step is reachable from it along forward
        # transitions, "ahead" when it is reachable from the current step, and
        # "off" when it sits on another branch. The bar hides the "off" steps
        # unless the user can move to them; the full graph still shows them.
        flow_index = {code: i for i, code in enumerate(main_codes)}
        forward: dict[str, set[str]] = {code: set() for code in main_codes}
        backward: dict[str, set[str]] = {code: set() for code in main_codes}
        for src, tgt in edges:
            if src in flow_index and tgt in flow_index and flow_index[tgt] > flow_index[src]:
                forward[src].add(tgt)
                backward[tgt].add(src)

        def reachable(start, graph):
            seen, stack = set(), [start]
            while stack:
                for nxt in graph[stack.pop()]:
                    if nxt not in seen:
                        seen.add(nxt)
                        stack.append(nxt)
            return seen

        on_flow = current in flow_index
        ahead = reachable(current, forward) if on_flow else set(main_codes)
        behind = reachable(current, backward) if on_flow else set()
        for node in steps:
            code = node["value"]
            if code == current:
                node["path"] = "current"
            elif code in behind:
                node["path"] = "done"
            elif code in ahead:
                node["path"] = "ahead"
            else:
                node["path"] = "off"
            # A move to a step that is not ahead of the current one is a way
            # back (rework, refusal, restore), whatever branch it sits on.
            node["direction"] = "forward" if node["path"] == "ahead" else "back"
            node["on_bar"] = node["path"] != "off" or node["actionable"]
        for node in exits:
            node["path"] = "current" if node["state"] == "current" else "ahead"
            # Leaving the flow is a quiet action, never the highlighted next step.
            node["direction"] = "exit"
            node["on_bar"] = node["path"] == "current" or node["actionable"]
        bar_steps = [node for node in steps if node["on_bar"]]
        bar_exits = [node for node in exits if node["on_bar"]]

        ctx.update({
            "lc_enabled": True,
            "lc_layout": lifecycle.layout,
            "lc_steps": steps,
            "lc_exits": exits,
            "lc_bar_steps": bar_steps,
            "lc_bar_exits": bar_exits,
            # Past this many steps the bar folds the completed ones to a tick,
            # so a long lifecycle still holds on one line.
            "lc_bar_dense": len(bar_steps) > LIFECYCLE_BAR_DENSE_FROM,
            "lc_current": current,
            "lc_current_label": obj.lifecycle_label,
            "lc_entity_label": str(obj._meta.verbose_name),
            "lc_container_id": f"lifecycle-stepper-{obj.pk}",
            "lc_transition_url": self.get_lifecycle_transition_url(obj),
        })
        # The graph payload is always built : the bar is the default rendering
        # and the full directed graph opens on demand, whatever the layout the
        # lifecycle declares.
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
            confirm = s.confirm_trigger
            graph_nodes.append({
                "id": code,
                "label": str(s.label),
                "tone": s.tone,
                "kind": kind_by_code[code],          # draft|intermediate|archived
                "state": state_by_code.get(code, "future"),
                "actionable": code in target_to_label,
                "action_label": str(target_to_label.get(code, s.label)),
                "requires_comment": bool(target_to_requires_comment.get(code, False)),
                # "confirm" trigger : ask before moving INTO this step.
                "confirm": confirm is not None,
                "confirm_message": str(confirm.config.get("message", "")) if confirm else "",
            })

        # Edge classification is keyed off the full main-flow order (Draft +
        # intermediates) and the Archived step kind, NOT the intermediates
        # alone : a send-back to Draft (pending -> draft) is a loop, and an
        # archive edge from a specific step (validated -> archived) is an
        # exit - both used to be mis-read as forward, which turned the source
        # into a spurious two-target branch and overlapped the nodes.
        archived_codes = {s.code for s in lifecycle.steps if s.kind == StepKind.ARCHIVED}
        flow_pos = {code: i for i, code in enumerate(main_codes)}
        graph_edges = []
        for t in lifecycle.transitions:
            if t.target in archived_codes:
                kind = "exit"                         # (any or a step) -> archived
                source = t.source
            elif t.source in archived_codes:
                kind = "restore"                      # archived -> earlier step
                source = t.source
            elif (
                t.source in flow_pos
                and t.target in flow_pos
                and flow_pos[t.target] <= flow_pos[t.source]
            ):
                # A back-edge along the main flow (including the send-back to
                # Draft) is a loop, never a forward branch. Several may exist
                # (each terminal branch outcome looping back) - all are drawn.
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
                "available": (t.source, t.target) in available_pairs,
            })

        ctx["lc_layout"] = "graph"   # kept for consumers : the graph is always available
        from core.safe_json import dumps_for_script

        ctx["lc_graph_nodes"] = dumps_for_script(graph_nodes)
        ctx["lc_graph_edges"] = dumps_for_script(graph_edges)
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

        return filter_queryset_by_scopes(
            qs, scope_ids, explicit=getattr(self, "scope_parent_lookup", None)
        )
