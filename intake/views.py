from django.shortcuts import render

# Create your views here.
from django.shortcuts import render, redirect
from .forms import IntakeSubmissionForm

def intake_form(request):
    if request.method == 'POST':
        form = IntakeSubmissionForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('intake_success')
    else:
        form = IntakeSubmissionForm()

    return render(request, 'intake/intake_form.html', {'form': form})


def intake_success(request):
    return render(request, 'intake/intake_success.html')