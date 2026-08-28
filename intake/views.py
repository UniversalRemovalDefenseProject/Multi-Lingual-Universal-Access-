from django.conf import settings
from django.forms import CheckboxInput
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.utils import translation

from .forms import IntakeSubmissionForm

SUPPORTED_LANGUAGE_CODES = {code for code, _name in settings.LANGUAGES}


def _valid_language(code: str | None) -> str:
    if code in SUPPORTED_LANGUAGE_CODES and translation.check_for_language(code):
        return code
    current_language = translation.get_language() or settings.LANGUAGE_CODE
    if current_language in SUPPORTED_LANGUAGE_CODES:
        return current_language
    return settings.LANGUAGE_CODE


def _remember_language(response: HttpResponse, language_code: str) -> HttpResponse:
    response.set_cookie(
        settings.LANGUAGE_COOKIE_NAME,
        language_code,
        max_age=settings.LANGUAGE_COOKIE_AGE,
        path=settings.LANGUAGE_COOKIE_PATH,
        domain=settings.LANGUAGE_COOKIE_DOMAIN,
        secure=settings.LANGUAGE_COOKIE_SECURE,
        httponly=settings.LANGUAGE_COOKIE_HTTPONLY,
        samesite=settings.LANGUAGE_COOKIE_SAMESITE,
    )
    return response


def _preserved_form_values(request: HttpRequest) -> dict[str, object]:
    # Switching display language must not force an applicant to re-enter draft answers.
    initial = {}
    for name, field in IntakeSubmissionForm.base_fields.items():
        if isinstance(field.widget, CheckboxInput):
            initial[name] = name in request.POST
        else:
            initial[name] = request.POST.get(name, '')
    return initial


def intake_form(request: HttpRequest) -> HttpResponse:
    requested_language = request.POST.get('language') if request.method == 'POST' else None
    language_code = _valid_language(requested_language)
    translation.activate(language_code)

    if request.method == 'POST' and request.POST.get('form_action') == 'change_language':
        form = IntakeSubmissionForm(initial=_preserved_form_values(request))
        response = render(
            request,
            'intake/intake_form.html',
            {'form': form, 'selected_language': language_code},
        )
        return _remember_language(response, language_code)

    if request.method == 'POST':
        form = IntakeSubmissionForm(request.POST)
        if form.is_valid():
            submission = form.save(commit=False)
            submission.language_preference = language_code
            submission.save()
            return _remember_language(redirect('intake_success'), language_code)
    else:
        form = IntakeSubmissionForm()

    response = render(
        request,
        'intake/intake_form.html',
        {'form': form, 'selected_language': language_code},
    )
    if request.method == 'POST':
        return _remember_language(response, language_code)
    return response


def intake_success(request: HttpRequest) -> HttpResponse:
    return render(request, 'intake/intake_success.html')
