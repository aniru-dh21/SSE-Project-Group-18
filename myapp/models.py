from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db import transaction

class User(AbstractUser):
    age = models.IntegerField(null=True, blank=True)
    mobile = models.CharField(max_length=15)
    country_of_citizenship = models.CharField(max_length=100)
    language_preferred = models.CharField(max_length=50)
    covid_vaccination_status = models.CharField(
        max_length=20,
        choices=[
            ('vaccinated', 'Vaccinated'),
            ('not_vaccinated', 'Not Vaccinated'),
        ],
        default='not_vaccinated'
    )
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
class Service(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    photos = models.JSONField(default=list, blank=True)  # Store list of image URLs
    customized_options = models.TextField(blank=True)
    experiences = models.TextField(blank=True)
    feedback = models.JSONField(default=list, blank=True)
    renovation_plans = models.TextField(blank=True)
    provider = models.ForeignKey(User, on_delete=models.CASCADE, related_name='provided_services', null=True)
    is_available = models.BooleanField(default=True)
    service_area = models.CharField(max_length=200, blank=True)
    photo = models.ImageField(
        upload_to='service_photos/',
        null=True,
        blank=True,
        help_text="Upload a single photo for your service"
    )

    def __str__(self):
        return self.name

class Booking(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
        ('completed', 'Completed')
    ]
    
    PAYMENT_STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Completed', 'Completed'),
        ('Refunded', 'Refunded')
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    service = models.ForeignKey(Service, on_delete=models.CASCADE)
    booking_date = models.DateTimeField(auto_now_add=True)
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='Pending')
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    stripe_session_id = models.CharField(max_length=255, blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    notes = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.user.username} - {self.service.name} ({self.get_status_display()})"

class ServicePackage(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField()
    services = models.ManyToManyField(Service, through='PackageService', related_name='packages')
    base_price = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    discount_percentage = models.DecimalField(max_digits=5, decimal_places=2)
    is_customizable = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True)  
    updated_at = models.DateTimeField(auto_now=True, null=True)   

    @classmethod
    def generate_automated_packages(cls):
        """
        Generates automated packages by combining services in pairs and triplets
        with optimized discounts based on total value
        """
        from itertools import combinations
        
        # Get all active services
        services = Service.objects.filter(is_available=True)
        
        # Generate combinations of 2 and 3 services
        packages_created = 0
        for size in [2, 3]:
            service_combinations = combinations(services, size)
            
            for combo in service_combinations:
                # Calculate total price of services
                total_price = sum(service.price for service in combo)
                
                # Skip if package with these exact services already exists
                existing_package = cls.objects.filter(services__in=combo).distinct()
                if existing_package.count() == len(combo):
                    continue
                
                # Calculate discount based on total price
                if total_price < 100:
                    discount = 10
                elif total_price < 200:
                    discount = 15
                else:
                    discount = 20
                
                # Create package name and description
                service_names = [s.name for s in combo]
                package_name = f"{' & '.join(service_names)} Package"
                description = f"Save {discount}% on this combination of {len(combo)} services: {', '.join(service_names)}"
                
                # Create the package
                try:
                    with transaction.atomic():
                        package = cls.objects.create(
                            name=package_name,
                            description=description,
                            base_price=0.00,
                            discount_percentage=discount,
                            is_customizable=True
                        )
                        
                        # Add services to package
                        for service in combo:
                            PackageService.objects.create(
                                package=package,
                                service=service,
                                is_optional=False
                            )
                        
                        packages_created += 1
                except Exception as e:
                    print(f"Error creating package {package_name}: {str(e)}")
                    continue
                    
        return packages_created   

    class Meta:
        db_table = 'myapp_servicepackage'
        
    def get_original_price(self):
        """Calculate the original price before discount"""
        services_total = sum(service.price for service in self.services.all())
        return services_total + self.base_price
    
    def get_total_price(self):
        """Calculate the final price after discount"""
        original_price = self.get_original_price()
        discount = (original_price * self.discount_percentage) / 100
        return original_price - discount

    def __str__(self):
        return self.name

class PackageService(models.Model):
    package = models.ForeignKey(ServicePackage, on_delete=models.CASCADE, related_name='package_services')
    service = models.ForeignKey(Service, on_delete=models.CASCADE, related_name='package_services')
    is_optional = models.BooleanField(default=False)
    individual_discount = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        default=0.00,
        help_text="Individual discount percentage for this service within the package"
    )
    class Meta:
        db_table = 'myapp_packageservice'
        unique_together = ['package', 'service']
        
    def __str__(self):
        return f"{self.package.name} - {self.service.name}"
    
class InspectionService(models.Model):
    DURATION_CHOICES = [
        ('few_hours', 'Few Hours'),
        ('one_day', 'One Day'),
        ('several_days', 'Several Days'),
    ]

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    preferred_date = models.DateField()
    alternative_date = models.DateField(null=True, blank=True)
    duration = models.CharField(max_length=20, choices=DURATION_CHOICES)
    preferred_cost_range = models.CharField(max_length=50)
    special_requirements = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)

    inspector = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='assigned_inspections'
    )

    def __str__(self):
        return f"Inspection for {self.user.username} on (self.preferred_data)"

class InspectionFindings(models.Model):
    URGENCY_CHOICES = [
        ('critical', 'Critical - Immediate Action Required'),
        ('high', 'High Priority'),
        ('medium', 'Medium Priority'),
        ('low', 'Low Priority'),
    ]

    inspection = models.ForeignKey(InspectionService, on_delete=models.CASCADE, related_name='findings')
    issue_description = models.TextField()
    location_in_house = models.CharField(max_length=100)
    urgency_level = models.CharField(max_length=20, choices=URGENCY_CHOICES)
    estimated_cost = models.DecimalField(max_digits=10, decimal_places=2)
    recommended_cost = models.ForeignKey(Service, on_delete=models.SET_NULL, null=True, blank=True)
    recommended_services = models.ManyToManyField(
        Service, 
        related_name='recommended_in_findings',
        blank=True
    )
    provider_feedback = models.TextField(
        blank=True,
        help_text="Service provider's feedback and recommendations"
    )
    recommendation_priority = models.CharField(
        max_length=20,
        choices=[
            ('immediate', 'Immediate Action Recommended'),
            ('soon', 'Address Within 3-6 Months'),
            ('future', 'Future Consideration'),
            ('optional', 'Optional Improvement')
        ],
        default='soon'
    )
    estimated_timeline = models.CharField(
        max_length=100,
        blank=True,
        help_text="Estimated timeline for recommended services"
    )

    def __str__(self):
        return f"{self.get_urgency_level_display()} issue at {self.location_in_house}"
    