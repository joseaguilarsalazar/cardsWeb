# views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Card, SafetyQuestion, SafetyAnswer, AltarEntry
from django.contrib.auth.models import User
from django.contrib.auth import update_session_auth_hash
import datetime
from django.conf import settings

def login_view(request):
    # If already logged in, skip the login screen
    if request.user.is_authenticated:
        return redirect('home')
        
    if request.method == 'POST':
        username = request.POST.get('username').strip()
        password = request.POST.get('password')
        
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)  # Triggers Django's session tracking engine
            return redirect('home')
        else:
            messages.error(request, "Incorrect username or password. Please try again.")
            
    return render(request, 'login.html')

@login_required(login_url='login')
def home_view(request):
    usuario_actual = request.user

    pareja = User.objects.exclude(id=usuario_actual.id).first()
    
    # Tus entradas ordenadas de la más reciente a la más antigua
    mis_entradas = Card.objects.filter(owner=usuario_actual).order_by('-fecha_redaccion')
    
    if pareja:
        # 1. Traemos todas sus entradas ordenadas de la más reciente a la más antigua
        raw_entradas_pareja = Card.objects.filter(owner=pareja).order_by('-fecha_redaccion')
        
        # 2. Separamos manteniendo el orden descendente gracias al QuerySet original
        unlocked_entries = [e for e in raw_entradas_pareja if e.is_unlocked]
        locked_entries = [e for e in raw_entradas_pareja if not e.is_unlocked]
        
        # 3. Combinamos: Primero las desbloqueadas (ej: 2, 1) y luego las bloqueadas (ej: 4, 3)
        entradas_pareja = unlocked_entries + locked_entries
    else:
        entradas_pareja = []

    context = {
        'mis_entradas': mis_entradas,
        'entradas_pareja': entradas_pareja,
        'pareja': pareja,
    }
    return render(request, 'home.html', context)

def logout_view(request):
    logout(request)
    return redirect('login')


@login_required(login_url='login')
def create_card_view(request):
    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        text = request.POST.get('text', '').strip()
        fecha_redaccion = request.POST.get('fecha_redaccion')

        if title and text and fecha_redaccion:
            # Creamos la tarjeta en la base de datos de manera simple
            Card.objects.create(
                title=title,
                text=text,
                fecha_redaccion=fecha_redaccion,
                owner=request.user
            )
            # Enviamos un mensaje de éxito que se mostrará en el Home
            messages.success(request, "¡Tu entrada de diario ha sido guardada con éxito!")
            return redirect('home')
        else:
            messages.error(request, "Por favor, completa todos los campos del formulario.")

    return render(request, 'create_card.html')



@login_required(login_url='login')
def card_detail_view(request, card_id):
    # Buscamos la tarjeta o lanzamos un error 404 si no existe
    card = get_object_or_404(Card, id=card_id)
    
    # GUARDIA DE SEGURIDAD CRÍTICA:
    # Si la tarjeta pertenece a tu pareja y NO está desbloqueada todavía, denegamos el acceso.
    if card.owner != request.user and not card.is_unlocked:
        messages.error(request, "Acceso denegado. Esta entrada aún se encuentra resguardada por el acuerdo de ayuno.")
        return redirect('home')
        
    return render(request, 'card_detail.html', {'card': card})


@login_required(login_url='login')
def edit_card_view(request, card_id):
    # Aseguramos que solo el DUEÑO real pueda editar su propia tarjeta
    card = get_object_or_404(Card, id=card_id, owner=request.user)
    
    if request.method == 'POST':
        card.title = request.POST.get('title', '').strip()
        card.text = request.POST.get('text', '').strip()
        
        fecha = request.POST.get('fecha_redaccion')
        if fecha:
            card.fecha_redaccion = fecha
            
        card.save() # Invoca automáticamente tus setters de encriptación
        messages.success(request, "¡Tu entrada ha sido actualizada con éxito!")
        return redirect('home')
        
    # Formateamos la fecha a YYYY-MM-DD para que el calendario nativo la entienda
    fecha_str = card.fecha_redaccion.strftime('%Y-%m-%d') if card.fecha_redaccion else ''
    return render(request, 'edit_card.html', {'card': card, 'fecha_str': fecha_str})


