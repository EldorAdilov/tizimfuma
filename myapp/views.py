import os
from io import BytesIO
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from django.db.models import Q
from django.http import  HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test
from myapp.models import Profile, Group, Video, Payments, ProfileGroup, CustomUser
from myproject import settings


def login_view(request):
    if request.method == 'POST':
        user = authenticate(request, username=request.POST.get('username'), password=request.POST.get('password'))
        if user:
            login(request, user)
            return redirect('dashboard' if user.is_superuser else 'home')
        messages.error(request, "Parol yoki login noto'g'ri kiritildi.", extra_tags='login_message')
    return render(request, 'login.html')


@login_required
def logout_view(request):
    logout(request)
    return redirect('login')


@login_required
def profile_view(request):
    profile, created = Profile.objects.get_or_create(user=request.user)
    groups = Group.objects.filter(students=profile)

    if request.method == 'POST':  # Faqat profil ma'lumotlarini yangilash
        profile.familiya = request.POST.get('familiya', '').strip()
        profile.ismi = request.POST.get('ismi', '').strip()
        profile.telefon = request.POST.get('telefon', '').strip()

        if request.FILES.get('rasm'):
            if profile.rasm:
                old_rasm_path = os.path.join(settings.MEDIA_ROOT, str(profile.rasm))
                if os.path.exists(old_rasm_path):
                    try:
                        os.remove(old_rasm_path)
                    except Exception as e:
                        messages.warning(request, f"Eski rasm o‘chirilmadi: {e}")
            profile.rasm = request.FILES.get('rasm')

        if not profile.familiya or not profile.ismi:
            messages.error(request, "Ism va familiya maydonlari to‘ldirilishi shart!")
        else:
            profile.save()
            messages.success(request, "Profil muvaffaqiyatli yangilandi!")

        return redirect('profile')
    return render(request, 'profile.html', {'profile': profile, 'groups': groups})


def is_teacher(user):
    return user.is_authenticated and (user.is_superuser or user.is_teacher)


@user_passes_test(is_teacher)
def teacher_home(request):
    user = request.user
    return render(request, 'dashboard.html', {'user': user})


@login_required
def change_password(request):
    if request.method == 'POST':
        current_password, new_password, confirm_password = (
            request.POST.get('current_password'),
            request.POST.get('new_password'),
            request.POST.get('confirm_password')
        )

        if not request.user.check_password(current_password):
            messages.error(request, "Joriy parol noto‘g‘ri.")
        elif new_password != confirm_password:
            messages.error(request, "Yangi parol va tasdiqlovchi parol mos emas.")
        elif len(new_password) < 8:
            messages.error(request, "Parol uzunligi kamida 8 ta belgidan iborat bo‘lishi kerak.")
        else:
            request.user.set_password(new_password)
            request.user.save()
            logout(request)
            messages.success(request, "Parol o‘zgartirildi. Yangi parol bilan tizimga kiring.")
            return redirect('login')

    return redirect('profile')


@user_passes_test(is_teacher)
def group_list_view(request):
    query = request.GET.get('q', '')
    groups = Group.objects.filter(
        Q(name__icontains=query) | Q(information__icontains=query)) if query else Group.objects.all()

    group_data = [
        {'group': group, 'student_count': group.students.filter(
            user__is_active=True,
            user__is_staff=False,
            user__is_superuser=False
        ).count()}
        for group in groups
    ]

    return render(request, 'group_list.html', {'group_data': group_data})


@user_passes_test(is_teacher)
def group_detail_view(request, group_id):
    group = get_object_or_404(Group, id=group_id)
    profile_groups = ProfileGroup.objects.filter(group=group, profile__user__is_active=True).select_related('profile')

    search_query = request.GET.get('q', '')
    if search_query:
        profile_groups = profile_groups.filter(
            Q(profile__ismi__icontains=search_query) | Q(profile__familiya__icontains=search_query)
        )
    return render(request, 'group_detail.html', {'group': group, 'profile_groups': profile_groups})


@login_required
def home(request):
    profile, created = Profile.objects.get_or_create(user=request.user)
    return render(request, 'home.html', {'profile': profile})


@login_required
def group_profile(request):
    profile = Profile.objects.get(user=request.user)
    profile_groups = ProfileGroup.objects.filter(profile=profile)
    return render(request, 'group_profile.html', {'profile': profile, 'profile_groups': profile_groups})


