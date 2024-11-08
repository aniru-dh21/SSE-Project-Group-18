from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import User
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
