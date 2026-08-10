from django import forms
from django.contrib.auth.forms import AuthenticationForm

from intake.models import IntakeSubmission
from .models import StaffNote


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
        self.fields['assigned_to'].queryset = assignable_users
        self.fields['assigned_to'].required = False
        self.fields['assigned_to'].empty_label = '— Unassigned —'


class StaffNoteForm(forms.ModelForm):
    class Meta:
        model = StaffNote
        fields = ['body']
        widgets = {
            'body': forms.Textarea(attrs={
                'placeholder': 'Add a staff note here…',
                'rows': 4,
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['body'].required = False
