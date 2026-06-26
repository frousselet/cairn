from django.http import HttpResponseRedirect
from django.urls import reverse
from django.utils import timezone

from context.models import Scope


class ApprovableUpdateMixin:
    """Reset approval status and increment version after a domain object is updated.

    Respects VersioningConfig: only triggers version bump and approval reset
    when a "major" field has changed. If approval is disabled for the model,
    the approval fields are left unchanged.
    """

    def _is_major_change(self, form):
        """Determine if the form changes include at least one major field."""
        from core.models import VersioningConfig

        model_class = self.object.__class__
        if not VersioningConfig.is_approval_enabled(model_class):
            return False
        major_fields = VersioningConfig.get_major_fields(model_class)
        if major_fields is None:
            # No config or empty major_fields list → all changes are major
            return True
        changed = set(form.changed_data)
        return bool(changed & major_fields)

    def form_valid(self, form):
        self.object = form.save(commit=False)
        if self._is_major_change(form):
            self.object.is_approved = False
            self.object.approved_by = None
            self.object.approved_at = None
            self.object.version = (self.object.version or 0) + 1
        self.object.save()
        form.save_m2m()
        return HttpResponseRedirect(self.get_success_url())


class ApprovalContextMixin:
    """Add approval context (can_approve, approve_url, approval_enabled) to detail views."""

    approval_module = None
    approval_feature = None
    approve_url_name = None

    def _get_approval_module(self):
        if self.approval_module:
            return self.approval_module
        return self.model._meta.app_label

    def _get_approval_feature(self):
        if self.approval_feature:
            return self.approval_feature
        return self.model._meta.model_name

    def get_context_data(self, **kwargs):
        from core.models import VersioningConfig

        ctx = super().get_context_data(**kwargs)

        # Check if approval is enabled for this model
        approval_enabled = VersioningConfig.is_approval_enabled(self.model)
        ctx["approval_enabled"] = approval_enabled

        if not approval_enabled:
            ctx["can_approve"] = False
            return ctx

        user = self.request.user
        module = self._get_approval_module()
        feature = self._get_approval_feature()
        codename = f"{module}.{feature}.approve"

        can_approve = False
        if user.is_superuser:
            can_approve = True
        elif user.has_perm(codename):
            # Check scope access via M2M scopes
            obj = self.object
            if hasattr(obj, "scopes") and hasattr(obj.scopes, "values_list"):
                allowed = user.get_allowed_scope_ids()
                if allowed is None:
                    can_approve = True
                else:
                    obj_scope_ids = set(obj.scopes.values_list("id", flat=True))
                    if obj_scope_ids & set(allowed):
                        can_approve = True
            else:
                can_approve = True

        ctx["can_approve"] = can_approve
        if self.approve_url_name:
            ctx["approve_url"] = reverse(self.approve_url_name, kwargs={"pk": self.object.pk})
        return ctx


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


