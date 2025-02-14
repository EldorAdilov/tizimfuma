"""
URL configuration for myproject project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path
from myapp import views, description
from myapp import createxam


urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.login_view, name='login'),
    path('dashboard/', views.teacher_home, name='dashboard'),
    path('groups/', views.group_list_view, name='group_list'),  # Guruhlar ro'yxati
    path('groups/<int:group_id>/', views.group_detail_view, name='group_detail'),
    path('home/', views.home, name='home'),
    path('group_profile/', views.group_profile, name='group_profile'),
    path('profile/', views.profile_view, name='profile'),
    path('change-password/', views.change_password, name='change_password'),
    path('upload-video/', views.upload_video, name='upload_video'),
    path('select_group/', views.video_list, name='select_group'),
    path('student_list_table/', views.student_list_table, name='student_list_table'),
    path('video/<int:video_id>/', views.video_detail, name='video_detail'),
    path('toggle_student_status/<int:user_id>/', views.toggle_student_status, name='toggle_student_status'),
    path('student_list/', views.student_list, name='student_list'),
    path('payment_detail/<int:student_id>/', views.payment_detail, name='payment_detail'),
    path('download_payments_pdf/<int:student_id>/', views.download_payments_pdf, name='download_payments_pdf'),
    path('student_payments/', views.student_payments, name='student_payments'),
    path('create_exam/', createxam.create_exam, name='create_exam'),
    path('teacher_exams/', createxam.teacher_exams, name='teacher_exams'),
    path('student_exam_list/', createxam.student_exam_list, name='student_exam_list'),
    path('exam_evaluation/', createxam.exam_evaluation, name='exam_evaluation'),
    path('get-exams-by-group/', createxam.get_exams_by_group, name='get_exams_by_group'),
    path('exam-results/<int:exam_id>/<int:group_id>/', createxam.exam_results, name='exam_results'),
    path('exam-results-table/<int:exam_id>/', createxam.exam_results_table, name='exam_results_table'),
    path('all_exam_results/', createxam.all_exam_results, name='all_exam_results'),
    path('exams_list/<int:exam_id>/<int:group_id>/', createxam.exams_list, name='exams_list'),
    path('recommendations/', description.recommendations_view, name='recommendations_view'),

] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
