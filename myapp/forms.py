from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import User, ServicePackage, PackageService, Service, InspectionService, InspectionFindings
from django.core.validators import RegexValidator
from django.core.exceptions import ValidationError

class RegistrationForm(UserCreationForm):
    # Username validation
    username = forms.CharField(
        min_length=4,
        max_length=150,
        validators=[
            RegexValidator(
                regex='^[a-zA-Z0-9_]*$',
                message='Username must contain only letters, numbers, and underscores',
                code='invalid_username'
            ),
        ]
    )

    # Password validation
    def clean_password1(self):
        password = self.cleaned_data.get('password1')
        if len(password) < 8:
            raise ValidationError('Password must be at least 8 characters long')
        if not any(char.isdigit() for char in password):
            raise ValidationError('Password must contain at least one number')
        if not any(char.isupper() for char in password):
            raise ValidationError('Password must contain at least one uppercase letter')
        if not any(char.islower() for char in password):
            raise ValidationError('Password must contain at least one lowercase letter')
        if not any(char in '!@#$%^&*()' for char in password):
            raise ValidationError('Password must contain at least one special character')
        return password
    
    # Clean and sanitize other fields
    def clean_mobile(self):
        mobile = self.cleaned_data.get('mobile')
        return forms.CharField(validators=[
            RegexValidator(regex=r'^\+?1?\d{9,15}$', 
            message="Phone number must be entered in the format: '+999999999'.")
        ]).clean(mobile)
    
    def clean_credit_card(self):
        credit_card = self.cleaned_data.get('credit_card')
        # Remove any non-digit characters and validate
        cleaned_cc = ''.join(filter(str.isdigit, credit_card))
        if not cleaned_cc.isdigit() or len(cleaned_cc) not in [15, 16]:
            raise ValidationError('Invalid credit card number')
        return cleaned_cc
    
    class Meta:
        model = User
        fields = ['username', 'password1', 'password2', 'age', 'mobile', 
                  'country_of_citizenship', 'language_preferred', 
                  'covid_vaccination_status', 'credit_card', 
                  'trade', 'profession', 'is_service_provider']

class LoginForm(forms.Form):
    username = forms.CharField(max_length=100)
    password = forms.CharField(widget=forms.PasswordInput)

class ServicePackageForm(forms.ModelForm):
    services = forms.ModelMultipleChoiceField(
        queryset=Service.objects.all(),
        widget=forms.CheckboxSelectMultiple
    )

    class Meta:
        model = ServicePackage
        fields = ['name', 'description', 'services', 'base_price', 'discount_percentage', 'is_customizable']

class CustomizePackageForm(forms.Form):
    def __init__(self, package, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for package_service in PackageService.objects.filter(package=package):
            if package_service.is_optional:
                self.fields[f'service_{package_service.service.id}'] = forms.BooleanField(
                    label=f"{package_service.service.name} (${package_service.service.price})",
                    required=False,
                    initial=True
                )

class InspectionServiceForm(forms.ModelForm):
    preferred_date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}),
        help_text="When would you like the inspection to take place?"
    )
    alternative_date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}),
        required=False,
        help_text="Optional alternative date if preferred date is unavailable"
    )
    preferred_cost_range = forms.ChoiceField(
        choices=[
            ('0-100', '$0-$100'),
            ('100-300', '$100-$300'),
            ('300-500', '$300-$500'),
            ('500+', '$500+')
        ],
        help_text="What is your budget range for the inspection?"
    )
    special_requirements = forms.CharField(
        widget=forms.Textarea,
        required=False,
        help_text="Any special requirements or areas of particular concern?"
    )

    class Meta:
        model = InspectionService
        fields = ['preferred_date', 'alternative_date', 'duration',
                  'preferred_cost_range', 'special_requirements']
        