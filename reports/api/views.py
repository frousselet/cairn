import base64
import logging

from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils.translation import gettext as _
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from accounts.api.permissions import ModulePermission
from compliance.constants import ActionPlanStatus, AssessmentStatus
from compliance.models import ComplianceActionPlan, ComplianceAssessment, Framework
from reports.constants import ManagementReviewStatus, ReportStatus, ReportType
from reports.generators import generate_audit_report_pdf, generate_soa_pdf
from reports.management_review import (
    gather_management_review_data,
    generate_management_review_docx,
    generate_management_review_pptx,
)
from reports.management_review_views import _serialize_snapshot
from reports.models import (
    IsmsChange,
    ManagementReview,
    ManagementReviewDecision,
    Report,
)
from .serializers import (
    AuditReportCreateSerializer,
    IsmsChangeSerializer,
    ManagementReviewCreateSerializer,
    ManagementReviewDecisionSerializer,
    ManagementReviewDetailSerializer,
    ManagementReviewSerializer,
    ReportSerializer,
    SoaReportCreateSerializer,
    TransitionActionSerializer,
)


class ReportViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Report.objects.all()
    serializer_class = ReportSerializer
    permission_classes = [ModulePermission]
    permission_module = "reports"
    permission_feature = "report"
    custom_action_map = {
        "generate_soa": "create",
        "generate_audit_report": "create",
        "generate_management_review": "create",
    }

    @action(detail=False, methods=["post"], url_path="generate-soa")
    def generate_soa(self, request):
        ser = SoaReportCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        frameworks = Framework.objects.filter(id__in=ser.validated_data["framework_ids"])
        if not frameworks.exists():
            return Response(
                {"detail": _("No frameworks found for given IDs.")},
                status=status.HTTP_400_BAD_REQUEST,
            )

        fw_names = ", ".join(fw.short_name or fw.name for fw in frameworks)
        report_name = _("Statement of Applicability") + f" - {fw_names}"

        try:
            filename, pdf_bytes = generate_soa_pdf(frameworks, request.user)
            report = Report.objects.create(
                report_type=ReportType.SOA,
                name=report_name,
                status=ReportStatus.COMPLETED,
                created_by=request.user,
                file_content=pdf_bytes,
                file_name=filename,
            )
            report.frameworks.set(frameworks)
        except Exception:
            logging.getLogger(__name__).exception("SoA PDF generation failed")
            report = Report.objects.create(
                report_type=ReportType.SOA,
                name=report_name,
                status=ReportStatus.FAILED,
                created_by=request.user,
            )

        return Response(ReportSerializer(report).data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["post"], url_path="generate-audit-report")
    def generate_audit_report(self, request):
        ser = AuditReportCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        try:
            assessment = ComplianceAssessment.objects.get(
                id=ser.validated_data["assessment_id"],
            )
        except ComplianceAssessment.DoesNotExist:
            return Response(
                {"detail": _("Assessment not found.")},
                status=status.HTTP_404_NOT_FOUND,
            )

        if assessment.status not in (AssessmentStatus.COMPLETED, AssessmentStatus.CLOSED):
            return Response(
                {"detail": _("The assessment must be completed or closed to generate a report.")},
                status=status.HTTP_400_BAD_REQUEST,
            )

        report_name = _("Audit report") + f" - {assessment.reference} : {assessment.name}"

        try:
            filename, pdf_bytes = generate_audit_report_pdf(assessment, request.user)
            report = Report.objects.create(
                report_type=ReportType.AUDIT_REPORT,
                name=report_name,
                status=ReportStatus.COMPLETED,
                created_by=request.user,
                assessment=assessment,
                file_content=pdf_bytes,
                file_name=filename,
            )
            report.frameworks.set(assessment.frameworks.all())
        except Exception:
            logging.getLogger(__name__).exception("Audit report PDF generation failed")
            report = Report.objects.create(
                report_type=ReportType.AUDIT_REPORT,
                name=report_name,
                status=ReportStatus.FAILED,
                created_by=request.user,
                assessment=assessment,
            )

        return Response(ReportSerializer(report).data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["post"], url_path="generate-management-review")
    def generate_management_review(self, request):
        ser = ManagementReviewCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        fmt = ser.validated_data["format"]
        scope_ids = ser.validated_data.get("scope_ids") or None
        period_start = ser.validated_data.get("period_start")
        period_end = ser.validated_data.get("period_end")

        if fmt == "pptx":
            report_type = ReportType.MANAGEMENT_REVIEW_PPTX
            generator = generate_management_review_pptx
            label = _("Presentation")
        else:
            report_type = ReportType.MANAGEMENT_REVIEW_DOCX
            generator = generate_management_review_docx
            label = _("Minutes")

        report_name = _("Management review") + f" - {label}"

        try:
            filename, file_bytes = generator(
                request.user, scope_ids,
                period_start=period_start, period_end=period_end,
            )
            report = Report.objects.create(
                report_type=report_type,
                name=report_name,
                status=ReportStatus.COMPLETED,
                created_by=request.user,
                file_content=file_bytes,
                file_name=filename,
            )
        except Exception:
            logging.getLogger(__name__).exception(
                "Management review %s generation failed", fmt.upper()
            )
            report = Report.objects.create(
                report_type=report_type,
                name=report_name,
                status=ReportStatus.FAILED,
                created_by=request.user,
            )

        return Response(ReportSerializer(report).data, status=status.HTTP_201_CREATED)


# =====================================================================
# Persistent management review API
# =====================================================================


