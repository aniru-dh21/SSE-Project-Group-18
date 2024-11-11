from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),  # Add this line to map the empty path
    path('register/', views.register, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('service_list/', views.service_list, name='service_list'),
    path('service/<int:id>/', views.service_detail, name='service_detail'),
    path('book_service/<int:pk>/', views.book_service, name='book_service'),
    path('recommend/', views.recommend_service, name='recommend_service'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('edit_profile/', views.edit_profile, name='edit_profile'),
    path('packages/', views.package_list, name='package_list'),
    path('packages/<int:pk>/', views.package_detail, name='package_detail'),
    path('packages/<int:pk>/book/', views.book_package, name='book_package'),
    path('packages/create/', views.create_package, name='create_package'),
    path('inspection/book/', views.book_inspection, name='book_inspection'),
    path('inspection/<int:inspection_id>/results/', views.view_inspection_results, name='inspection_results'),
    path('inspection/success/', views.inspection_success, name='inspection_success'),
    path('manage-services/', views.manage_services, name='manage_services'),
    path('booking/<int:booking_id>/update-status/', views.update_booking_status, name='update_booking_status'),
    path('booking/<int:booking_id>/add-note/', views.add_booking_note, name='add_booking_note'),
    path('inspections/available/', views.available_inspections, name='available_inspections'),
    path('inspections/<int:inspection_id>/accept/', views.accept_inspection, name='accept_inspection'),
    path('inspections/<int:inspection_id>/submit-results/', views.submit_inspection_results, name='submit_inspection_results'),
    path('success/', views.success_view, name='success'),
    path('cancel/', views.cancel_view, name='cancel'),
    path('stripe_webhook/', views.stripe_webhook, name='stripe_webhook'),
]
