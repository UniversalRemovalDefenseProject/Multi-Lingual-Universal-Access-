from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View
from django.views.generic import ListView

from intake.models import IntakeSubmission
from .forms import AssignForm, StaffNoteForm

User = get_user_model()

_UNASSIGNED = 'unassigned'


def _assignable_users():
    return User.objects.filter(groups__name='Case Manager', is_active=True).order_by('username')


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

    def _selected_assignee(self):
        """Returns a user pk (int), 'unassigned', or '' (no filter)."""
        raw = self.request.GET.get('assigned_to', '')
        if raw == _UNASSIGNED:
            return _UNASSIGNED
        if raw.isdigit():
            uid = int(raw)
            if _assignable_users().filter(pk=uid).exists():
                return uid
        return ''

    def get_queryset(self):
        queryset = super().get_queryset()
        status = self._selected_status()
        if status:
            queryset = queryset.filter(status=status)
        assignee = self._selected_assignee()
        if assignee == _UNASSIGNED:
            queryset = queryset.filter(assigned_to__isnull=True)
        elif assignee:
            queryset = queryset.filter(assigned_to_id=assignee)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['status_choices'] = IntakeSubmission.STATUS_CHOICES
        context['selected_status'] = self._selected_status()
        context['assignable_users'] = _assignable_users()
        context['selected_assignee'] = self._selected_assignee()
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
            'notes': submission.staff_notes.all(),
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