@user_passes_test(is_teacher)
def upload_video(request):
    if request.method == 'POST':
        title = request.POST.get('title')
        youtube_link = request.POST.get('youtube_link')
        is_general = request.POST.get('is_general') == 'on'  # Checkbox uchun
        group_ids = request.POST.getlist('groups')  # Tanlangan guruhlar

        # Tekshirishlar
        if not title or not youtube_link:
            messages.error(request, "Iltimos, sarlavha va YouTube linkini kiriting!")
            return redirect('upload_video')

        # Agar "Barcha guruhlar uchun" tanlangan bo'lsa, guruhlar bo'sh bo'lishi kerak
        if is_general and group_ids:
            messages.error(request, "'Barcha guruhlar uchun' ni tanlangan bo'lsa, guruh tanlanmasligi kerak!")
            return redirect('upload_video')

        # Agar "Barcha guruhlar uchun" tanlanmagan bo'lsa, kamida bitta guruh tanlanishi kerak
        if not is_general and not group_ids:
            messages.error(request, "Iltimos, 'Barcha guruhlar uchun' ni tanlang yoki kamida bitta guruh tanlang!")
            return redirect('upload_video')

        # Video yaratish
        try:
            video = Video.objects.create(
                title=title,
                youtube_link=youtube_link,
                is_general=is_general
            )

            # Tanlangan guruhlarni videoga qo'shish
            if group_ids:
                groups = Group.objects.filter(id__in=group_ids)
                video.groups.set(groups)

            messages.success(request, "Video muvaffaqiyatli yuklandi!")
            return redirect('upload_video')

        except Exception as e:
            messages.error(request, f"Xato yuz berdi: {e}")
            return redirect('upload_video')

    # Guruhlarni olish (formada tanlash uchun)
    groups = Group.objects.all()
    return render(request, 'upload_video.html', {'groups': groups})


def extract_youtube_id(youtube_link):
    """
    YouTube havolasidan video ID ni ajratib olish.
    """
    import re

    if 'youtu.be' in youtube_link:
        return youtube_link.split('/')[-1].split('?')[0]

    elif 'youtube.com' in youtube_link:
        match = re.search(r'(?<=v=)[^&]+', youtube_link)
        if match:
            return match.group(0)
        match = re.search(r'(?<=be/)[^&]+', youtube_link)
        if match:
            return match.group(0)

    return None


@login_required
def video_list(request):
    profile = Profile.objects.get(user=request.user)
    profile_groups = ProfileGroup.objects.filter(profile__user=request.user)
    groups = [pg.group for pg in profile_groups]

    selected_group = request.GET.get('group', '')

    if selected_group == 'all' or not selected_group:
        videos = Video.objects.filter(is_general=True)
    else:
        videos = Video.objects.filter(groups__id=selected_group)

    videos = videos.distinct()

    for video in videos:
        video.youtube_id = extract_youtube_id(video.youtube_link)

    return render(request, 'select_group.html', {'videos': videos, 'groups': groups, 'profile': profile})


@login_required
def video_detail(request, video_id):
    video = get_object_or_404(Video, id=video_id)
    video.youtube_id = extract_youtube_id(video.youtube_link)

    return render(request, 'video_detail.html', {'video': video})


@user_passes_test(is_teacher)
def student_list(request):
    search_query = request.GET.get('search', '')

    students = Profile.objects.filter(user__is_teacher=False, user__is_superuser=False)

    if search_query:
        students = students.filter(
            familiya__icontains=search_query
        ) | students.filter(
            ismi__icontains=search_query
        )
    return render(request, 'student_list.html', {'students': students, 'search_query': search_query})


@user_passes_test(is_teacher)
def student_list_table(request):
    search_query = request.GET.get('search', '')
    students = Profile.objects.filter(user__is_teacher=False, user__is_superuser=False)

    if search_query:
        students = students.filter(familiya__icontains=search_query) | students.filter(ismi__icontains=search_query)
    return render(request, 'student_list_table.html', {'students': students, 'search_query': search_query})


