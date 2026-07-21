from django.contrib import admin
from import_export.admin import ImportExportActionModelAdmin
from .models import *
from import_export.admin import ImportExportModelAdmin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from .resources import UserResource  # if you put it in resources.py


# Register your models here.

from django import forms
from .models import Program, Student, ParticipationRule, FestConfiguration, LiveAuctionState, BidLog, SystemSetting

class ProgramAdminForm(forms.ModelForm):
    class Meta:
        model = Program
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        sections = SystemSetting.objects.filter(setting_type='OTHER', key='section').values_list('value', flat=True).distinct()
        categories = SystemSetting.objects.filter(setting_type='CATEGORY').values_list('value', flat=True).distinct()
        types = SystemSetting.objects.filter(setting_type='TYPE').values_list('value', flat=True).distinct()
        skills = SystemSetting.objects.filter(setting_type='SKILL').values_list('value', flat=True).distinct()
        modes = SystemSetting.objects.filter(setting_type='MODE').values_list('value', flat=True).distinct()

        self.fields['section'] = forms.ChoiceField(choices=[('', '---------')] + [(s, s) for s in sorted(sections)], required=False)
        self.fields['category'] = forms.ChoiceField(choices=[('', '---------')] + [(c, c) for c in sorted(categories)], required=False)
        self.fields['type'] = forms.ChoiceField(choices=[('', '---------')] + [(t, t) for t in sorted(types)], required=False)
        self.fields['skill'] = forms.ChoiceField(choices=[('', '---------')] + [(sk, sk) for sk in sorted(skills)], required=False)
        self.fields['mode'] = forms.ChoiceField(choices=[('', '---------')] + [(m, m) for m in sorted(modes)], required=False)


class StudentAdminForm(forms.ModelForm):
    class Meta:
        model = Student
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        sections = SystemSetting.objects.filter(setting_type='OTHER', key='section').values_list('value', flat=True).distinct()
        categories = SystemSetting.objects.filter(setting_type='CATEGORY').values_list('value', flat=True).distinct()

        self.fields['section'] = forms.ChoiceField(choices=[('', '---------')] + [(s, s) for s in sorted(sections)], required=False)
        self.fields['category'] = forms.ChoiceField(choices=[('', '---------')] + [(c, c) for c in sorted(categories)], required=False)


@admin.register(Program)
class studentdata(ImportExportActionModelAdmin):
    form = ProgramAdminForm

@admin.register(Student)
class students(ImportExportActionModelAdmin):
    form = StudentAdminForm
    actions = ['audit_minimum_requirements']

    @admin.action(description="Audit minimum program requirements")
    def audit_minimum_requirements(self, request, queryset):
        from .models import ParticipationRule, ProgramParticipant
        from django.contrib import messages

        unmet_details = []
        met_count = 0

        for student in queryset:
            student_category = student.category
            if not student_category:
                continue

            rules = ParticipationRule.objects.filter(category__iexact=student_category)
            student_unmet = []

            for rule in rules:
                if rule.min_count > 0:
                    query = ProgramParticipant.objects.filter(participant=student)
                    current_count = 0
                    for p in query:
                        type_matches = not rule.program_type or (p.program.type and p.program.type.lower() == rule.program_type.lower())
                        mode_matches = not rule.program_mode or (p.program.mode and p.program.mode.lower() == rule.program_mode.lower())
                        if type_matches and mode_matches:
                            current_count += 1

                    if current_count < rule.min_count:
                        desc = f"{rule.program_type or 'any'} type / {rule.program_mode or 'any'} mode (has {current_count}, needs {rule.min_count})"
                        student_unmet.append(desc)

            if student_unmet:
                unmet_details.append(f"{student.name} ({student.adno}): " + ", ".join(student_unmet))
            else:
                met_count += 1

        if unmet_details:
            msg = f"Audit complete. {met_count} students met all minimum requirements. The following students did not meet their minimum requirements:\n" + "\n".join(unmet_details)
            self.message_user(request, msg, messages.WARNING)
        else:
            self.message_user(request, "Audit complete. All selected students met their minimum requirements.", messages.SUCCESS)

@admin.register(ParticipationRule)
class ParticipationRuleAdmin(admin.ModelAdmin):
    list_display = ('category', 'program_type', 'program_mode', 'min_count', 'max_count')

@admin.register(OnlineProfile)
class OnlineProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'last_seen', 'is_online')

@admin.register(FestConfiguration)
class FestConfigurationAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        if FestConfiguration.objects.exists():
            return False
        return super().has_add_permission(request)

@admin.register(LiveAuctionState)
class LiveAuctionStateAdmin(admin.ModelAdmin):
    list_display = ('student', 'current_highest_amount', 'current_highest_bidder', 'expires_at', 'is_active')

@admin.register(BidLog)
class BidLogAdmin(admin.ModelAdmin):
    list_display = ('student', 'leader', 'amount', 'timestamp')

@admin.register(SystemSetting)
class SystemSettingAdmin(admin.ModelAdmin):
    list_display = ('setting_type', 'key', 'value')

class CustomUserAdmin(ImportExportModelAdmin, UserAdmin):
    resource_class = UserResource

# Unregister the default User admin and re-register
from django.contrib import admin
admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)
admin.site.register(ProgramSectionCount)
  