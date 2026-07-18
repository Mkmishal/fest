from django.contrib import admin
from import_export.admin import ImportExportActionModelAdmin
from .models import *
from import_export.admin import ImportExportModelAdmin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from .resources import UserResource  # if you put it in resources.py


# Register your models here.

from django import forms
from .models import Program, Student, AdminSetting

class ProgramAdminForm(forms.ModelForm):
    class Meta:
        model = Program
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        sections = AdminSetting.objects.filter(section__isnull=False).exclude(section='').values_list('section', flat=True).distinct()
        categories = AdminSetting.objects.filter(category__isnull=False).exclude(category='').values_list('category', flat=True).distinct()
        types = AdminSetting.objects.filter(type__isnull=False).exclude(type='').values_list('type', flat=True).distinct()
        skills = AdminSetting.objects.filter(skill__isnull=False).exclude(skill='').values_list('skill', flat=True).distinct()

        self.fields['section'] = forms.ChoiceField(choices=[('', '---------')] + [(s, s) for s in sorted(sections)], required=False)
        self.fields['category'] = forms.ChoiceField(choices=[('', '---------')] + [(c, c) for c in sorted(categories)], required=False)
        self.fields['type'] = forms.ChoiceField(choices=[('', '---------')] + [(t, t) for t in sorted(types)], required=False)
        self.fields['skill'] = forms.ChoiceField(choices=[('', '---------')] + [(sk, sk) for sk in sorted(skills)], required=False)


class StudentAdminForm(forms.ModelForm):
    class Meta:
        model = Student
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        sections = AdminSetting.objects.filter(section__isnull=False).exclude(section='').values_list('section', flat=True).distinct()
        categories = AdminSetting.objects.filter(category__isnull=False).exclude(category='').values_list('category', flat=True).distinct()

        self.fields['section'] = forms.ChoiceField(choices=[('', '---------')] + [(s, s) for s in sorted(sections)], required=False)
        self.fields['category'] = forms.ChoiceField(choices=[('', '---------')] + [(c, c) for c in sorted(categories)], required=False)


@admin.register(Program)
class studentdata(ImportExportActionModelAdmin):
    form = ProgramAdminForm

@admin.register(Student)
class students(ImportExportActionModelAdmin):
    form = StudentAdminForm

@admin.register(OnlineProfile)
class OnlineProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'last_seen', 'is_online')

admin.site.register(AdminSetting)

class CustomUserAdmin(ImportExportModelAdmin, UserAdmin):
    resource_class = UserResource

# Unregister the default User admin and re-register
from django.contrib import admin
admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)
  