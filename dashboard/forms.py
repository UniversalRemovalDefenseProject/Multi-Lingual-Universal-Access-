from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm

from intake.models import IntakeSubmission

from .models import StaffNote

User = get_user_model()


class DashboardLoginForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].widget.attrs['placeholder'] = 'Username'
        self.fields['password'].widget.attrs['placeholder'] = 'Password'


class AssignForm(forms.ModelForm):
    class Meta:
        model = IntakeSubmission
        fields = ['assigned_to']

    def __init__(self, *args, **kwargs):
        assignable_users = kwargs.pop('assignable_users')
        super().__init__(*args, **kwargs)
        field = self.fields['assigned_to']
        held_by = self.instance.assigned_to_id
        if held_by and not assignable_users.filter(pk=held_by).exists():
            # The case is held by someone no longer assignable (deactivated account).
            # Without them in the queryset the dropdown would render as unassigned and
            # an untouched re-save would silently strip the assignment.
            assignable_users = (assignable_users | User.objects.filter(pk=held_by)).order_by(
                'username'
            )
        field.queryset = assignable_users
        field.required = False
        field.empty_label = '— Unassigned —'
        field.label_from_instance = _assignee_label


def _assignee_label(user):
    name = user.get_full_name() or user.username
    return name if user.is_active else f'{name} (deactivated)'


class StaffNoteForm(forms.ModelForm):
    class Meta:
        model = StaffNote
        fields = ['body']
        widgets = {
            'body': forms.Textarea(
                attrs={
                    'placeholder': 'Add a staff note here…',
                    'rows': 4,
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['body'].required = False