@user_passes_test(is_teacher)
def toggle_student_status(request, user_id):

    student = get_object_or_404(CustomUser, id=user_id)

    student.is_active = not student.is_active
    student.save()

    if student.is_active:
        messages.success(request,
                         f"{student.profile.familiya} {student.profile.ismi} o'quvchi aktiv holatga o‘tkazildi.",
                         extra_tags="student_list_table")
    else:
        messages.warning(request,
                         f"{student.profile.familiya} {student.profile.ismi} o'quvchi deaktiv qilindi.",
                         extra_tags="student_list_table")

    return redirect('student_list_table')


@user_passes_test(is_teacher)
def payment_detail(request, student_id):
    student = get_object_or_404(Profile, id=student_id)  # Tanlangan talaba
    payments = Payments.objects.filter(names_ful=student)  # Talabaga tegishli to'lovlar

    if request.method == 'POST':
        # Yangi to'lovni kiritish
        month = request.POST.get('month')
        money_summ = request.POST.get('money_summ')
        amount_paid = request.POST.get('amount_paid')
        payment_date = request.POST.get('payment_date')

        if not month or not money_summ or not amount_paid or not payment_date:
            messages.error(request, 'Barcha maydonlarni to\'ldiring: Oy, To\'lanadigan summa, To\'langan summa, va To\'lov sanasi.')
        else:

            payment = Payments(
                names_ful=student,
                month=month,
                money_summ=money_summ,
                amount_paid=amount_paid,
                payment_date=payment_date,
            )
            payment.save()
            messages.success(request, 'To\'lov muvaffaqiyatli saqlandi.', extra_tags='payment_message')
            return redirect('payment_detail', student_id=student.id)

    return render(request, 'payment_detail.html', {'student': student, 'payments': payments})


@user_passes_test(is_teacher)
def download_payments_pdf(request, student_id):
    # Talabani va uning to'lovlarini olish
    student = get_object_or_404(Profile, id=student_id)
    payments = Payments.objects.filter(names_ful=student)

    # To'lovlar bo'sh bo'lsa, xabar qaytarish
    if not payments.exists():
        return HttpResponse("To'lovlar ma\'lumotlari topilmadi.", content_type='text/plain')

    # PDF faylni yaratish uchun bufer
    buffer = BytesIO()
    pdf = SimpleDocTemplate(buffer, pagesize=letter)

    # Sarlavha matni
    styles = getSampleStyleSheet()
    title = f"{student.ismi} {student.familiya} - To\'lov Ro'yxati"
    title_paragraph = Paragraph(title, styles['Title'])

    # Jadval uchun sarlavha va ma'lumotlar
    data = [
        ["No", "Oy", "To\'lanadigan summa", "To\'langan summa", "To\'lov sanasi"]
    ]

    for idx, payment in enumerate(payments, start=1):
        data.append([
            idx,
            payment.month,
            f"{payment.money_summ} so\'m",
            f"{payment.amount_paid} so\'m",
            payment.payment_date.strftime('%d-%m-%Y') if payment.payment_date else "—",
        ])

    # Jadvalni yaratish
    table = Table(data, colWidths=[30, 100, 150, 150, 150])

    # Jadval stilini o'rnatish
    style = TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightblue),  # Sarlavha qatori foni
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),  # Sarlavha matni rangi
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),  # Markazlashgan matn
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),  # Sarlavha uchun shrift
        ('FONTSIZE', (0, 0), (-1, 0), 12),  # Sarlavha shrift o'lchami
        ('BOTTOMPADDING', (0, 0), (-1, 0), 10),  # Sarlavha pastki bo'shligi
        ('BACKGROUND', (0, 1), (-1, -1), colors.whitesmoke),  # Jadval satrlari foni
        ('GRID', (0, 0), (-1, -1), 1, colors.black),  # Chegara chiziqlari
    ])
    table.setStyle(style)

    # PDF elementlarini yig'ish
    elements = [title_paragraph, table]

    # PDFni yaratish
    pdf.build(elements)

    # PDFni HTTP javobga qaytarish
    buffer.seek(0)
    response = HttpResponse(buffer, content_type='application/pdf')
    filename = f"{student.ismi}_{student.familiya}_tolovlar.pdf"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


@login_required
def student_payments(request):
    # Talaba va uning to‘lov ma'lumotlarini olish
    student = Profile.objects.get(user=request.user)
    payments = Payments.objects.filter(names_ful=student)

    return render(request, 'student_payments.html', {
        'student': student,
        'payments': payments,
    })

