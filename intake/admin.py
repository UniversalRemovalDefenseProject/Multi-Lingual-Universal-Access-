from django.contrib import admin

# Register your models here.
from django.contrib import admin
from .models import IntakeSubmission

@admin.register(IntakeSubmission)
class IntakeSubmissionAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'preferred_language', 'country_of_origin', 'detained', 'status', 'created_at')
    list_filter = ('preferred_language', 'detained', 'status', 'created_at')
    search_fields = ('full_name', 'country_of_origin', 'a_number', 'email', 'phone')