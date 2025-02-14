from datetime import datetime

from django.db.models import Prefetch
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.utils import timezone

from myapp.models import Group, Exam, Profile, ExamResult
from django.db.models import OuterRef, Subquery

from myapp.views import is_teacher


@user_passes_test(is_teacher)
def create_exam(request):
    if request.method == 'POST':
        group_id = request.POST.get('group')  # Guruh ID
        question_count = request.POST.get('question_count')  # Savollar soni
        max_score = request.POST.get('max_score')  # Maksimal ball
        exam_date = request.POST.get('exam_date')  # Imtihon sanasi
        teacher_name = request.POST.get('teacher_name')  # Ism familiya

        # Sana validatsiyasi
        try:
            # Sana formatini tekshirish
            exam_date = datetime.strptime(exam_date, "%Y-%m-%dT%H:%M")
        except ValueError:
            messages.error(request, "Sana hato formatda kiritildi. ", extra_tags='exam_message')
            return redirect('create_exam')

        # Guruhni olish
        group = Group.objects.filter(id=group_id).first()
        if not group:
            messages.error(request, "Bunday guruh topilmadi", extra_tags='exam_message')
            return redirect('create_exam')

        # Yangi imtihon yaratish
        Exam.objects.create(
            group=group,
            question_count=question_count,
            max_score=max_score,
            teacher_name=teacher_name,
            exam_date=exam_date,
            created_by=request.user
        )

        messages.success(request, "Imtihon muvaffaqiyatli yaratildi!", extra_tags='exam_message')
        return redirect('create_exam')

    groups = Group.objects.all()  # Barcha guruhlarni olamiz
    return render(request, 'create_exam.html', {'groups': groups})


@user_passes_test(is_teacher)
def teacher_exams(request):
    # Faqat o'qituvchi tomonidan yaratilgan imtihonlarni olish
    exams = Exam.objects.filter(created_by=request.user).order_by('-created_at')
    return render(request, 'teacher_exams.html', {'exams': exams})


@login_required
def student_exam_list(request):
    user_profile = Profile.objects.get(user=request.user)
    user_groups = Group.objects.filter(students=user_profile)

    # Har bir imtihon uchun o'quvchining natijasini olish
    results_subquery = ExamResult.objects.filter(
        exam=OuterRef('pk'),
        student=user_profile
    ).values('score')[:1]

    exams = Exam.objects.filter(group__in=user_groups).annotate(
        student_score=Subquery(results_subquery)
    ).order_by('group__name', '-exam_date')

    # Imtihonlarni guruhlash
    grouped_exams = {}
    for exam in exams:
        group_name = exam.group.name
        if group_name not in grouped_exams:
            grouped_exams[group_name] = []
        grouped_exams[group_name].append(exam)

    return render(request, 'student_exam_list.html', {
        'grouped_exams': grouped_exams,
        'user_profile': user_profile
    })


@user_passes_test(is_teacher)
def get_exams_by_group(request):
    group_id = request.GET.get('group_id')  # Guruh ID so'rovdan olinadi
    exams = Exam.objects.filter(group_id=group_id)
    exam_data = [
        {'id': exam.id, 'exam_date': exam.exam_date.strftime('%Y-%m-%d %H:%M')}
        for exam in exams
    ]
    return JsonResponse(exam_data, safe=False)


@user_passes_test(is_teacher)
def exam_evaluation(request):
    groups = Group.objects.all()  # Barcha guruhlar
    if request.method == "POST":
        group_id = request.POST.get('group_id')  # Tanlangan guruh
        exam_id = request.POST.get('exam_id')  # Tanlangan imtihon

        # Tanlangan guruh va imtihonga oid ma'lumotlar
        group = Group.objects.get(id=group_id)
        exam = Exam.objects.get(id=exam_id)

        return redirect('exam_results', exam_id=exam.id, group_id=group.id)

    return render(request, 'exam_evaluation.html', {
        'groups': groups,
    })


