from django.contrib import admin

from core.models import Card, SafetyQuestion, SafetyAnswer
# Register your models here.

admin.site.register(Card)
admin.site.register(SafetyQuestion)
admin.site.register(SafetyAnswer)
