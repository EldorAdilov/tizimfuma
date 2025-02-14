from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin
from myapp.models import Profile, Video, Group, Payments, Exam, ExamResult, ProfileGroup
from django.urls import reverse
from django.utils.html import format_html
CustomUser = get_user_model()


# Profile modelini CustomUser admin panelida inline qilish
class ProfileInline(admin.StackedInline):
    model = Profile
    can_delete = False
    verbose_name_plural = 'Profile'


class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'is_superuser', 'is_staff', 'is_active')
    search_fields = ('username', 'email')
    ordering = ('username',)
    readonly_fields = ('date_joined',)
    inlines = [ProfileInline]  # Profile modelini CustomUser admin paneliga inline tarzda qo'shamiz


@admin.register(Video)
class VideoAdmin(admin.ModelAdmin):
    list_display = ('title', 'youtube_link', 'is_general', 'created_time')
    list_filter = ('is_general', 'created_time')
    search_fields = ('title', 'youtube_link')
    filter_horizontal = ('groups',)  # Guruhlarni tanlash uchun filter


# Group modelining admin interfeysi
@admin.register(Group)
class GuruhAdmin(admin.ModelAdmin):
    list_display = ('name', 'created_time')
    search_fields = ('name',)
    filter_horizontal = ('students',)  # Guruhdagi talabalarni qo'shish/olib tashlash
    ordering = ('-created_time',)

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        group = form.instance

        # Guruhni yangilashda o'quvchilarni ProfileGroup modeliga qo'shish
        ProfileGroup.objects.filter(group=group).exclude(profile__in=group.students.all()).delete()
        for student in group.students.all():
            ProfileGroup.objects.get_or_create(profile=student, group=group)


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'familiya', 'ismi', 'telefon', 'added_time')
    search_fields = ('familiya', 'ismi', 'telefon')
    list_filter = ('added_time',)


class PaymentsAdmin(admin.ModelAdmin):
    list_display = ('names_ful', 'month', 'money_summ', 'amount_paid', 'payment_date', 'view_payments_link')
    list_filter = ('month',)  # Filtrlar
    search_fields = ('names_ful__ismi', 'names_ful__familiya')  # Qidiruv
    date_hierarchy = 'payment_date'

    def view_payments_link(self, obj):
        """
        Talaba to'lovlarini ko'rish uchun admin sahifasiga havola
        """
        url = reverse('admin:myapp_payments_changelist') + f"?names_ful__id__exact={obj.names_ful.id}"
        return format_html('<a href="{}">Toʻlovlar</a>', url)

    view_payments_link.short_description = "Toʻlovlarni koʻrish"

# Modelni ro'yxatdan o'tkazish
admin.site.register(Payments, PaymentsAdmin)


@admin.register(Exam)
class ExamAdmin(admin.ModelAdmin):
    list_display = ('group', 'exam_date', 'question_count', 'max_score', 'created_by')
    list_filter = ('exam_date', 'group')
    search_fields = ('group__name',)
    ordering = ('-exam_date',)
    fields = ('group', 'question_count', 'max_score', 'exam_date', 'created_by')
    readonly_fields = ('created_by',)

    def save_model(self, request, obj, form, change):
        if not obj.created_by:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(ExamResult)
class ExamResultAdmin(admin.ModelAdmin):
    list_display = ('exam', 'student', 'score')
    search_fields = ('student__ismi', 'student__familiya', 'exam__group__name')
    list_filter = ('exam__exam_date', 'score')
    ordering = ('-exam__exam_date',)



# CustomUser modelini admin panelga qo'shish
admin.site.register(CustomUser, CustomUserAdmin)
