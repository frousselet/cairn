from django.db.models.signals import post_save
from django.dispatch import receiver

from risks.constants import (
    EBIOS_WORKSHOP_COUNT,
    EbiosIterationType,
    EbiosWorkshopStatus,
    Methodology,
)


@receiver(post_save, sender="risks.RiskAssessment")
def bootstrap_ebios_artifacts(sender, instance, created, **kwargs):
    """Create the EBIOS RM scaffolding the first time an assessment is saved as ebios_rm.

    Creates one StudyFramework, one SecurityBaseline and six EbiosWorkshopProgress
    rows (W0 to W5, strategic cycle, iteration 1). Idempotent: subsequent saves
    or switching back to ebios_rm after an ISO 27005 phase will not duplicate rows.
    """
    if instance.methodology != Methodology.EBIOS_RM:
        return

    from risks.models import (
        EbiosSummary,
        EbiosWorkshopProgress,
        SecurityBaseline,
        StudyFramework,
    )

    StudyFramework.objects.get_or_create(
        assessment=instance,
        defaults={"created_by": instance.created_by},
    )
    SecurityBaseline.objects.get_or_create(
        assessment=instance,
        defaults={"created_by": instance.created_by},
    )
    EbiosSummary.objects.get_or_create(
        assessment=instance,
        defaults={"created_by": instance.created_by},
    )
    for workshop_number in range(EBIOS_WORKSHOP_COUNT):
        EbiosWorkshopProgress.objects.get_or_create(
            assessment=instance,
            workshop_number=workshop_number,
            iteration_type=EbiosIterationType.STRATEGIC,
            iteration_number=1,
            defaults={
                "status": EbiosWorkshopStatus.NOT_STARTED,
                "created_by": instance.created_by,
            },
        )