@user_passes_test(is_teacher)
def exam_results(request, exam_id, group_id):
    # Tanlangan imtihon va guruhni olish
    exam = get_object_or_404(Exam, id=exam_id)
    group = get_object_or_404(Group, id=group_id)

    search_query = request.GET.get('search', '')

    # Guruhdagi o'quvchilarni olish
    students = Profile.objects.filter(
        profile_group=group,
        user__is_staff=False,
        user__is_superuser=False,
        user__is_active=True
    )

    if search_query:
        students = students.filter(
            familiya__icontains=search_query
        ) | students.filter(
            ismi__icontains=search_query
        )

    students = students.prefetch_related(
        Prefetch(
            'exam_results',
            queryset=ExamResult.objects.filter(exam=exam),
            to_attr='results'
        )
    )

    if request.method == "POST":
        # Barcha natijalarni bir martalik so‘rov bilan olish
        existing_results = {r.student_id: r for r in ExamResult.objects.filter(exam=exam)}

        for student in students:
            score = request.POST.get(f'student_{student.id}')  # Talabaning natijasi
            if score:
                score = int(score)  # Ballni integer ko‘rinishga keltirish
                if student.id in existing_results:
                    existing_results[student.id].score = score
                    existing_results[student.id].save()
                else:
                    ExamResult.objects.create(exam=exam, student=student, score=score)

        return redirect('exam_results_table', exam_id=exam.id)

    return render(request, 'exam_results.html', {
        'exam': exam,
        'group': group,
        'students': students,
        'search_query': search_query
    })


@user_passes_test(is_teacher)
def exam_results_table(request, exam_id):
    # Tanlangan imtihonni olish
    exam = get_object_or_404(Exam, id=exam_id)

    # Qidiruv so‘rovini olish
    search_query = request.GET.get('search', '')

    # Natijalarni olish (faqat aktiv o‘quvchilar)
    results = ExamResult.objects.filter(
        exam=exam,
        student__user__is_active=True
    ).select_related('student')

    # Qidiruv (ismi yoki familiya bo‘yicha)
    if search_query:
        results = results.filter(
            student__familiya__icontains=search_query
        ) | results.filter(
            student__ismi__icontains=search_query
        )

    return render(request, 'exam_results_table.html', {
        'exam': exam,
        'results': results,
        'search_query': search_query  # Qidiruv shablonga yuboriladi
    })


@user_passes_test(is_teacher)
def all_exam_results(request):
    groups = Group.objects.all()  # Barcha guruhlar
    if request.method == "POST":
        group_id = request.POST.get('group_id')  # Tanlangan guruh
        exam_id = request.POST.get('exam_id')  # Tanlangan imtihon

        # Tanlangan guruh va imtihonga oid ma'lumotlar
        group = Group.objects.get(id=group_id)
        exam = Exam.objects.get(id=exam_id)

        return redirect('exams_list', exam_id=exam.id, group_id=group.id)

    return render(request, 'all_exam_results.html', {
        'groups': groups,
    })


@user_passes_test(is_teacher)
def exams_list(request, exam_id, group_id):
    exam = get_object_or_404(Exam, id=exam_id)
    group = get_object_or_404(Group, id=group_id)

    search_query = request.GET.get('search', '').strip()

    # O'quvchilarning natijalarini olish
    students = Profile.objects.filter(
        profile_group=group,
        user__is_staff=False,
        user__is_superuser=False,
        user__is_active=True
    )

    if search_query:
        students = students.filter(
            familiya__icontains=search_query
        ) | students.filter(
            ismi__icontains=search_query
        )

    students = students.prefetch_related(
        Prefetch(
            'exam_results',
            queryset=ExamResult.objects.filter(exam=exam).only('score'),
            to_attr='results'
        )
    )

    # Natijalar shablonda ko'rsatiladi
    return render(request, 'exams_list.html', {
        'exam': exam,
        'group': group,
        'students': students,
        'search_query': search_query,
    })
