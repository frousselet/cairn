import django_filters

from risks.models import (
    BaselineGap,
    EbiosWorkshopProgress,
    FearedEvent,
    SecurityBaseline,
    StudyFramework,
)


class StudyFrameworkFilter(django_filters.FilterSet):
    assessment = django_filters.UUIDFilter(field_name="assessment_id")

    class Meta:
        model = StudyFramework
        fields = {
            "status": ["exact"],
        }


class EbiosWorkshopProgressFilter(django_filters.FilterSet):
    assessment = django_filters.UUIDFilter(field_name="assessment_id")

    class Meta:
        model = EbiosWorkshopProgress
        fields = {
            "workshop_number": ["exact"],
            "iteration_type": ["exact"],
            "iteration_number": ["exact"],
            "status": ["exact"],
        }


class SecurityBaselineFilter(django_filters.FilterSet):
    assessment = django_filters.UUIDFilter(field_name="assessment_id")

    class Meta:
        model = SecurityBaseline
        fields = {
            "status": ["exact"],
            "is_approved": ["exact"],
        }


class FearedEventFilter(django_filters.FilterSet):
    baseline = django_filters.UUIDFilter(field_name="baseline_id")
    essential_asset = django_filters.UUIDFilter(field_name="essential_asset_id")

    class Meta:
        model = FearedEvent
        fields = {
            "dic_criterion": ["exact"],
            "gravity_level": ["exact", "gte", "lte"],
        }


class BaselineGapFilter(django_filters.FilterSet):
    baseline = django_filters.UUIDFilter(field_name="baseline_id")
    linked_requirement = django_filters.UUIDFilter(field_name="linked_requirement_id")

    class Meta:
        model = BaselineGap
        fields = {
            "severity": ["exact"],
            "status": ["exact"],
        }