@login_required(login_url='login')
def delete_card_view(request, card_id):
    # Aseguramos que solo el dueño real pueda gatillar la eliminación
    card = get_object_or_404(Card, id=card_id, owner=request.user)
    
    if request.method == 'POST':
        card.delete()
        messages.success(request, "La entrada ha sido eliminada de forma permanente.")
        
    return redirect('home')


def quiz_view(request):
    # 1. Si no existe un juego activo en la sesión, lo inicializamos
    if 'quiz_question_ids' not in request.session:
        # Traemos los IDs de las preguntas ordenadas por ID de forma consistente
        question_ids = list(SafetyQuestion.objects.values_list('id', flat=True).order_by('id'))
        
        if not question_ids:
            messages.error(request, "No hay preguntas registradas en la base de datos todavía.")
            return redirect('home' if request.user.is_authenticated else 'login')
            
        request.session['quiz_question_ids'] = question_ids
        request.session['quiz_index'] = 0              # Empezamos en la pregunta 1 (índice 0)
        request.session['quiz_state'] = 'question'      # Estados válidos: 'question' o 'feedback'
        request.session['quiz_selected_answer_id'] = None

    # Recuperamos los estados de la sesión actual
    question_ids = request.session['quiz_question_ids']
    current_index = request.session['quiz_index']
    state = request.session['quiz_state']
    
    # Control de desborde por seguridad
    if current_index >= len(question_ids):
        if request.user.is_authenticated:
            return redirect('home')
        return redirect('setup_password') if request.session.get('passed_quiz') else redirect('login')

    # Buscamos la pregunta actual en la base de datos
    current_question_id = question_ids[current_index]
    pregunta = get_object_or_404(SafetyQuestion, id=current_question_id)
    
    # Si ya eligió una opción, cargamos el objeto de la respuesta seleccionada
    selected_answer = None
    if request.session.get('quiz_selected_answer_id'):
        selected_answer = SafetyAnswer.objects.filter(id=request.session['quiz_selected_answer_id']).first()

    # PROCESAMIENTO DE ACCIONES MEDIANTE POST
    if request.method == 'POST':
        action = request.POST.get('action')
        
        # PASO A: Ella envía su opción elegida
        if state == 'question' and action == 'submit_answer':
            answer_id = request.POST.get('answer_id')
            if not answer_id:
                messages.error(request, "Por favor, selecciona una opción antes de continuar.")
                return redirect('quiz')
                
            request.session['quiz_selected_answer_id'] = int(answer_id)
            request.session['quiz_state'] = 'feedback' # Cambiamos al estado de ver la reacción
            request.session.modified = True
            return redirect('quiz')
            
        # PASO B: Ella lee tu texto y presiona el botón "Continuar"
        elif state == 'feedback' and action == 'continue':
            if selected_answer:
                if selected_answer.is_correct:
                    # ¡ACERTÓ! Avanzamos el índice a la siguiente pregunta
                    request.session['quiz_index'] = current_index + 1
                    
                    # ¿Era la última pregunta?
                    if request.session['quiz_index'] >= len(question_ids):
                        # Limpiamos las variables de control del juego
                        request.session.pop('quiz_question_ids', None)
                        request.session.pop('quiz_index', None)
                        request.session.pop('quiz_state', None)
                        request.session.pop('quiz_selected_answer_id', None)
                        
                        if request.user.is_authenticated:
                            messages.success(request, "¡Increíble! Te acuerdas de absolutamente todo a la perfección. 💕")
                            return redirect('home')
                        else:
                            # Le abrimos la compuerta de acceso temporal
                            request.session['passed_quiz'] = True
                            return redirect('setup_password')
                else:
                    # ¡FALLÓ! Se queda en la misma pregunta para reintentarlo
                    pass
            
            # Reseteamos al estado normal de pregunta para la siguiente iteración o reintento
            request.session['quiz_state'] = 'question'
            request.session['quiz_selected_answer_id'] = None
            request.session.modified = True
            return redirect('quiz')

    # Para evitar que las respuestas cambien de posición entre el paso de pregunta y el de feedback,
    # las ordenamos de forma fija por su ID de base de datos.
    respuestas = pregunta.answers.all().order_by('id')

    context = {
        'pregunta': pregunta,
        'respuestas': respuestas,
        'current_index': current_index + 1,
        'total_preguntas': len(question_ids),
        'state': state,
        'selected_answer': selected_answer,
    }
    return render(request, 'quiz.html', context)


