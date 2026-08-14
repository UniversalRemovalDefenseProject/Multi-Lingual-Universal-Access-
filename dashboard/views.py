from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.http import urlencode
from django.views import View
from django.views.generic import ListView

from intake.models import IntakeSubmission
from .forms import AssignForm, StaffNoteForm

User = get_user_model()

_UNASSIGNED = 'unassigned'


def _assignable_users():
    return User.objects.filter(groups__name='Case Manager', is_active=True).order_by('username')


def _selected_status(request) -> str:
    # Only a known status key is ever used; anything else falls back to unfiltered
    # so the raw query parameter never reaches the queryset or the template.
    status = request.GET.get('status', '')
    return status if status in dict(IntakeSubmission.STATUS_CHOICES) else ''


def _selected_assignee(request):
    """Returns a user pk (int), 'unassigned', or '' (no filter)."""
    raw = request.GET.get('assigned_to', '')
    if raw == _UNASSIGNED:
        return _UNASSIGNED
    if raw.isdigit():
        uid = int(raw)
        if _assignable_users().filter(pk=uid).exists():
            return uid
    return ''


def _back_query(request):
    """Validated filter state as a query string, for links back to the queue."""
    params = {}
    status = _selected_status(request)
    if status:
        params['status'] = status
    assignee = _selected_assignee(request)
    # Explicit comparison: the 'unassigned' sentinel must survive, and truthiness
    # would be one refactor away from silently dropping it.
    if assignee != '':
        params['assigned_to'] = assignee
    return urlencode(params)


class CaseQueueView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    """Read-only queue of intake submissions, newest first."""

    permission_required = 'intake.access_dashboard'
    model = IntakeSubmission
    ordering = '-created_at'
    paginate_by = 25
    template_name = 'dashboard/queue.html'
    context_object_name = 'submissions'

    def get_queryset(self):
        # select_related: the assignee column reads submission.assigned_to per row.
        queryset = super().get_queryset().select_related('assigned_to')
        status = _selected_status(self.request)
        if status:
            queryset = queryset.filter(status=status)
        assignee = _selected_assignee(self.request)
        if assignee == _UNASSIGNED:
            queryset = queryset.filter(assigned_to__isnull=True)
        elif assignee:
            queryset = queryset.filter(assigned_to_id=assignee)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['status_choices'] = IntakeSubmission.STATUS_CHOICES
        context['selected_status'] = _selected_status(self.request)
        context['assignable_users'] = _assignable_users()
        context['selected_assignee'] = _selected_assignee(self.request)
        context['UNASSIGNED'] = _UNASSIGNED
        return context


class CaseDetailView(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_required = 'intake.access_dashboard'
    template_name = 'dashboard/detail.html'

    def _render(self, request, submission, assign_form, note_form):
        return render(request, self.template_name, {
            'submission': submission,
            'assign_form': assign_form,
            'note_form': note_form,
            'notes': submission.staff_notes.select_related('author'),
            'back_query': _back_query(request),
        })

    def get(self, request, pk):
        submission = get_object_or_404(IntakeSubmission, pk=pk)
        return self._render(
            request,
            submission,
            AssignForm(instance=submission, assignable_users=_assignable_users()),
            StaffNoteForm(),
        )

    def post(self, request, pk):
        submission = get_object_or_404(IntakeSubmission, pk=pk)
        assign_form = AssignForm(request.POST, instance=submission, assignable_users=_assignable_users())
        note_form = StaffNoteForm(request.POST)
        body = request.POST.get('body', '').strip()

        if assign_form.is_valid() and (not body or note_form.is_valid()):
            assign_form.save()
            if body:
                note = note_form.save(commit=False)
                note.intake = submission
                note.author = request.user
                note.save()
            messages.success(request, 'Changes saved.')
            return redirect('dashboard:detail', pk=pk)

        return self._render(request, submission, assign_form, note_form)
