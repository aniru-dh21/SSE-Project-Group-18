from django.conf import settings
from django.shortcuts import render, redirect, get_object_or_404  # Ensure get_object_or_404 is imported
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db import transaction

from .forms import RegistrationForm, LoginForm, ServicePackageForm, CustomizePackageForm, InspectionServiceForm
from .models import User, Service, Booking, ServicePackage, PackageService, InspectionService, InspectionFindings  # Ensure Service and Booking are imported
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
    return render(request, 'logout.html')

def service_list(request):
    services = Service.objects.all()
    return render(request, 'service_list.html', {'services': services})

def service_detail(request, id):
    service = get_object_or_404(Service, id=id)
    return render(request, 'service_detail.html', {'service': service})

def recommend_service(request):
    services = Service.objects.order_by('price')[:1]
    return render(request, 'recommend_service.html', {'services': services})

@login_required
def dashboard(request):
    context = {
        'user': request.user,
    }
    
    if request.user.is_service_provider:
        # Service provider dashboard
        provided_services = Service.objects.filter(provider=request.user)
        service_bookings = Booking.objects.filter(
            service__in=provided_services
        ).select_related('user', 'service').order_by('-booking_date')
        
        context.update({
            'provided_services': provided_services,
            'service_bookings': service_bookings,
        })
        return render(request, 'dashboard_provider.html', context)
    else:
        # Regular user dashboard
        user_bookings = Booking.objects.filter(user=request.user).select_related('service')
        context.update({
            'bookings': user_bookings,
        })
        return render(request, 'dashboard.html', context)

@login_required
def edit_profile(request):
    if request.method == 'POST':
        # Sanitize all POST data
        clean_data = {key: sanitize_input(value)
                      for key, value in request.POST.items()}
        
        # Update user fields
        user = request.user
        updateable_fields = [
            'mobile', 'country_of_citizenship', 'language_preferred',
            'covid_vaccination_status', 'trade', 'profession'
        ]

        try:
            with transaction.atomic():
                for field in updateable_fields:
                    if field in clean_data:
                        setattr(user, field, clean_data[field])
                user.save()
                messages.success(request, 'Profile updated successfully!')
        except Exception as e:
            messages.error(request, 'An error occurred while updating your profile.')
        
        return redirect('dashboard')
    
    return render(request, 'edit_profile.html', {'user': request.user})

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

def package_list(request):
    packages = ServicePackage.objects.prefetch_related('services').all()
    return render(request, 'packages/package_list.html', {'packages': packages})

def package_detail(request, pk):
    package = get_object_or_404(ServicePackage, pk=pk)
    customize_form = None
    
    if package.is_customizable:
        customize_form = CustomizePackageForm(package)
    
    # Calculate the discount amount
    total_price = package.get_total_price()
    original_price = package.get_original_price()  
    discount = original_price - total_price
    
    context = {
        'package': package,
        'customize_form': customize_form,
        'discount': discount,
        'original_price': original_price,
    }
    return render(request, 'packages/package_detail.html', context)

@login_required
def book_package(request, pk):
    package = get_object_or_404(ServicePackage, pk=pk)
    selected_services = package.services.all()
    total_price = package.get_total_price()

    if request.method == 'POST':
        if package.is_customizable:
            form = CustomizePackageForm(package, request.POST)
            if form.is_valid():
                selected_services = []
                for package_service in PackageService.objects.filter(package=package):
                    if not package_service.is_optional or \
                       form.cleaned_data.get(f'service_{package_service.service.id}', False):
                        selected_services.append(package_service.service)
                
                total_price = sum(service.price for service in selected_services)
                discount = (total_price * package.discount_percentage) / 100
                total_price -= discount

        # Create Stripe session for the package
        session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': 'usd',
                    'product_data': {
                        'name': f"Package: {package.name}",
                    },
                    'unit_amount': int(total_price * 100),
                },
                'quantity': 1,
            }],
            mode='payment',
            success_url=request.build_absolute_uri('/success/'),
            cancel_url=request.build_absolute_uri('/cancel/'),
        )

        # Create bookings for all selected services
        with transaction.atomic():
            for service in selected_services:
                Booking.objects.create(
                    user=request.user,
                    service=service,
                    amount_paid=service.price * (1 - package.discount_percentage/100),
                    stripe_session_id=session.id,
                )

        return redirect(session.url)

    return render(request, 'packages/book_package.html', {
        'package': package,
        'selected_services': selected_services,
        'total_price': total_price,
    })

@login_required
@user_passes_test(lambda u: u.is_superuser)
def create_package(request):
    if request.method == 'POST':
        form = ServicePackageForm(request.POST)
        if form.is_valid():
            package = form.save()
            messages.success(request, 'Service package created successfully!')
            return redirect('package_list')
    else:
        form = ServicePackageForm()
    
    return render(request, 'packages/create_package.html', {'form': form})

@login_required
def book_inspection(request):
    if request.method == 'POST':
        form = InspectionServiceForm(request.POST)
        if form.is_valid():
            inspection = form.save(commit=False)
            inspection.user = request.user
            inspection.save()
            
            # Create Stripe session for inspection payment
            session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=[{
                    'price_data': {
                        'currency': 'usd',
                        'product_data': {
                            'name': 'General House Inspection Service',
                        },
                        'unit_amount': 10000,  # $100.00
                    },
                    'quantity': 1,
                }],
                mode='payment',
                success_url=request.build_absolute_uri('/inspection/success/'),
                cancel_url=request.build_absolute_uri('/inspection/cancel/'),
            )
            
            return redirect(session.url)
    else:
        form = InspectionServiceForm()
    
    return render(request, 'inspection/book_inspection.html', {'form': form})

@login_required
def view_inspection_results(request, inspection_id):
    inspection = get_object_or_404(InspectionService, id=inspection_id, user=request.user)
    findings = inspection.findings.all().order_by('-urgency_level')
    
    total_estimated_cost = sum(finding.estimated_cost for finding in findings)
    
    context = {
        'inspection': inspection,
        'findings': findings,
        'total_estimated_cost': total_estimated_cost,
    }
    return render(request, 'inspection/inspection_results.html', context)

def inspection_success(request):
    return render(request, 'inspection/inspection_success.html')

@login_required
@user_passes_test(lambda u: u.is_service_provider)
def manage_services(request):
    if request.method == 'POST':
        action = request.POST.get('action')
        service_id = request.POST.get('service_id')
        
        if action == 'toggle_status':
            # Handle status toggle
            service = get_object_or_404(Service, id=service_id, provider=request.user)
            service.is_available = not service.is_available
            service.save()
            messages.success(request, f'Service status updated successfully!')
            
        elif action == 'update':
            # Handle service update
            service = get_object_or_404(Service, id=service_id, provider=request.user)
            service.name = request.POST.get('name')
            service.description = request.POST.get('description')
            service.price = request.POST.get('price')
            service.is_available = request.POST.get('is_available') == 'on'
            service.service_area = request.POST.get('service_area')
            service.save()
            messages.success(request, f'Service updated successfully!')
            
        else:
            # Handle new service creation
            Service.objects.create(
                provider=request.user,
                name=request.POST.get('name'),
                description=request.POST.get('description'),
                price=request.POST.get('price'),
                is_available=request.POST.get('is_available', False) == 'on',
                service_area=request.POST.get('service_area')
            )
            messages.success(request, 'New service added successfully!')
            
        return redirect('manage_services')
    
    services = Service.objects.filter(provider=request.user)
    return render(request, 'manage_services.html', {'services': services})