def setup_password_view(request):
    if request.user.is_authenticated:
        return redirect('home')
        
    # GUARDIA DE SEGURIDAD CRÍTICA: Bloquea el ingreso directo si no pasó el juego
    if not request.session.get('passed_quiz', False):
        messages.error(request, "Debes completar el cuestionario de recuerdos para acceder a esta página.")
        return redirect('quiz')
        
    if request.method == 'POST':
        password = request.POST.get('password')
        password_confirm = request.POST.get('password_confirm')
        
        # Buscamos dinámicamente al usuario que no es administrador (Solange)
        partner_user = User.objects.filter(is_staff=False).first()
        
        if not partner_user:
            messages.error(request, "Error de sistema: No se encontró la cuenta de destino.")
            return redirect('quiz')
            
        if password == password_confirm:
            if len(password) < 4:
                messages.error(request, "Como que menos de 4 caracteres, acaso quieres que te hackeen?")
            else:
                # Registramos su contraseña real de forma segura
                partner_user.set_password(password)
                partner_user.save()
                
                # Cerramos la compuerta de sesión temporal y la logueamos de forma inmediata
                request.session.pop('passed_quiz', None)
                login(request, partner_user)
                
                messages.success(request, "Listo ya estas dentro, espero que puedas apreciar este pequeño espacio que hice solo para nosotros 💕")
                return redirect('home')
        else:
            messages.error(request, "Cuidado con tu TDAH, como asi que las contraseñas no coinciden? Intenta de nuevo con calma.")
            
    return render(request, 'setup_password.html')


@login_required(login_url='login')
def profile_view(request):
    usuario = request.user
    
    # 1. CÁLCULO DE ESTADÍSTICAS DINÁMICAS
    fecha_inicio = getattr(settings, 'FAST_START_DATE', datetime.date.today())
    hoy = datetime.date.today()
    
    # Días transcurridos desde el inicio (Día 1, Día 2, etc.)
    dias_completados = (hoy - fecha_inicio).days + 1
    dias_completados = max(1, dias_completados) # Evita ceros si están en el día de inicio
    
    # Controlamos el tope del propósito de 90 días
    if dias_completados > 90:
        dias_completados = 90
        dias_restantes = 0
    else:
        dias_restantes = 90 - dias_completados
        
    # Total de reflexiones escritas por este usuario específico
    total_entradas = Card.objects.filter(owner=usuario).count()

    # 2. PROCESAMIENTO DEL FORMULARIO DE EDICIÓN DE PERFIL
    if request.method == 'POST':
        nuevo_username = request.POST.get('username', '').strip()
        nuevo_email = request.POST.get('email', '').strip()
        
        if nuevo_username and nuevo_email:
            # Validación rápida para evitar nombres duplicados
            if nuevo_username != usuario.username and User.objects.filter(username=nuevo_username).exists():
                messages.error(request, "Este nombre de usuario ya está en uso. Elige otro.")
            else:
                usuario.username = nuevo_username
                usuario.email = nuevo_email
                usuario.save()
                messages.success(request, "¡Tus datos de perfil han sido actualizados!")
                return redirect('profile')
        else:
            messages.error(request, "Por favor, completa todos los campos obligatorios.")

    context = {
        'dias_completados': dias_completados,
        'dias_restantes': dias_restantes,
        'total_entradas': total_entradas,
    }
    return render(request, 'profile.html', context)


@login_required(login_url='login')
def change_password_view(request):
    if request.method == 'POST':
        current_password = request.POST.get('current_password')
        new_password = request.POST.get('new_password')
        confirm_password = request.POST.get('confirm_password')
        
        usuario = request.user
        
        # 1. Validamos la contraseña actual
        if not usuario.check_password(current_password):
            messages.error(request, "La contraseña actual es incorrecta.")
        # 2. Validamos que las nuevas coincidan
        elif new_password != confirm_password:
            messages.error(request, "Las nuevas contraseñas no coinciden entre sí.")
        # 3. Validación de longitud mínima de seguridad
        elif len(new_password) < 4:
            messages.error(request, "La nueva contraseña debe tener al menos 4 caracteres.")
        else:
            # Guardamos de forma segura
            usuario.set_password(new_password)
            usuario.save()
            
            # ¡CRUCIAL! Actualiza la sesión para que Django no desloguee al usuario al cambiar la clave
            update_session_auth_hash(request, usuario)
            
            messages.success(request, "¡Tu contraseña ha sido cambiada con éxito!")
            return redirect('profile')
            
    return render(request, 'change_password.html')


