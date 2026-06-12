"""Shared compliance scoring.

Single source of truth for the framework compliance percentages shown on
the dashboard, pushed by the dashboard WebSocket refresh and exposed by
the predefined indicators. The score of a framework is the proportion of
its applicable requirements whose latest assessment result is compliant
(with a fallback to the latest expressed result when the most recent one
is not evaluated yet).
"""

from django.db.models import Count, Q

from compliance.constants import ComplianceStatus as CS

NOT_EVALUATED = {CS.NOT_ASSESSED, CS.EVALUATED}
COMPLIANT_STATUSES = {CS.COMPLIANT, CS.STRENGTH}
PARTIAL_STATUSES = {
    CS.MINOR_NON_CONFORMITY, CS.OBSERVATION,
    CS.IMPROVEMENT_OPPORTUNITY,
}


def annotate_compliance_segments(frameworks):
    """Compute compliance segments for each framework, in place.

    Sets ``seg_compliant`` / ``seg_partial`` / ``seg_non_compliant`` /
    ``seg_evaluated`` / ``seg_not_assessed`` (percentages of applicable
    requirements) and ``computed_compliance`` (the compliant proportion)
    on every framework of *frameworks*. Uses the ``req_count`` annotation
    when present, otherwise counts applicable requirements.

    Returns *frameworks* for convenience.
    """
    from compliance.models.assessment import AssessmentResult

    for fw in frameworks:
        rc = getattr(fw, "req_count", None)
        if rc is None:
            rc = fw.requirements.filter(is_applicable=True).count()
            fw.req_count = rc
        if not rc:
            fw.seg_compliant = fw.seg_partial = fw.seg_non_compliant = 0
            fw.seg_evaluated = fw.seg_not_assessed = 0
            fw.computed_compliance = 0
            continue

        req_ids = set(
            fw.requirements.filter(is_applicable=True).values_list("pk", flat=True)
        )
        all_results = (
            AssessmentResult.objects.filter(
                assessment__frameworks=fw,
                requirement_id__in=req_ids,
            )
            .select_related("assessment")
            .order_by("-assessment__assessment_end_date", "-assessment__created_at")
        )

        latest_map = {}    # req_id -> (status, level)
        fallback_map = {}  # req_id -> (status, level)
        for r in all_results:
            rid = r.requirement_id
            if rid not in latest_map:
                latest_map[rid] = (r.compliance_status, r.compliance_level)
            if rid not in fallback_map and r.compliance_status not in NOT_EVALUATED:
                fallback_map[rid] = (r.compliance_status, r.compliance_level)

        counts = {"compliant": 0, "partial": 0, "non_compliant": 0, "evaluated": 0, "not_assessed": 0}
        for rid in req_ids:
            latest = latest_map.get(rid)
            if latest is None:
                counts["not_assessed"] += 1
                continue
            status, level = latest
            if status in NOT_EVALUATED:
                fb = fallback_map.get(rid)
                if fb:
                    status, level = fb
                else:
                    status, level = CS.NOT_ASSESSED, 0

            if status == CS.NOT_APPLICABLE:
                counts["compliant"] += 1
            elif status in COMPLIANT_STATUSES:
                counts["compliant"] += 1
            elif status in PARTIAL_STATUSES:
                counts["partial"] += 1
            elif status == CS.MAJOR_NON_CONFORMITY:
                counts["non_compliant"] += 1
            elif status == CS.EVALUATED:
                counts["evaluated"] += 1
            else:
                counts["not_assessed"] += 1

        fw.seg_compliant = round(counts["compliant"] * 100 / rc)
        fw.seg_partial = round(counts["partial"] * 100 / rc)
        fw.seg_non_compliant = round(counts["non_compliant"] * 100 / rc)
        fw.seg_evaluated = round(counts["evaluated"] * 100 / rc)
        fw.seg_not_assessed = round(counts["not_assessed"] * 100 / rc)
        # Compliance % = proportion of compliant requirements (matches green segment)
        fw.computed_compliance = fw.seg_compliant

    return frameworks


def active_frameworks_for_scoring(queryset=None):
    """Active, reportable frameworks whose score feeds the overall average."""
    from core.workflow import reportable

    from compliance.models import Framework

    qs = queryset if queryset is not None else Framework.objects.all()
    return reportable(qs.filter(status="active")).annotate(
        req_count=Count("requirements", filter=Q(requirements__is_applicable=True)),
    )


def overall_compliance_rate(queryset=None, precision=0):
    """Average computed compliance of the active reportable frameworks.

    *queryset* optionally restricts the frameworks considered (e.g. user
    scoping); it is filtered to active reportable ones here. Returns a
    number rounded to *precision* (an int when precision is 0).
    """
    frameworks = annotate_compliance_segments(
        list(active_frameworks_for_scoring(queryset))
    )
    if not frameworks:
        return 0
    avg = sum(fw.computed_compliance for fw in frameworks) / len(frameworks)
    return round(avg, precision) if precision else round(avg)
