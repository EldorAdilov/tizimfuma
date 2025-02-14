from sklearn.neighbors import KNeighborsRegressor
import numpy as np
import matplotlib.pyplot as plt
import io
import base64
from django.shortcuts import render, get_object_or_404
from myapp.models import Group, ExamResult, Profile


def recommendations_view(request):
    user_profile = Profile.objects.get(user=request.user)
    groups = Group.objects.filter(students=user_profile)

    group_id = request.GET.get('group_id')
    suggestion = None
    selected_group_name = None
    chart_url = None
    group_chart_url = None

    if group_id:
        group = get_object_or_404(Group, id=group_id)
        selected_group_name = group.name

        results = ExamResult.objects.filter(
            exam__group__id=group_id, student=user_profile
        ).order_by('exam__exam_date')

        group_results = ExamResult.objects.filter(exam__group__id=group_id).order_by('-exam__exam_date')

        if results.count() < 2:
            suggestion = "Imtihon natijalaringiz hali yetarli emas. Iltimos, yangi imtihonlarga qatnashing."
        else:
            latest_score = results.last().score
            previous_scores = [result.score for result in list(results)[:-1]]
            previous_avg = sum(previous_scores) / len(previous_scores) if previous_scores else latest_score

            if latest_score > previous_avg:
                suggestion = (
                    f"So‘nggi natijangiz ({latest_score}) oldingi o‘rtacha ({previous_avg:.1f}) natijangizdan yuqori! "
                    "O‘zlashtirishingiz yaxshilanmoqda. Davom eting!"
                )
            elif latest_score < previous_avg:
                suggestion = (
                    f"So‘nggi natijangiz ({latest_score}) oldingi o‘rtacha ({previous_avg:.1f}) natijangizdan past. "
                    "Mavzularni qayta ko‘rib chiqishingizni tavsiya qilamiz."
                )
            else:
                suggestion = (
                    f"So‘nggi natijangiz ({latest_score}) oldingi o‘rtacha ({previous_avg:.1f}) natijangizga teng. "
                    "O‘zlashtirishni davom ettiring va yuqori natijalarga erishishga harakat qiling."
                )

            group_scores = [(result.student.id, result.score) for result in group_results]

            if len(group_scores) >= 3:
                group_scores = np.array(group_scores, dtype=np.float64)
                knn = KNeighborsRegressor(n_neighbors=3)
                student_ids = group_scores[:, 0].reshape(-1, 1)
                scores = group_scores[:, 1]

                knn.fit(student_ids, scores)
                similar_scores = knn.predict([[latest_score]])

                avg_group_score = group_scores[:, 1].mean()
                if latest_score > avg_group_score:
                    suggestion += (
                        " Guruhingizdagi o'quvchilardan o'zlashtirishingiz yaxshi. Agar shu tarzda ketsangiz, muvaffaqiyatlaringiz yanada oshadi!"
                    )
                else:
                    suggestion += (
                        " Guruhingizdagi o'quvchilarning o'rtacha natijasidan biroz pastroqdasiz. Harakatni kuchaytirishingiz kerak!"
                    )

            # Grafik 1: Talabaning individual natijalari
            fig, ax = plt.subplots(figsize=(8, 6))
            previous_scores.append(latest_score)
            ax.plot(range(1, len(previous_scores) + 1), previous_scores, marker='o', color='#1D2D5B', label='Natijalar')
            ax.set_title("Sizning imtihon natijalaringiz")
            ax.set_xlabel("Imtihonlar")
            ax.set_ylabel("Natija")
            ax.legend()

            buf = io.BytesIO()
            plt.savefig(buf, format='png')
            buf.seek(0)
            chart_url = base64.b64encode(buf.read()).decode('utf-8')
            buf.close()

            # **Grafik 2: Guruhdagi barcha talabalarning eng so‘nggi imtihon natijalari**
            last_exam_results = {}
            for result in group_results:
                if result.student.id not in last_exam_results:
                    last_exam_results[result.student.id] = result.score  # Faqat eng oxirgi natija olinadi

            sorted_students = sorted(last_exam_results.keys())  # Talabalarni ID bo‘yicha saralash
            sorted_scores = [last_exam_results[student_id] for student_id in sorted_students]

            fig, ax = plt.subplots(figsize=(8, 6))
            ax.bar(range(len(sorted_students)), sorted_scores, color='#1D2D5B', label='Talabalar natijalari')

            # Foydalanuvchining natijasi
            if user_profile.id in last_exam_results:
                user_index = sorted_students.index(user_profile.id)
                ax.scatter(user_index, last_exam_results[user_profile.id], color='red', s=100, label="Sizning natijangiz")

            ax.set_title("Tanlagan guruhingizdagi barcha talabalarning eng so‘nggi imtihon natijalari")
            ax.set_xlabel("Talabalar")
            ax.set_ylabel("Natija")
            ax.legend()

            buf = io.BytesIO()
            plt.savefig(buf, format='png')
            buf.seek(0)
            group_chart_url = base64.b64encode(buf.read()).decode('utf-8')
            buf.close()

    return render(request, 'recommendations.html', {
        'user_profile': user_profile,
        'groups': groups,
        'suggestion': suggestion,
        'selected_group_name': selected_group_name,
        'chart_url': chart_url,
        'group_chart_url': group_chart_url,
    })
