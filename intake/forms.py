from django import forms
from django.utils.translation import gettext_lazy as _

from .models import IntakeSubmission


class IntakeSubmissionForm(forms.ModelForm):
    consent_acknowledged = forms.BooleanField(
        label=_(
            "I understand that submitting this form does not create an "
            "attorney-client relationship."
        ),
        required=True,
        error_messages={
            "required": _("Please acknowledge this notice before submitting your intake.")
        },
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
    )

    class Meta:
        model = IntakeSubmission
        fields = [
            'full_name',
            'date_of_birth',
            'country_of_origin',
            'preferred_language',
            'phone',
            'email',
            'current_location',
            'detained',
            'immigration_court',
            'a_number',
            'next_hearing_date',
            'fear_of_return_summary',
            'past_harm_summary',
            'countries_traveled_asylum_summary',
            'family_members_included',
            'consent_acknowledged',
        ]
        labels = {
            "full_name": _("Full name"),
            "date_of_birth": _("Date of birth"),
            "country_of_origin": _("Country of origin"),
            "preferred_language": _("Preferred language"),
            "phone": _("Phone number"),
            "email": _("Email address"),
            "current_location": _("Current city or location"),
            "detained": _("Currently detained"),
            "immigration_court": _("Immigration court"),
            "a_number": _("A-number"),
            "next_hearing_date": _("Next hearing date"),
            "fear_of_return_summary": _("Reason for fearing return"),
            "past_harm_summary": _("Past harm or persecution"),
            "countries_traveled_asylum_summary": _(
                "Countries traveled through and asylum applications"
            ),
            "family_members_included": _("Family members included"),
        }
        widgets = {
            "full_name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": _("Enter your full name"),
                    "autocomplete": "name",
                }
            ),
            "date_of_birth": forms.DateInput(
                attrs={
                    "class": "form-control",
                    "type": "date",
                    "autocomplete": "bday",
                }
            ),
            "country_of_origin": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": _("Country where you are from"),
                    "autocomplete": "country-name",
                }
            ),
            "preferred_language": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": _("Language you prefer for communication"),
                    "autocomplete": "language",
                }
            ),
            "phone": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": _("Best phone number to reach you"),
                    "autocomplete": "tel",
                    "inputmode": "tel",
                }
            ),
            "email": forms.EmailInput(
                attrs={
                    "class": "form-control",
                    "placeholder": _("Email address, if available"),
                    "autocomplete": "email",
                    "inputmode": "email",
                }
            ),
            "current_location": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": _("City, state, or detention facility"),
                    "autocomplete": "address-level2",
                }
            ),
            "detained": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "immigration_court": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": _("Court name or city, if known"),
                }
            ),
            "a_number": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": _("Example: A123456789"),
                    "autocomplete": "off",
                }
            ),
            "next_hearing_date": forms.DateInput(
                attrs={"class": "form-control", "type": "date"}
            ),
            "fear_of_return_summary": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "placeholder": _("Describe why returning would be unsafe for you."),
                    "rows": 5,
                    "aria-describedby": "fear-of-return-help",
                }
            ),
            "past_harm_summary": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "placeholder": _("Describe any past harm, threats, or persecution."),
                    "rows": 5,
                    "aria-describedby": "past-harm-help",
                }
            ),
            "countries_traveled_asylum_summary": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "placeholder": _(
                        "List countries traveled through and whether you applied for asylum."
                    ),
                    "rows": 5,
                    "aria-describedby": "countries-traveled-help",
                }
            ),
            "family_members_included": forms.CheckboxInput(
                attrs={"class": "form-check-input"}
            ),
        }
