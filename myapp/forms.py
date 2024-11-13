from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import User, ServicePackage, PackageService, Service, InspectionService, InspectionFindings
from django.core.validators import RegexValidator
from django.core.exceptions import ValidationError

class RegistrationForm(UserCreationForm):
    first_name = forms.CharField(
        max_length=150,
        required=True,
    )
    
    last_name = forms.CharField(
        max_length=150,
        required=True,
    )

    username = forms.CharField(
        min_length=4,
        max_length=150,
        validators=[
            RegexValidator(
                regex='^[a-zA-Z0-9_]*$',
                message='Username must contain only letters, numbers, and underscores',
                code='invalid_username'
            ),
        ],
        help_text='Only letters, numbers, and underscores allowed.'
    )

    age = forms.IntegerField(
        required=True,
    )

    mobile = forms.CharField(
        validators=[
            RegexValidator(
                regex=r'^\+?1?\d{9,15}$',
                message="Phone number must be entered in the format: '+999999999'."
            )
        ],
        required=True,
    )

    country_of_citizenship = forms.CharField(
        max_length=100,
        required=True,
    )

    language_preferred = forms.CharField(
        max_length=50,
        required=True,
    )

    COVID_VACCINATION_CHOICES = [
        ('vaccinated', 'Vaccinated'),
        ('not_vaccinated', 'Not Vaccinated'),
    ]
    covid_vaccination_status = forms.ChoiceField(
        choices=COVID_VACCINATION_CHOICES,
        widget=forms.RadioSelect,
        required=True,
    )

    is_service_provider = forms.BooleanField(
        required=False,
        label='Register as Service Provider'
    )

    trade = forms.CharField(
        max_length=50,
        required=False,
    )

    profession = forms.CharField(
        max_length=50,
        required=False,
    )

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

    def clean(self):
        cleaned_data = super().clean()
        is_service_provider = cleaned_data.get('is_service_provider')
        trade = cleaned_data.get('trade')
        profession = cleaned_data.get('profession')

        if is_service_provider:
            if not trade:
                self.add_error('trade', 'Trade is required for service providers')
            if not profession:
                self.add_error('profession', 'Profession is required for service providers')

        return cleaned_data

    class Meta:
        model = User
        fields = [
            'first_name',
            'last_name',
            'username',
            'password1',
            'password2',
            'age',
            'mobile',
            'country_of_citizenship',
            'language_preferred',
            'covid_vaccination_status',
            'is_service_provider',
            'trade',
            'profession',
        ]

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
        
class InspectionResultForm(forms.ModelForm):
    class Meta:
        model = InspectionFindings
        fields = ['issue_description', 'location_in_house', 'urgency_level', 
                 'estimated_cost', 'recommended_cost']
        widgets = {
            'issue_description': forms.Textarea(attrs={'rows': 4}),
            'estimated_cost': forms.NumberInput(attrs={'step': '0.01'}),
        }

class InspectionRecommendationForm(forms.ModelForm):
    class Meta:
        model = InspectionFindings
        fields = [
            'issue_description', 
            'location_in_house', 
            'urgency_level',
            'estimated_cost',
            'recommended_services',
            'provider_feedback',
            'recommendation_priority',
            'estimated_timeline'
        ]
        widgets = {
            'issue_description': forms.Textarea(attrs={'rows': 4}),
            'provider_feedback': forms.Textarea(attrs={'rows': 4}),
            'recommended_services': forms.CheckboxSelectMultiple(),
            'estimated_cost': forms.NumberInput(attrs={'step': '0.01'})
        }

class ServiceManagementForm(forms.ModelForm):
    class Meta:
        model = Service
        fields = ['name', 'description', 'price', 'service_area', 'is_available', 'photo']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
            'price': forms.NumberInput(attrs={'step': '0.01'}),
        }

    def clean_photo(self):
        photo = self.cleaned_data.get('photo')
        if photo:
            # Validate file size (limit to 5MB)
            if photo.size > 5 * 1024 * 1024:
                raise forms.ValidationError("Image size should not exceed 5MB")
            
            # Validate file type
            allowed_types = ['image/jpeg', 'image/png', 'image/jpg']
            if photo.content_type not in allowed_types:
                raise forms.ValidationError("Only JPEG and PNG files are allowed")
        
        return photo