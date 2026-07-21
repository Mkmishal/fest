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
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from .models import SystemSetting
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


class StudentForm(forms.ModelForm):
    class Meta:
        model = Student
        exclude = ['user', 'assigned_by', 'assigned_at', 'amount']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from .models import SystemSetting
        sections = SystemSetting.objects.filter(setting_type='OTHER', key='section').values_list('value', flat=True).distinct()
        categories = SystemSetting.objects.filter(setting_type='CATEGORY').values_list('value', flat=True).distinct()

        self.fields['section'] = forms.ChoiceField(choices=[('', '---------')] + [(s, s) for s in sorted(sections)], required=False)
        self.fields['category'] = forms.ChoiceField(choices=[('', '---------')] + [(c, c) for c in sorted(categories)], required=False)