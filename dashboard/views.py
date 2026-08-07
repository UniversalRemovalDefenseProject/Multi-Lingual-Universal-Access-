from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.views.generic import ListView

from intake.models import IntakeSubmission


class CaseQueueView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    """Read-only queue of intake submissions, newest first."""

    permission_required = 'intake.access_dashboard'
    model = IntakeSubmission
    ordering = '-created_at'
    paginate_by = 25
    template_name = 'dashboard/queue.html'
    context_object_name = 'submissions'

    def _selected_status(self) -> str:
        # Only a known status key is ever used; anything else falls back to unfiltered
        # so the raw query parameter never reaches the queryset or the template.
        status = self.request.GET.get('status', '')
        return status if status in dict(IntakeSubmission.STATUS_CHOICES) else ''

    def get_queryset(self):
        queryset = super().get_queryset()
        status = self._selected_status()
        return queryset.filter(status=status) if status else queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['status_choices'] = IntakeSubmission.STATUS_CHOICES
        context['selected_status'] = self._selected_status()
        return context
