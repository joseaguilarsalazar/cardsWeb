from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
from cryptography.fernet import Fernet
from django.conf import settings
import base64
# Create your models here.

class Card(models.Model):
    # Guardaremos los textos encriptados en campos de texto normales
    title_encrypted = models.TextField(db_column='title')
    text_encrypted = models.TextField(db_column='text', max_length=10000)
    
    fecha_redaccion = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    owner = models.ForeignKey(User, on_delete=models.CASCADE)

    def __str__(self):
        # Desencripta el título solo para la representación en consola/admin
        return self.title

    # --- MOTOR DE ENCRIPCIÓn INTERNO ---
    def _get_cipher(self):
        """Genera el descifrador usando la SECRET_KEY de tu settings.py"""
        # Fernet necesita una llave de 32 bytes en base64. 
        # Forzamos a que tu SECRET_KEY de Django cumpla con este formato.
        key = settings.SECRET_KEY[:32].encode('utf-8')
        encoded_key = base64.urlsafe_b64encode(key)
        return Fernet(encoded_key)

    # --- PROPIEDADES DINÁMICAS (GETTERS Y SETTERS) ---
    @property
    def title(self):
        """Desencripta el título al leerlo desde Python"""
        if not self.title_encrypted:
            return ""
        try:
            cipher = self._get_cipher()
            return cipher.decrypt(self.title_encrypted.encode('utf-8')).decode('utf-8')
        except Exception:
            return "[Error al desencriptar título]"

    @title.setter
    def title(self, value):
        """Encripta el título al asignarlo"""
        if value:
            cipher = self._get_cipher()
            self.title_encrypted = cipher.encrypt(value.encode('utf-8')).decode('utf-8')

    @property
    def text(self):
        """Desencripta el cuerpo del texto al leerlo"""
        if not self.text_encrypted:
            return ""
        try:
            cipher = self._get_cipher()
            return cipher.decrypt(self.text_encrypted.encode('utf-8')).decode('utf-8')
        except Exception:
            return "[Error al desencriptar contenido]"

    @text.setter
    def text(self, value):
        """Encripta el cuerpo del texto al asignarlo"""
        if value:
            cipher = self._get_cipher()
            self.text_encrypted = cipher.encrypt(value.encode('utf-8')).decode('utf-8')
    
    @property
    def dias_restantes(self):
        """Calcula cuántos días faltan para el desbloqueo"""
        today = timezone.now().date()
        unlock_date = self.fecha_redaccion + timedelta(days=30)
        remaining = (unlock_date - today).days
        return max(0, remaining) # Evita números negativos

    # --- TU REGLA DE LOS 30 DÍAS ---
    @property
    def is_unlocked(self):
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
    text_if_selected = models.TextField(blank=True, null=True, help_text="Texto que se mostrará si el usuario selecciona esta respuesta (opcional)")
    question = models.ForeignKey(SafetyQuestion, on_delete=models.CASCADE, related_name='answers')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.answer