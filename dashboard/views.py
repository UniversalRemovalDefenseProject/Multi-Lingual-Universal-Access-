from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.http import urlencode
from django.views import View
from django.views.generic import ListView

from intake.models import IntakeSubmission
from .forms import AssignForm, StaffNoteForm

User = get_user_model()

_UNASSIGNED = 'unassigned'
_DETAINED_YES = 'yes'
_DETAINED_NO = 'no'
PAGE_SIZE = 25
# Applicant names and A-numbers are PII, so the query lives in the session and never in
# a URL, browser history, referrer header, or access log.
SEARCH_SESSION_KEY = 'dashboard_search'
MAX_SEARCH_LENGTH = 100


def _assignable_users():
    return User.objects.filter(groups__name='Case Manager', is_active=True).order_by('username')


def _validated_status_value(value) -> str:
    # The single membership check. Every status that reaches a queryset, a template, or
    # a URL passes through here, whether it arrived by GET or POST.
    return value if value in dict(IntakeSubmission.STATUS_CHOICES) else ''


def _validated_assignee_value(raw):
    """Returns a user pk (int), 'unassigned', or '' (no filter)."""
    if raw == _UNASSIGNED:
        return _UNASSIGNED
    if isinstance(raw, str) and raw.isdigit():
        uid = int(raw)
        if _assignable_users().filter(pk=uid).exists():
            return uid
    return ''


def _validated_detained_value(value) -> str:
    # Membership check only, same shape as _validated_status_value. A rejected
    # value falls back to '' (no filter) and is never echoed.
    return value if value in (_DETAINED_YES, _DETAINED_NO) else ''


def _validated_page(value) -> int:
    try:
        return max(int(value), 1)
    except (TypeError, ValueError):
        return 1


def _selected_status(request) -> str:
    return _validated_status_value(request.GET.get('status', ''))


def _selected_assignee(request):
    return _validated_assignee_value(request.GET.get('assigned_to', ''))


def _selected_detained(request) -> str:
    return _validated_detained_value(request.GET.get('detained', ''))


def _active_search(request) -> str:
    return request.session.get(SEARCH_SESSION_KEY, '')


def _queue_params(status, assignee, detained, page=1) -> dict:
    """Validated filter state as URL params. The single builder for every queue URL."""
    params = {}
    if status:
        params['status'] = status
    # Explicit comparison: the 'unassigned' sentinel must survive, and truthiness
    # would be one refactor away from silently dropping it.
    if assignee != '':
        params['assigned_to'] = assignee
    if detained:
        params['detained'] = detained
    if page > 1:
        params['page'] = page
    return params


def _queue_url(status='', assignee='', detained='', page=1) -> str:
    query = urlencode(_queue_params(status, assignee, detained, page))
    base = reverse('dashboard:queue')
    return f'{base}?{query}' if query else base


def _back_query(request) -> str:
    """Query string for links back to the queue, from validated GET state."""
    return urlencode(_queue_params(
        _selected_status(request),
        _selected_assignee(request),
        _selected_detained(request),
        _validated_page(request.GET.get('page', 1)),
    ))


def _queue_queryset(status, assignee, detained, query):
    """The queue's result set. Shared so a POST redirect can page against the same rows."""
    queryset = IntakeSubmission.objects.order_by('-detained', '-created_at').select_related('assigned_to')
    if status:
        queryset = queryset.filter(status=status)
    if assignee == _UNASSIGNED:
        queryset = queryset.filter(assigned_to__isnull=True)
    elif assignee:
        queryset = queryset.filter(assigned_to_id=assignee)
    if detained == _DETAINED_YES:
        queryset = queryset.filter(detained=True)
    elif detained == _DETAINED_NO:
        queryset = queryset.filter(detained=False)
    if query:
        queryset = queryset.filter(
            Q(full_name__icontains=query)
            | Q(country_of_origin__icontains=query)
            | Q(a_number__icontains=query)
        )
    return queryset


