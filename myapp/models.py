from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils.timezone import now


class CustomUser(AbstractUser):
    bio = models.TextField(blank=True, null=True)
    is_teacher = models.BooleanField(default=False)


class Group(models.Model):
    name = models.CharField(max_length=100)
    information = models.TextField(blank=True, null=True)
    created_time = models.DateTimeField(auto_now_add=True)
    students = models.ManyToManyField('Profile', related_name='profile_group', blank=True)
    objects = models.Manager()

    def __str__(self):
        return self.name


class Profile(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE)
    familiya = models.CharField(max_length=100)
    ismi = models.CharField(max_length=100)
    telefon = models.CharField(max_length=15, blank=True, null=True)
    added_time = models.DateTimeField(default=now)
    rasm = models.ImageField(upload_to='users_img', blank=True, null=True)

    # Guruhlarni ManyToMany orqali bog'lash, va 'through' parametri bilan ProfileGroup modelini ko'rsatish
    guruhlar = models.ManyToManyField(Group, through='ProfileGroup', related_name='group_profiles', blank=True)

    objects = models.Manager()

    def __str__(self):
        return f"{self.ismi} {self.familiya}"

    # Guruhlar bilan bog‘lanish
    def add_to_group(self, group):
        ProfileGroup.objects.get_or_create(profile=self, group=group)


class ProfileGroup(models.Model):
    profile = models.ForeignKey('Profile', on_delete=models.CASCADE)
    group = models.ForeignKey('Group', on_delete=models.CASCADE)
    added_time = models.DateTimeField(auto_now=True)  # Faqat guruhga qo'shilgan vaqtda saqlanadi

    objects = models.Manager()

    def __str__(self):
        return f"{self.profile} - {self.group}"


class Video(models.Model):
    title = models.CharField(max_length=255)  # Video sarlavhasi
    youtube_link = models.URLField()  # YouTube havolasi
    is_general = models.BooleanField(default=False)  # Umumiy video yoki yo'q
    groups = models.ManyToManyField('Group', blank=True)  # Tanlangan guruhlar
    created_time = models.DateTimeField(auto_now_add=True)  # Video yuklangan vaqt

    objects = models.Manager()

    def __str__(self):
        return self.title


class Payments(models.Model):
    names_ful = models.ForeignKey(Profile, on_delete=models.SET_NULL, null=True)
    month = models.CharField(max_length=20, choices=[  # Oylar uchun tanlovlar
        ('Yanvar', 'Yanvar'),
        ('Fevral', 'Fevral'),
        ('Mart', 'Mart'),
        ('Aprel', 'Aprel'),
        ('May', 'May'),
        ('Iyun', 'Iyun'),
        ('Iyul', 'Iyul'),
        ('Avgust', 'Avgust'),
        ('Sentabr', 'Sentabr'),
        ('Oktabr', 'Oktabr'),
        ('Noyabr', 'Noyabr'),
        ('Dekabr', 'Dekabr'),
    ])
    money_summ = models.DecimalField(max_digits=10, decimal_places=2)  # To'lanadigan summa
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2, default=0)  # To'langan summa
    payment_date = models.DateField(null=True, blank=True)  # To'lov qilingan sana

    objects = models.Manager()

    def __str__(self):
        # To'lov qiluvchi va oyni matn sifatida qaytarish
        if self.names_ful:
            return f"{self.names_ful.ismi} {self.names_ful.familiya} - {self.month}"
        return f"{self.month} (No Profile)"


class Exam(models.Model):
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name='exams')
    question_count = models.PositiveIntegerField()
    max_score = models.PositiveIntegerField()
    teacher_name = models.CharField(max_length=255)
    exam_date = models.DateTimeField()
    created_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    objects = models.Manager()

    def __str__(self):
        return f"{self.group.name} - {self.exam_date.strftime('%Y-%m-%d %H:%M')}"


class ExamResult(models.Model):
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name='results')
    student = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='exam_results')
    score = models.IntegerField(null=True, blank=True)

    objects = models.Manager()

    class Meta:
        unique_together = ('exam', 'student')

    def __str__(self):
        return f"{self.student.ismi} {self.student.familiya} - {self.score}"


class Recommendation(models.Model):
    student = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='recommendations')
    suggestion = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    objects = models.Manager()

    def __str__(self):
        return f"Recommendation for {self.student.ismi} {self.student.familiya}"