class ManagementReviewViewSet(viewsets.ModelViewSet):
    queryset = ManagementReview.objects.all().select_related("facilitator", "approver")
    serializer_class = ManagementReviewSerializer
    permission_classes = [ModulePermission]
    permission_module = "reports"
    permission_feature = "management_review"
    custom_action_map = {
        "transition": "update",
        "export": "read",
        "decisions": "read",
        "isms_changes": "read",
    }

    def get_serializer_class(self):
        if self.action == "retrieve":
            return ManagementReviewDetailSerializer
        return ManagementReviewSerializer

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(detail=True, methods=["post"], url_path="transition")
    def transition(self, request, pk=None):
        review = self.get_object()
        ser = TransitionActionSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        target = ser.validated_data["target_status"]
        comment = ser.validated_data.get("comment", "")

        if (
            target == ManagementReviewStatus.CLOSED
            and not request.user.has_perm("reports.management_review.approve")
        ):
            return Response(
                {"detail": _("Closure requires approve permission.")},
                status=status.HTTP_403_FORBIDDEN,
            )

        try:
            review.transition_to(target, request.user, comment=comment)
        except ValueError as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if review.status == ManagementReviewStatus.CLOSED:
            try:
                scope_ids = list(review.scopes.values_list("id", flat=True))
                data = gather_management_review_data(
                    request.user,
                    scope_ids=scope_ids,
                    period_start=review.period_start,
                    period_end=review.period_end,
                )
                review.take_snapshot(_serialize_snapshot(data))
            except Exception:
                logging.getLogger(__name__).exception("Snapshot generation failed")

        return Response(
            ManagementReviewSerializer(review).data,
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["get"], url_path="export")
    def export(self, request, pk=None):
        review = self.get_object()
        fmt = request.query_params.get("fmt", "docx")
        scope_ids = list(review.scopes.values_list("id", flat=True))

        try:
            if fmt == "pptx":
                filename, data = generate_management_review_pptx(
                    request.user,
                    scope_ids=scope_ids,
                    period_start=review.period_start,
                    period_end=review.period_end,
                    review=review,
                )
                ctype = ("application/vnd.openxmlformats-officedocument"
                         ".presentationml.presentation")
            elif fmt == "docx":
                filename, data = generate_management_review_docx(
                    request.user,
                    scope_ids=scope_ids,
                    period_start=review.period_start,
                    period_end=review.period_end,
                    review=review,
                )
                ctype = ("application/vnd.openxmlformats-officedocument"
                         ".wordprocessingml.document")
            else:
                return Response(
                    {"detail": _("Unsupported format.")},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        except Exception:
            logging.getLogger(__name__).exception("Export failed")
            return Response(
                {"detail": _("Export generation failed.")},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        resp = HttpResponse(data, content_type=ctype)
        resp["Content-Disposition"] = f'attachment; filename="{filename}"'
        return resp

    @action(detail=True, methods=["get", "post"], url_path="decisions")
    def decisions(self, request, pk=None):
        review = self.get_object()
        if request.method == "GET":
            qs = review.decisions.select_related("owner").all()
            return Response(
                ManagementReviewDecisionSerializer(qs, many=True).data,
            )
        ser = ManagementReviewDecisionSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        ser.save(review=review)
        return Response(ser.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["get", "post"], url_path="isms-changes")
    def isms_changes(self, request, pk=None):
        review = self.get_object()
        if request.method == "GET":
            qs = review.isms_changes.select_related("owner").all()
            return Response(IsmsChangeSerializer(qs, many=True).data)
        ser = IsmsChangeSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        ser.save(review=review)
        return Response(ser.data, status=status.HTTP_201_CREATED)


class ManagementReviewDecisionViewSet(viewsets.ModelViewSet):
    queryset = ManagementReviewDecision.objects.all().select_related("owner", "review")
    serializer_class = ManagementReviewDecisionSerializer
    permission_classes = [ModulePermission]
    permission_module = "reports"
    permission_feature = "management_review"
    custom_action_map = {"promote": "update"}

    @action(detail=True, methods=["post"], url_path="promote")
    def promote(self, request, pk=None):
        """Promote a decision to a ComplianceActionPlan."""
        decision = self.get_object()
        if not request.user.has_perm("compliance.action_plan.create"):
            return Response(
                {"detail": _("Missing action_plan.create permission.")},
                status=status.HTTP_403_FORBIDDEN,
            )
        if decision.linked_action_plan_id:
            return Response(
                {"detail": _("Decision is already linked to an action plan.")},
                status=status.HTTP_400_BAD_REQUEST,
            )

        plan = ComplianceActionPlan.objects.create(
            name=decision.title,
            description=decision.description,
            gap_description=decision.description,
            remediation_plan=decision.rationale or decision.description,
            priority=decision.priority,
            owner=decision.owner or request.user,
            target_date=decision.due_date,
            status=ActionPlanStatus.NEW,
            originating_review=decision.review,
            created_by=request.user,
        )
        plan.scopes.set(decision.review.scopes.all())
        decision.linked_action_plan = plan
        if decision.status == "pending":
            decision.status = "in_progress"
        decision.save(update_fields=["linked_action_plan", "status", "updated_at"])

        return Response(
            ManagementReviewDecisionSerializer(decision).data,
            status=status.HTTP_201_CREATED,
        )


class IsmsChangeViewSet(viewsets.ModelViewSet):
    queryset = IsmsChange.objects.all().select_related("owner", "review")
    serializer_class = IsmsChangeSerializer
    permission_classes = [ModulePermission]
    permission_module = "reports"
    permission_feature = "management_review"