class WorkflowStepperMixin:
    """Build the generic lifecycle stepper context for a detail view.

    Reads the object's workflow definition (states in declaration order, the
    caller's allowed transitions, branch states like cancelled / archived) and
    produces the context consumed by ``includes/workflow_stepper.html``.

    The transition is posted to the shared ``workflow:transition`` URL by
    default; views whose bespoke transition endpoint carries extra side effects
    (required-fields gating, recalculations) set
    ``workflow_transition_url_name`` or override
    :meth:`get_workflow_transition_url`.
    """

    workflow_transition_url_name = None
    # When the off-ramp (archive / cancel) action lives outside the stepper
    # (e.g. a dedicated button in the page-title bar), the branch state is shown
    # display-only - never a clickable pill - so the stepper stays a pure state
    # display and the action is triggered elsewhere.
    workflow_branch_action_external = False

    def get_workflow_transition_url(self, obj):
        if self.workflow_transition_url_name:
            return reverse(self.workflow_transition_url_name, kwargs={"pk": obj.pk})
        return reverse(
            "workflow:transition",
            kwargs={
                "app_label": obj._meta.app_label,
                "model": obj._meta.model_name,
                "pk": obj.pk,
            },
        )

    def get_context_data(self, **kwargs):
        from core.workflow import allowed_transitions

        ctx = super().get_context_data(**kwargs)
        obj = self.object
        if not hasattr(obj, "get_workflow"):
            return ctx
        workflow = obj.get_workflow()
        current = obj.workflow_state or workflow.initial_state.code
        user = self.request.user

        def has_perm(codename):
            return user.is_superuser or user.has_perm(codename)

        allowed = allowed_transitions(
            workflow, current,
            has_perm=has_perm, perm_namespace=obj.workflow_perm_namespace,
        ) if workflow.has_state(current) else ()

        main_states = [s for s in workflow.states if not s.branch]
        branch_state = next((s for s in workflow.states if s.branch), None)
        main_codes = [s.code for s in main_states]
        current_idx = main_codes.index(current) if current in main_codes else None
        on_branch = branch_state is not None and current == branch_state.code

        # Forward step: the allowed transition to the next main-flow state.
        next_transition = None
        if current_idx is not None and current_idx + 1 < len(main_codes):
            next_code = main_codes[current_idx + 1]
            next_transition = next(
                (t for t in allowed if t.target == next_code and not t.requires_comment),
                None,
            )

        steps = []
        for i, state in enumerate(main_states):
            if current_idx is None:
                step_state = "future"
            elif i < current_idx:
                step_state = "done"
            elif i == current_idx:
                step_state = "current"
            elif next_transition is not None and state.code == next_transition.target:
                step_state = "next"
            else:
                step_state = "future"
            steps.append({"value": state.code, "label": state.label, "state": step_state})

        # Backward move (refusal / rework): first allowed transition going back.
        refusal_transition = None
        if current_idx is not None:
            for t in allowed:
                if t.target in main_codes and main_codes.index(t.target) < current_idx:
                    refusal_transition = t
                    break

        branch_transition = None
        if branch_state is not None and not self.workflow_branch_action_external:
            branch_transition = next(
                (t for t in allowed if t.target == branch_state.code), None,
            )

        # When the off-ramp action lives outside the stepper (e.g. a title-bar
        # Archive button, ``workflow_branch_action_external``), the branch pill is
        # shown ONLY once the item is actually on the branch - otherwise it stays
        # hidden so the line has nothing dangling to click. For the standard case
        # (the branch is reached through the stepper) it is always shown as the
        # off-ramp: a static future pill, a clickable cancel when reachable now,
        # or the current state once on it.
        show_branch = branch_state is not None and (
            on_branch or not self.workflow_branch_action_external
        )

        ctx.update({
            "wf_enabled": True,
            "wf_steps": steps,
            "wf_container_id": f"workflow-stepper-{obj.pk}",
            "wf_entity_id": str(obj.pk),
            "wf_transition_url": self.get_workflow_transition_url(obj),
            "wf_next_status": next_transition.target if next_transition else None,
            "wf_cancelled": {
                "value": branch_state.code,
                "label": branch_state.label,
                "state": "current" if on_branch else "future",
            } if show_branch else None,
            "wf_can_cancel": branch_transition is not None,
            "wf_cancel_requires_comment": bool(
                branch_transition and branch_transition.requires_comment
            ),
            "wf_cancel_verb": branch_transition.verb if branch_transition else None,
            "wf_refusal": {
                "status": refusal_transition.target,
                "label": refusal_transition.verb,
            } if refusal_transition else None,
            "wf_can_refuse": refusal_transition is not None,
            "wf_refuse_requires_comment": bool(
                refusal_transition and refusal_transition.requires_comment
            ),
        })
        return ctx


class LifecycleStepperMixin:
    """Build the stepper context for an entity on the standardised engine.

    For a DetailView whose object runs a ``core.lifecycle`` Lifecycle (i.e.
    ``get_lifecycle()`` is not ``None``). Produces ``lc_steps`` (every step in
    declaration order, marked done / current / future and flagged actionable
    when it is the target of a transition available to the user) plus the data
    the ``includes/lifecycle_stepper.html`` partial needs. Transitions post to
    the shared ``workflow:transition`` endpoint (new-engine aware).
    """

    def get_context_data(self, **kwargs):
        from django.urls import reverse

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
            "lc_transition_url": reverse(
                "workflow:transition",
                kwargs={
                    "app_label": obj._meta.app_label,
                    "model": obj._meta.model_name,
                    "pk": obj.pk,
                },
            ),
        })
        if lifecycle.layout == "cycle":
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
