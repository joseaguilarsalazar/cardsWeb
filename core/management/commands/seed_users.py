# diary/management/commands/seed_users.py
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from core.models import SafetyQuestion, SafetyAnswer
import os, json
from django.conf import settings

class Command(BaseCommand):
    help = 'Seeds the database with the 2 core users and initial memory quiz questions.'

    def handle(self, *args, **options):
        self.stdout.write("Starting database seeding...")

        # 1. Create Your User (The Author/Admin)
        your_username = "joso_dovo"  # Change this to your preferred username
        your_email = "joseaguilarsalazar2004@gmail.com"
        your_temp_password = "ChangeMe123!" # Change this immediately after login!

        if not User.objects.filter(username=your_username).exists():
            your_user = User.objects.create_user(
                username=your_username,
                email=your_email,
                password=your_temp_password
            )
            your_user.is_staff = True
            your_user.is_superuser = True  # Gives you full admin panel access
            your_user.save()
            self.stdout.write(self.style.SUCCESS(f"Successfully created your user: '{your_username}'"))
        else:
            self.stdout.write(self.style.WARNING(f"User '{your_username}' already exists. Skipping."))

        # 2. Create Her User (The Partner)
        her_username = "soldurand"    # Change this to her preferred username
        her_email = "her@example.com"

        if not User.objects.filter(username=her_username).exists():
            her_user = User.objects.create_user(
                username=her_username,
                email=her_email
            )
            # This makes her account lock out from traditional login screen setups
            her_user.set_unusable_password() 
            her_user.save()
            self.stdout.write(self.style.SUCCESS(f"Successfully created her user: '{her_username}' (Password is set to unusable)"))
        else:
            self.stdout.write(self.style.WARNING(f"User '{her_username}' already exists. Skipping."))

        if not SafetyQuestion.objects.exists():
            # Construimos la ruta absoluta hacia la raíz del proyecto
            json_path = os.path.join(settings.BASE_DIR, 'quiz_data.json')
            
            if not os.path.exists(json_path):
                self.stdout.write(self.style.ERROR(f"Error: No se encontró el archivo '{json_path}'"))
                return

            try:
                with open(json_path, 'r', encoding='utf-8') as file:
                    quiz_data = json.load(file)
                
                # Iteramos sobre la lista de preguntas del archivo JSON
                for item in quiz_data:
                    pregunta_texto = item.get('question')
                    respuestas_lista = item.get('answers', [])
                    
                    # Creamos la pregunta principal
                    nueva_pregunta = SafetyQuestion.objects.create(question=pregunta_texto)
                    
                    # Iteramos y asociamos cada una de sus respuestas
                    for ans in respuestas_lista:
                        SafetyAnswer.objects.create(
                            question=nueva_pregunta,
                            answer=ans.get('answer'),
                            is_correct=ans.get('is_correct', False),
                            text_if_selected=ans.get('text_if_selected', '')
                        )
                
                self.stdout.write(self.style.SUCCESS(f"Se cargaron exitosamente las preguntas desde '{json_path}'."))
            
            except json.JSONDecodeError:
                self.stdout.write(self.style.ERROR("Error: El archivo quiz_data.json no tiene un formato JSON válido."))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Ocurrió un error inesperado al leer el JSON: {str(e)}"))
        else:
            self.stdout.write(self.style.WARNING("Ya existen preguntas en la base de datos. Omitiendo la carga del JSON."))

        self.stdout.write(self.style.SUCCESS("Database seeding process completed successfully!"))