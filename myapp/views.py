# myapp/views.py
from django.conf import settings
from django.shortcuts import render, redirect, get_object_or_404  # Ensure get_object_or_404 is imported
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.db import transaction

  # Correct import for login_required
from .forms import RegistrationForm, LoginForm
from .models import User, Service, Booking  # Ensure Service and Booking are imported
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
import stripe # type: ignore
import bleach
from django.utils.html import escape


stripe.api_key = settings.STRIPE_SECRET_KEY

@csrf_exempt
def stripe_webhook(request):
    payload = request.body
    sig_header = request.META['HTTP_STRIPE_SIGNATURE']
    event = None

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    except ValueError as e:
        # Invalid payload
        return JsonResponse({'error': str(e)}, status=400)
    except stripe.error.SignatureVerificationError as e:
        # Invalid signature
        return JsonResponse({'error': str(e)}, status=400)

    # Handle the event
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        # Fulfill the purchase...
        handle_checkout_session(session)

    return JsonResponse({'status': 'success'}, status=200)

def handle_checkout_session(session):
    # Retrieve the booking using the session ID
    booking = Booking.objects.get(stripe_session_id=session.id)
    booking.payment_status = 'paid'
    booking.save()

def sanitize_input(data):
    """Sanitize user inout to prevent XSS attacks"""
    if isinstance(data, str):
        return bleach.clean(data)
    return data

def register(request):
    if request.method == 'POST':
        # Sanitize all POST data
        clean_data = {key: sanitize_input(value) 
                     for key, value in request.POST.items()}
        form = RegistrationForm(clean_data)
        if form.is_valid():
            try:
                with transaction.atomic():
                    user = form.save()
                messages.success(request, 'Registration successful! You can now log in.')
                return redirect('login')
            except Exception as e:
                messages.error(request, 'An error occurred during registration.')
    else:
        form = RegistrationForm()
    return render(request, 'register.html', {'form': form})


def home(request):
    return render(request, 'home.html')

def login_view(request):
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, 'Login successful!')
                return redirect('service_list')
            else:
                messages.error(request, 'Invalid username or password.')
    else:
        form = LoginForm()
        
    return render(request, 'login.html', {'form': form})

def logout_view(request):
    logout(request)
    messages.success(request, 'You have been logged out.')
    return redirect('login')

def service_list(request):
    services = Service.objects.all()
    return render(request, 'service_list.html', {'services': services})

def service_detail(request, id):
    service = get_object_or_404(Service, id=id)
    return render(request, 'service_detail.html', {'service': service})

def recommend_service(request):
    services = Service.objects.order_by('price')[:1]
    return render(request, 'recommend_service.html', {'services': services})

@login_required  # Ensure that the user is logged in before booking
def book_service(request, pk):
    service = get_object_or_404(Service, pk=pk)
    if request.method == 'POST':
        # Create a Stripe Checkout Session
        session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': 'usd',
                    'product_data': {
                        'name': service.name,
                    },
                    'unit_amount': int(service.price * 100),  # Amount in cents
                },
                'quantity': 1,
            }],
            mode='payment',
            success_url=request.build_absolute_uri('/success/'),
            cancel_url=request.build_absolute_uri('/cancel/'),
        )
        # Create a booking record
        Booking.objects.create(
            user=request.user,
            service=service,
            amount_paid=service.price,
            stripe_session_id=session.id,
        )
        return redirect(session.url)
    return render(request, 'book_service.html', {'service': service})

def success_view(request):
    return render(request, 'success.html')

def cancel_view(request):
    return render(request, 'cancel.html')