class CaseQueueView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    """Read-only queue of intake submissions, newest first."""

    permission_required = 'intake.access_dashboard'
    paginate_by = PAGE_SIZE
    template_name = 'dashboard/queue.html'
    context_object_name = 'submissions'

    def get_queryset(self):
        return _queue_queryset(
            _selected_status(self.request),
            _selected_assignee(self.request),
            _selected_detained(self.request),
            _active_search(self.request),
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['status_choices'] = IntakeSubmission.STATUS_CHOICES
        context['selected_status'] = _selected_status(self.request)
        context['assignable_users'] = _assignable_users()
        context['selected_assignee'] = _selected_assignee(self.request)
        context['UNASSIGNED'] = _UNASSIGNED
        context['selected_detained'] = _selected_detained(self.request)
        context['DETAINED_YES'] = _DETAINED_YES
        context['DETAINED_NO'] = _DETAINED_NO
        context['search_query'] = _active_search(self.request)
        # Row links carry the current filters and page so the detail back-link can
        # return here; built server-side so templates never assemble filter state.
        context['row_query'] = urlencode(_queue_params(
            context['selected_status'],
            context['selected_assignee'],
            context['selected_detained'],
            context['page_obj'].number,
        ))
        # Filters without a page number: the pager appends its own page param, so this
        # must omit page (left at its default of 1).
        context['filter_query'] = urlencode(_queue_params(
            context['selected_status'],
            context['selected_assignee'],
            context['selected_detained'],
        ))
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
            'selected_status': _selected_status(request),
            'selected_assignee': _selected_assignee(request),
            'selected_detained': _selected_detained(request),
            'selected_page': _validated_page(request.GET.get('page', 1)),
            'status_choices': IntakeSubmission.STATUS_CHOICES,
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

        # Separate forms post to this one URL; branch on the named submit button so a
        # note submit can never touch the assignment, and vice versa.
        if 'save_note' in request.POST:
            note_form = StaffNoteForm(request.POST)
            body = request.POST.get('body', '').strip()
            if body and note_form.is_valid():
                note = note_form.save(commit=False)
                note.intake = submission
                note.author = request.user
                note.save()
                messages.success(request, 'Note added.')
            return redirect('dashboard:detail', pk=pk)

        if 'save_assignment' in request.POST:
            # Assignment is a case-disposition write: access_dashboard lets a reviewer
            # read and leave notes, change_case_status is required to move the case.
            if not request.user.has_perm('intake.change_case_status'):
                raise PermissionDenied
            assign_form = AssignForm(
                request.POST, instance=submission, assignable_users=_assignable_users(),
            )
            if assign_form.is_valid():
                assign_form.save()
                messages.success(request, 'Assignment updated.')
                return redirect('dashboard:detail', pk=pk)
            return self._render(request, submission, assign_form, StaffNoteForm())

        return HttpResponseBadRequest('Unrecognized form submission.')


class CaseSearchView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """Stores a search term in the session, then redirects. Searching is a read."""

    permission_required = 'intake.access_dashboard'
    http_method_names = ['post']

    def post(self, request, *args, **kwargs):
        query = request.POST.get('q', '').strip()[:MAX_SEARCH_LENGTH]
        if query and 'clear' not in request.POST:
            request.session[SEARCH_SESSION_KEY] = query
        else:
            # icontains='' matches everything, so an empty query is a clear, not a search.
            request.session.pop(SEARCH_SESSION_KEY, None)
        # A new result set invalidates the page number; keep both filters.
        return redirect(_queue_url(
            _validated_status_value(request.POST.get('status', '')),
            _validated_assignee_value(request.POST.get('assigned_to', '')),
            _validated_detained_value(request.POST.get('detained', '')),
        ))


class CaseStatusUpdateView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """POST only, both permissions: read the dashboard and write case status."""

    permission_required = ('intake.access_dashboard', 'intake.change_case_status')
    http_method_names = ['post']

    def post(self, request, pk, *args, **kwargs):
        submission = get_object_or_404(IntakeSubmission, pk=pk)
        new_status = _validated_status_value(request.POST.get('new_status', ''))
        if not new_status:
            return HttpResponseBadRequest('Unrecognized status.')

        # A no-op submit must not reassign authorship of the change that actually happened.
        if new_status != submission.status:
            submission.status = new_status
            submission.status_changed_at = timezone.now()
            submission.status_changed_by = request.user
            submission.save(
                update_fields=['status', 'status_changed_at', 'status_changed_by'],
            )

        status = _validated_status_value(request.POST.get('status', ''))
        assignee = _validated_assignee_value(request.POST.get('assigned_to', ''))
        detained = _validated_detained_value(request.POST.get('detained', ''))
        return redirect(_queue_url(
            status, assignee, detained, self._clamped_page(request, status, assignee, detained),
        ))

    @staticmethod
    def _clamped_page(request, status, assignee, detained) -> int:
        # A status change can push a case out of the active filter and shrink the result
        # set, so the page the form came from may no longer exist. Built after the save
        # so the count reflects the new result set.
        page = _validated_page(request.POST.get('page', 1))
        paginator = Paginator(
            _queue_queryset(status, assignee, detained, _active_search(request)), PAGE_SIZE,
        )
        return min(page, paginator.num_pages)
