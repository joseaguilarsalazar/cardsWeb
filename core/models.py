from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta

# Create your models here.

class Card(models.Model):
    title = models.CharField(max_length=100)
    text = models.TextField()
    fecha_redaccion = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    owner = models.ForeignKey(User, on_delete=models.CASCADE)

    def __str__(self):
        return self.title

    @property
    def is_unlocked(self):
        """
        Calculates if 30 days have passed since the fecha_redaccion.
        If True, the partner is allowed to see it.
        """
        today = timezone.now().date()
        unlock_date = self.fecha_redaccion + timedelta(days=30)
        return today >= unlock_date
    
class SafetyQuestion(models.Model):
    question = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.question
    
    def get_shuffled_answers(self):
        """
        Returns the answers for this question in a random order.
        """
        return self.answers.order_by('?')
    
class SafetyAnswer(models.Model):
    answer = models.TextField()
    is_correct = models.BooleanField(default=False)
    question = models.ForeignKey(SafetyQuestion, on_delete=models.CASCADE, related_name='answers')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.answer