@login_required(login_url='login')
def faq_view(request):
    return render(request, 'faq.html')

@login_required(login_url='login')
def timeline_view(request):
    # Eliminados los marcadores ocultos que rompían la sintaxis de Python
    fecha_inicio = getattr(settings, 'FAST_START_DATE', datetime.date.today())
    hoy = datetime.date.today()
    dias_completados = (hoy - fecha_inicio).days + 1
    
    # Generamos la lista del 1 al 90 con el estado de cada día
    dias_lista = []
    for i in range(1, 91):
        
        if i < dias_completados:
            estado = 'pasado'
        elif i == dias_completados:
            estado = 'hoy'
        else:
            estado = 'futuro'
            
        dias_lista.append({
            'numero': i,
            'estado': estado,
        })
        
    context = {
        'dias_lista': dias_lista,
        'dia_actual': min(90, max(1, dias_completados)),
    }
    return render(request, 'timeline.html', context)


@login_required(login_url='login')
def altar_view(request):
    usuario_actual = request.user
    pareja = User.objects.exclude(id=usuario_actual.id).first()
    
    # 1. Determinar el tiempo del ayuno
    fecha_inicio = getattr(settings, 'FAST_START_DATE', datetime.date.today())
    dias_completados = (datetime.date.today() - fecha_inicio).days + 1
    es_dia_91_o_mas = dias_completados >= 91
    
    # Recolectar las promesas escritas por el usuario actual
    mis_promesas = AltarEntry.objects.filter(owner=usuario_actual).order_by('created_at')
    
    # 2. FASE ANTES DEL DÍA 91: Escritura libre y resguardo ciego
    if not es_dia_91_o_mas:
        if request.method == 'POST' and 'guardar_promesa' in request.POST:
            texto = request.POST.get('promise_text', '').strip()
            if texto:
                nueva_promesa = AltarEntry(owner=usuario_actual)
                nueva_promesa.text = texto  # El setter lo encripta automáticamente
                nueva_promesa.save()
                messages.success(request, "¡Tu palabra ha sido sellada y guardada en el Altar! 🌟")
                return redirect('altar')
                
        return render(request, 'altar.html', {
            'es_dia_91_o_mas': False,
            'mis_promesas': mis_promesas,
            'conteo_mis_promesas': mis_promesas.count(),
            'dias_faltantes': 91 - dias_completados
        })
        
    # 3. FASE DÍA 91+: COMPUERTA DE ANFITRIÓN DOBLE CONTRASEÑA
    altar_desbloqueado = request.session.get('altar_unlocked', False)
    
    if request.method == 'POST' and 'verificar_llaves' in request.POST:
        pass_actual = request.POST.get('password_mine')
        pass_pareja = request.POST.get('password_partner')
        
        # Validación A: Contraseña de quien está sentado frente a la pantalla
        if not usuario_actual.check_password(pass_actual):
            messages.error(request, f"Tu contraseña ({usuario_actual.username}) es incorrecta.")
        # Validación B: Contraseña de la pareja que acompaña el momento
        elif not pareja or not pareja.check_password(pass_pareja):
            messages.error(request, f"La contraseña de su pareja ({pareja.username if pareja else 'Solange'}) es incorrecta.")
        else:
            # Ambos códigos coinciden: Abrimos el cofre en la sesión actual
            request.session['altar_unlocked'] = True
            return redirect('altar')
            
    # Si ya superaron la prueba de llaves, cargamos los datos desencriptados de ambos
    todas_las_promesas = []
    if altar_desbloqueado:
        todas_las_promesas = AltarEntry.objects.all().order_by('created_at')
        
    return render(request, 'altar.html', {
        'es_dia_91_o_mas': True,
        'altar_desbloqueado': altar_desbloqueado,
        'todas_las_promesas': todas_las_promesas,
        'pareja': pareja
    })