#This is not in use now
from django import forms
from .models import Program, Student, ProgramParticipant

class AssignStudentForm(forms.ModelForm):
    class Meta:
        model = ProgramParticipant
        fields = ['student', 'program']

    student = forms.ModelChoiceField(queryset=Student.objects.all(), label="Select Student")
    program = forms.ModelChoiceField(queryset=Program.objects.all(), label="Select Program")


class ProgramForm(forms.ModelForm):
    class Meta:
        model = Program
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from .models import AdminSetting
        sections = AdminSetting.objects.filter(section__isnull=False).exclude(section='').values_list('section', flat=True).distinct()
        categories = AdminSetting.objects.filter(category__isnull=False).exclude(category='').values_list('category', flat=True).distinct()
        types = AdminSetting.objects.filter(type__isnull=False).exclude(type='').values_list('type', flat=True).distinct()
        skills = AdminSetting.objects.filter(skill__isnull=False).exclude(skill='').values_list('skill', flat=True).distinct()

        self.fields['section'] = forms.ChoiceField(choices=[('', '---------')] + [(s, s) for s in sorted(sections)], required=False)
        self.fields['category'] = forms.ChoiceField(choices=[('', '---------')] + [(c, c) for c in sorted(categories)], required=False)
        self.fields['type'] = forms.ChoiceField(choices=[('', '---------')] + [(t, t) for t in sorted(types)], required=False)
        self.fields['skill'] = forms.ChoiceField(choices=[('', '---------')] + [(sk, sk) for sk in sorted(skills)], required=False)


class StudentForm(forms.ModelForm):
    class Meta:
        model = Student
        exclude = ['user', 'assigned_by', 'assigned_at', 'amount']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from .models import AdminSetting
        sections = AdminSetting.objects.filter(section__isnull=False).exclude(section='').values_list('section', flat=True).distinct()
        categories = AdminSetting.objects.filter(category__isnull=False).exclude(category='').values_list('category', flat=True).distinct()

        self.fields['section'] = forms.ChoiceField(choices=[('', '---------')] + [(s, s) for s in sorted(sections)], required=False)
        self.fields['category'] = forms.ChoiceField(choices=[('', '---------')] + [(c, c) for c in sorted(categories)], required=False)