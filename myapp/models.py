from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    age = models.IntegerField(null=True, blank=True)
    mobile = models.CharField(max_length=15)
    country_of_citizenship = models.CharField(max_length=100)
    language_preferred = models.CharField(max_length=50)
    covid_vaccination_status = models.BooleanField(default=False)
    credit_card = models.CharField(max_length=20)
    trade = models.CharField(max_length=50)
    profession = models.CharField(max_length=50)
    is_service_provider = models.BooleanField(default=False)

    # Adding related_name to avoid clashes with default auth.User model
    groups = models.ManyToManyField(
        'auth.Group',
        related_name='custom_user_set',  # Custom related name to avoid clash
        blank=True,
        help_text='The groups this user belongs to.',
        verbose_name='groups'
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        related_name='custom_user_permissions_set',  # Custom related name to avoid clash
        blank=True,
        help_text='Specific permissions for this user.',
        verbose_name='user permissions'
    )

# models.py
from django.db import models

class Service(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    photos = models.JSONField(default=list, blank=True)  # Store list of image URLs
    customized_options = models.TextField(blank=True)
    experiences = models.TextField(blank=True)
    feedback = models.JSONField(default=list, blank=True)
    renovation_plans = models.TextField(blank=True)

    def __str__(self):
        return self.name


class Booking(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    service = models.ForeignKey(Service, on_delete=models.CASCADE)
    booking_date = models.DateTimeField(auto_now_add=True)
    payment_status = models.CharField(max_length=20, choices=[('Pending', 'Pending'), ('Completed', 'Completed')], default='Pending')
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    stripe_session_id = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return f"{self.user.username} - {self.service.name}"

