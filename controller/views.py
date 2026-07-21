from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.models import User
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import Group
from django.contrib.auth import authenticate,login as lgin,logout as lgout
from controller.models import *
from django.template.loader import render_to_string
from django.http import JsonResponse, HttpResponse, HttpResponseRedirect
from django.views.decorators.csrf import csrf_exempt
from import_export.formats.base_formats import XLSX
from django.contrib.auth import update_session_auth_hash
from django.contrib import messages
from .forms import AssignStudentForm, ProgramForm, StudentForm
from django.db.models import Count,Q
from openpyxl import Workbook
from .resources import UserResource, StudentResource, ProgramResource
from django.urls import reverse
from tablib import Dataset
import tablib
from django.utils import timezone


def is_student(user):
    return user.groups.filter(name='student').exists() 

def is_teacher(user):
    return user.groups.filter(name='teacher').exists()

def is_admin(user):
    return user.groups.filter(name='Admin').exists()

def is_controller(user):
    return user.groups.filter(name='controller').exists()

def is_leader(user):
    return user.groups.filter(name='leader').exists()

def get_ordered_leaders(setting):
    leaders = list(User.objects.filter(groups__name='leader'))
    order_list = [int(x) for x in setting.leader_order.split(',')] if getattr(setting, 'leader_order', None) else []
    if order_list:
        leader_map = {l.id: l for l in leaders}
        ordered = []
        for lid in order_list:
            if lid in leader_map:
                ordered.append(leader_map[lid])
        # Add remaining leaders (failsafe)
        for l in leaders:
            if l not in ordered:
                ordered.append(l)
        return ordered
    return sorted(leaders, key=lambda l: l.id)


#user setups.
def login(request):
    error_message =None
    if request.POST:
        username = request.POST.get('username')
        password = request.POST.get('password')
        user= authenticate(username=username,password=password)
        if user is not None:
            lgin(request,user)
            return redirect('/dashboard')
        else:
            error_message = 'invalid credentials'
    return render(request,'login.html',{'error_message':error_message})


def dashboard(request):
    groups = request.user.groups.values_list('name', flat=True)
    setting, _ = FestConfiguration.objects.get_or_create(pk=1)  # ensures single record
    available_grades = Student.objects.values_list('grade', flat=True).distinct()
    
    settings_sections = SystemSetting.objects.filter(setting_type='OTHER', key='section').order_by('id')
    settings_categories = SystemSetting.objects.filter(setting_type='CATEGORY').order_by('id')
    settings_types = SystemSetting.objects.filter(setting_type='TYPE').order_by('id')
    settings_skills = SystemSetting.objects.filter(setting_type='SKILL').order_by('id')
    settings_judging = SystemSetting.objects.filter(setting_type='OTHER', key='judging_conditions').order_by('id')
    settings_keys = SystemSetting.objects.filter(setting_type='OTHER').exclude(key__in=['section', 'judging_conditions']).order_by('id')
    settings_fest_names = SystemSetting.objects.filter(setting_type='FEST_NAME').order_by('id')
    settings_houses = SystemSetting.objects.filter(setting_type='HOUSE').order_by('id')
    settings_modes = SystemSetting.objects.filter(setting_type='MODE').order_by('id')
    rules = ParticipationRule.objects.all().order_by('id')
 
    if request.method == 'POST':
        if request.POST.get('toggle_bidding') == '1':
            mode = request.POST.get('bidding_mode')
            if mode == 'on':
                setting.bidding_mode = True
            elif mode == 'off':
                setting.bidding_mode = False
            setting.save()
            return redirect('dashboard')

        if request.POST.get('toggle_auction') == '1':
            mode = request.POST.get('auction_active')
            if mode == 'on':
                setting.auction_active = True
            elif mode == 'off':
                setting.auction_active = False
            setting.save()
            return redirect('dashboard')
            
        if request.POST.get('toggle_round_mode') == '1':
            mode = request.POST.get('selection_round_active')
            if mode == 'on':
                setting.selection_round_active = True
            elif mode == 'off':
                setting.selection_round_active = False
            setting.save()
            return redirect('dashboard')

        if request.POST.get('toggle_candidate_registration') == '1':
            mode = request.POST.get('candidate_registration_active')
            if mode == 'on':
                setting.candidate_registration_active = True
            elif mode == 'off':
                setting.candidate_registration_active = False
            setting.save()
            return redirect('dashboard')

        if request.POST.get('manage_rounds') == '1':
            action = request.POST.get('action')
            if action == 'reset':
                setting.current_round = 1
                setting.current_turn_step = 0
                setting.save()
            elif action == 'advance':
                leaders = get_ordered_leaders(setting)
                if leaders:
                    N = len(leaders)
                    setting.current_turn_step += 1
                    if setting.current_turn_step >= N:
                        setting.current_turn_step = 0
                        setting.current_round += 1
                    setting.save()
            return redirect('dashboard')

        if request.POST.get('set_leader_order') == '1':
            leader_positions = []
            for key, val in request.POST.items():
                if key.startswith('leader_pos_'):
                    try:
                        leader_id = int(key.replace('leader_pos_', ''))
                        pos = int(val)
                        leader_positions.append((leader_id, pos))
                    except ValueError:
                        pass
            leader_positions.sort(key=lambda x: x[1])
            setting.leader_order = ",".join(str(x[0]) for x in leader_positions)
            setting.save()
            return redirect('dashboard')
            
        if request.POST.get('update_bidding_config') == '1':
            try:
                min_bid = int(request.POST.get('min_bid', 1000))
                setting.min_bid_amount = min_bid
                
                bid_confirmation_duration = int(request.POST.get('bid_confirmation_duration', 10))
                setting.bid_confirmation_duration = bid_confirmation_duration

                avg_biddable_count = int(request.POST.get('avg_biddable_count', 3))
                setting.avg_biddable_count = avg_biddable_count
                
                setting.save()
            except ValueError:
                pass
            return redirect('dashboard')

        grade = request.POST.get('grade')
        if grade:
            setting.selected_grade = grade
        setting.save()
        return redirect('dashboard')  # or wherever you'd like
        
    current_turn_leader_name = "None"
    if setting.selection_round_active:
        leaders = get_ordered_leaders(setting)
        if leaders:
            N = len(leaders)
            leader_idx = ((setting.current_round - 1) + setting.current_turn_step) % N
            current_leader = leaders[leader_idx]
            current_turn_leader_name = current_leader.first_name if current_leader.first_name else current_leader.username

    # For displaying leader ordering in the template
    all_leaders = list(User.objects.filter(groups__name='leader').order_by('id'))
    order_list = [int(x) for x in setting.leader_order.split(',')] if setting.leader_order else []
    leaders_list = []
    for leader in all_leaders:
        try:
            pos = order_list.index(leader.id) + 1
        except ValueError:
            pos = len(order_list) + 1
        leaders_list.append({
            'id': leader.id,
            'username': leader.username,
            'first_name': leader.first_name,
            'student': Student.objects.filter(user=leader).first(),
            'pos': pos
        })
    leaders_list.sort(key=lambda x: x['pos'])

    context = {
        'groups': groups,
        'available_grades': available_grades,
        'selected_grade' : setting.selected_grade,
        'bidding_mode': setting.bidding_mode,
        'auction_active': setting.auction_active,
        'min_bid_amount': setting.min_bid_amount,
        'bid_confirmation_duration': setting.bid_confirmation_duration,
        'avg_biddable_count': setting.avg_biddable_count,
        'selection_round_active': setting.selection_round_active,
        'current_round': setting.current_round,
        'current_turn_leader_name': current_turn_leader_name,
        'leaders_list': leaders_list,
        'settings_sections': settings_sections,
        'settings_categories': settings_categories,
        'settings_types': settings_types,
        'settings_skills': settings_skills,
        'settings_judging': settings_judging,
        'settings_keys': settings_keys,
        'settings_fest_names': settings_fest_names,
        'settings_houses': settings_houses,
        'settings_modes': settings_modes,
        'rules': rules,
        'candidate_registration_active': setting.candidate_registration_active,
    }
    return render(request, 'dashboard.html',context)


@user_passes_test(is_admin)
def add_setting(request):
    if request.method == 'POST':
        setting_type = request.POST.get('setting_type_field')
        
        if setting_type == 'key_value':
            key = request.POST.get('key')
            value = request.POST.get('value')
            SystemSetting.objects.create(setting_type='OTHER', key=key, value=value)
        elif setting_type == 'section':
            section = request.POST.get('section')
            SystemSetting.objects.create(setting_type='OTHER', key='section', value=section)
        elif setting_type == 'category':
            category = request.POST.get('category')
            SystemSetting.objects.create(setting_type='CATEGORY', key='category', value=category)
        elif setting_type == 'type':
            type_val = request.POST.get('type')
            SystemSetting.objects.create(setting_type='TYPE', key='type', value=type_val)
        elif setting_type == 'skill':
            skill = request.POST.get('skill')
            SystemSetting.objects.create(setting_type='SKILL', key='skill', value=skill)
        elif setting_type == 'judging_conditions':
            judging_conditions = request.POST.get('judging_conditions')
            SystemSetting.objects.create(setting_type='OTHER', key='judging_conditions', value=judging_conditions)
        elif setting_type == 'fest_name':
            fest_name = request.POST.get('fest_name')
            SystemSetting.objects.create(setting_type='FEST_NAME', key='fest_name', value=fest_name)
        elif setting_type == 'house':
            house = request.POST.get('house')
            SystemSetting.objects.create(setting_type='HOUSE', key='house', value=house)
        elif setting_type == 'mode':
            mode_val = request.POST.get('mode')
            SystemSetting.objects.create(setting_type='MODE', key='mode', value=mode_val)
            
        messages.success(request, "Admin setting added successfully.")
    return redirect('dashboard')


@user_passes_test(is_admin)
def edit_setting(request, setting_id):
    setting = get_object_or_404(SystemSetting, id=setting_id)
    if request.method == 'POST':
        setting_type = request.POST.get('setting_type_field')
        
        if setting_type == 'key_value':
            setting.setting_type = 'OTHER'
            setting.key = request.POST.get('key')
            setting.value = request.POST.get('value')
        elif setting_type == 'section':
            setting.setting_type = 'OTHER'
            setting.key = 'section'
            setting.value = request.POST.get('section')
        elif setting_type == 'category':
            setting.setting_type = 'CATEGORY'
            setting.key = 'category'
            setting.value = request.POST.get('category')
        elif setting_type == 'type':
            setting.setting_type = 'TYPE'
            setting.key = 'type'
            setting.value = request.POST.get('type')
        elif setting_type == 'skill':
            setting.setting_type = 'SKILL'
            setting.key = 'skill'
            setting.value = request.POST.get('skill')
        elif setting_type == 'judging_conditions':
            setting.setting_type = 'OTHER'
            setting.key = 'judging_conditions'
            setting.value = request.POST.get('judging_conditions')
        elif setting_type == 'fest_name':
            setting.setting_type = 'FEST_NAME'
            setting.key = 'fest_name'
            setting.value = request.POST.get('fest_name')
        elif setting_type == 'house':
            setting.setting_type = 'HOUSE'
            setting.key = 'house'
            setting.value = request.POST.get('house')
        elif setting_type == 'mode':
            setting.setting_type = 'MODE'
            setting.key = 'mode'
            setting.value = request.POST.get('mode')
            
        setting.save()
        messages.success(request, "Admin setting updated successfully.")
    return redirect('dashboard')


@user_passes_test(is_admin)
def delete_setting(request, setting_id):
    setting = get_object_or_404(SystemSetting, id=setting_id)
    setting.delete()
    messages.success(request, "Admin setting deleted successfully.")
    return redirect('dashboard')


@user_passes_test(is_admin)
def add_rule(request):
    if request.method == 'POST':
        category = request.POST.get('category')
        program_type = request.POST.get('program_type') or None
        program_mode = request.POST.get('program_mode') or None
        language = request.POST.get('language') or None
        
        is_multilingual_raw = request.POST.get('is_multilingual')
        if is_multilingual_raw == 'true':
            is_multilingual = True
        elif is_multilingual_raw == 'false':
            is_multilingual = False
        else:
            is_multilingual = None
            
        skill = request.POST.get('skill') or None
        role = request.POST.get('role') or None
        min_count = int(request.POST.get('min_count') or 0)
        max_count = int(request.POST.get('max_count'))
        
        ParticipationRule.objects.create(
            category=category,
            program_type=program_type,
            program_mode=program_mode,
            language=language,
            is_multilingual=is_multilingual,
            skill=skill,
            role=role,
            min_count=min_count,
            max_count=max_count
        )
        messages.success(request, "Participation rule added successfully.")
    return redirect('dashboard')


@user_passes_test(is_admin)
def edit_rule(request, rule_id):
    rule = get_object_or_404(ParticipationRule, id=rule_id)
    if request.method == 'POST':
        rule.category = request.POST.get('category')
        rule.program_type = request.POST.get('program_type') or None
        rule.program_mode = request.POST.get('program_mode') or None
        rule.language = request.POST.get('language') or None
        
        is_multilingual_raw = request.POST.get('is_multilingual')
        if is_multilingual_raw == 'true':
            rule.is_multilingual = True
        elif is_multilingual_raw == 'false':
            rule.is_multilingual = False
        else:
            rule.is_multilingual = None
            
        rule.skill = request.POST.get('skill') or None
        rule.role = request.POST.get('role') or None
        rule.min_count = int(request.POST.get('min_count') or 0)
        rule.max_count = int(request.POST.get('max_count'))
        rule.save()
        messages.success(request, "Participation rule updated successfully.")
    return redirect('dashboard')


@user_passes_test(is_admin)
def delete_rule(request, rule_id):
    rule = get_object_or_404(ParticipationRule, id=rule_id)
    rule.delete()
    messages.success(request, "Participation rule deleted successfully.")
    return redirect('dashboard')


from django.db.models import Prefetch
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
# Make sure to import your models: Student, Program, ProgramParticipant

@login_required
def utilities(request):
    groups = [g.name for g in request.user.groups.all()]
    if not ('Admin' in groups or 'teacher' in groups or 'leader' in groups):
        messages.error(request, "You do not have permission to access the Utilities page.")
        return redirect('dashboard')

    leader_house = None
    if 'leader' in groups and 'Admin' not in groups and 'teacher' not in groups:
        leader_student = Student.objects.filter(user=request.user).first()
        if leader_student and leader_student.house:
            leader_house = leader_student.house
        else:
            leader_house = request.user.username

    if leader_house:
        # 1. Create a filtered queryset of ONLY this house's participants
        house_participants = ProgramParticipant.objects.filter(
            participant__house=leader_house
        ).select_related('participant')

        students = Student.objects.filter(house=leader_house).prefetch_related('student_programs__program').order_by('name')
        
        # 2. Apply that filtered queryset using Prefetch
        programs = Program.objects.filter(
            program_participants__participant__house=leader_house
        ).distinct().prefetch_related(
            Prefetch('program_participants', queryset=house_participants)
        ).order_by('name')
    else:
        # Admin / teacher sees everything
        programs = Program.objects.all().prefetch_related('program_participants__participant').order_by('name')
        students = Student.objects.all().prefetch_related('student_programs__program').order_by('name')

    context = {
        'groups': groups,
        'programs': programs,
        'students': students,
        'leader_house': leader_house,
    }
    return render(request, 'utilities.html', context)


@login_required 
def logout(request):
    lgout(request)
    return redirect('login')


@login_required
def edit_password(request):
    if request.method == 'POST':
        current = request.POST.get('current_password')
        new = request.POST.get('new_password')
        confirm = request.POST.get('confirm_password')

        if not request.user.check_password(current):
            return JsonResponse({'status': 'error', 'message': 'Current password is incorrect.'})
        if new != confirm:
            return JsonResponse({'status': 'error', 'message': 'New passwords do not match.'})

        request.user.set_password(new)
        request.user.save()
        update_session_auth_hash(request, request.user)
        return JsonResponse({'status': 'success', 'message': 'Password updated successfully.'})

    return JsonResponse({'status': 'error', 'message': 'Invalid request.'})



#content area
def website(request):
    leaders = User.objects.filter(groups__name='leader')
    grouped_students = {}

    for leader in leaders:
        house_name = leader.username
        student_profile = Student.objects.filter(user=leader).first()
        if student_profile and student_profile.house:
            house_name = student_profile.house
        grouped_students[house_name] = Student.objects.filter(house=house_name).order_by('-assigned_at', 'id')

    return render(request, 'webpage.html', {
        'grouped_students': grouped_students
    })


@login_required  
def program(request):
    programs = Program.objects.all()
    form = ProgramForm()
    sections = SystemSetting.objects.filter(setting_type='OTHER', key='section').values_list('value', flat=True).distinct()
    variables = {
        'program': programs,
        'form': form,
        'sections_list': sorted(list(sections))
    }
    return render(request, 'program.html', variables)


@user_passes_test(is_admin)
def add_program(request):
    if request.method == 'POST':
        form = ProgramForm(request.POST)
        if form.is_valid():
            program_obj = form.save()
            # Save section counts
            sections = SystemSetting.objects.filter(setting_type='OTHER', key='section').values_list('value', flat=True).distinct()
            for sec in sections:
                count_val = request.POST.get(f'section_count_{sec}')
                if count_val is not None and count_val != '':
                    try:
                        val = int(count_val)
                        ProgramSectionCount.objects.update_or_create(
                            program=program_obj,
                            section=sec,
                            defaults={'count': val}
                        )
                    except ValueError:
                        pass
            return JsonResponse({'success': True, 'message': 'Program added successfully.'})
        else:
            errors = form.errors.as_text()
            return JsonResponse({'success': False, 'message': f'Validation Error: {errors}'})
    return JsonResponse({'success': False, 'message': 'Invalid request method.'})


@user_passes_test(is_admin)
def edit_program(request, program_id):
    program_obj = get_object_or_404(Program, id=program_id)
    if request.method == 'POST':
        form = ProgramForm(request.POST, instance=program_obj)
        if form.is_valid():
            form.save()
            # Save section counts
            sections = SystemSetting.objects.filter(setting_type='OTHER', key='section').values_list('value', flat=True).distinct()
            for sec in sections:
                count_val = request.POST.get(f'section_count_{sec}')
                if count_val is not None and count_val != '':
                    try:
                        val = int(count_val)
                        ProgramSectionCount.objects.update_or_create(
                            program=program_obj,
                            section=sec,
                            defaults={'count': val}
                        )
                    except ValueError:
                        pass
                else:
                    ProgramSectionCount.objects.filter(program=program_obj, section=sec).delete()
            messages.success(request, f'Program "{program_obj.name}" updated successfully.')
        else:
            messages.error(request, f'Error updating program: {form.errors.as_text()}')
    return redirect('program')


@user_passes_test(is_admin)
def delete_program(request, program_id):
    program_obj = get_object_or_404(Program, id=program_id)
    name = program_obj.name
    program_obj.delete()
    messages.success(request, f'Program "{name}" deleted successfully.')
    return redirect('program')

@login_required
def timetable(request):
    programs = Program.objects.all()
    variables = {
        'programs':programs
    }
    return render(request, 'timetable.html',variables)

@staff_member_required
def users(request):
    users = User.objects.all()
    groups = Group.objects.all()
    context = {
        'users':users,
        'user_groups':groups,
    }
    return render(request, 'users.html', context)

# Handle AJAX submission
@csrf_exempt
def create_user(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('number')
        group_name = request.POST.get('group')
        house_name = request.POST.get('house') 
        if house_name:
            house_name = house_name.strip()
            if house_name.lower() == 'none' or house_name == '':
                house_name = None
        else:
            house_name = None
        amount = request.POST.get('amount')

        if User.objects.filter(username=username).exists():
            return JsonResponse({'success': False, 'message': 'Username already exists'})
        
        user = User.objects.create_user(username=username, email=email, password=username, first_name=first_name, last_name=last_name)
        group, _ = Group.objects.get_or_create(name=group_name)
        student, _ = Student.objects.get_or_create(user=user)
        student.house = house_name
        student.name = first_name
        if amount:
            try:
                student.amount = int(amount)
            except ValueError:
                pass
        student.save()
        user.groups.add(group)
        return JsonResponse({'success': True, 'message': 'User created successfully'})
    return JsonResponse({'success': False, 'message': 'Invalid request'})  

@user_passes_test(is_admin)
def import_users(request):
    if request.method == 'POST' and request.FILES.get('excel_file'):
        print('recieved')
        file = request.FILES['excel_file']
        if not file.name.endswith('.xlsx'):
            return JsonResponse({'success': False, 'message': 'Only .xlsx files supported'})

        dataset = XLSX().create_dataset(file.read())
        resource = UserResource()

        # Optional dry run to check for errors
        result = resource.import_data(dataset, dry_run=True, format=XLSX())
        if result.has_errors():
            return JsonResponse({'success': False, 'message': 'Import failed. Check your data.'})

        # Final import
        resource.import_data(dataset, dry_run=False, format=XLSX())
        return JsonResponse({'success': True, 'message': f'{len(dataset)} users imported successfully.'})

    return JsonResponse({'success': False, 'message': 'Invalid request'})


@user_passes_test(is_admin)
def dummy_export_excel(request):
    headers = [
        'username', 'password', 'email',
        'first_name', 'last_name',
        'is_staff', 'is_superuser', 'is_active','groups'
    ]

    dataset = tablib.Dataset(headers=headers)

    response = HttpResponse(
        dataset.export('xlsx'),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = 'attachment; filename="excel_file.xlsx"'
    return response


@user_passes_test(is_admin)
def delete_user(request, user_id):
    if request.method == 'POST' or request.method == 'GET':  # allow GET if using a direct link
        try:
            user = User.objects.get(id=user_id)
            user.delete()
            # return JsonResponse({'success': True, 'message': f'User {user_id} deleted successfully.'})
            # Or redirect if using in HTML
            return redirect('users')
        except User.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'User not found.'})
    return JsonResponse({'success': False, 'message': 'Invalid request'})

@user_passes_test(is_admin)
def edit_user(request, user_id):
    user = get_object_or_404(User, id=user_id)
    if request.method == 'POST':
        try:
            # Update basic fields
            user.username = request.POST.get('username', user.username)
            user.email = request.POST.get('email', user.email)
            user.first_name = request.POST.get('first_name', user.first_name)
            user.last_name = request.POST.get('last_name', user.last_name)

            user.is_active = bool(request.POST.get('is_active'))
            user.is_staff = bool(request.POST.get('is_staff'))
            user.is_superuser = bool(request.POST.get('is_superuser'))

            password = request.POST.get('username')
            if password:
                user.set_password(password)

            # Update group
            selected_group = request.POST.get('groups')
            user.groups.clear()
            if selected_group:
                group_obj = Group.objects.get(name=selected_group)
                user.groups.add(group_obj)

            user.save()

            # Update Student profile
            house_name = request.POST.get('house')
            if house_name:
                house_name = house_name.strip()
                if house_name.lower() == 'none' or house_name == '':
                    house_name = None
            else:
                house_name = None
            amount = request.POST.get('amount')
            student, _ = Student.objects.get_or_create(user=user)
            student.house = house_name
            student.name = user.first_name
            if amount is not None:
                if amount.strip() == '':
                    student.amount = None
                else:
                    try:
                        student.amount = int(amount)
                    except ValueError:
                        pass
            student.save()

            messages.success(request, f'User "{user.username}" updated successfully.')
        except Exception as e:
            messages.error(request, f"Error: {str(e)}")
        return redirect('users')


@user_passes_test(is_admin)
def group(request):
    online_users = OnlineProfile.objects.select_related('user').order_by('-is_online', 'user__username')
    if request.GET.get('ajax') == '1':
        return render(request, 'partials/online_users.html', {'online_users': online_users})
    return render(request, 'group.html', {'online_users': online_users})

@user_passes_test(is_leader)
def auction(request):
    try:
        setting = FestConfiguration.objects.first()
        selected_grade = setting.selected_grade
        bidding_mode = setting.bidding_mode
        auction_active = setting.auction_active
        min_bid_amount = setting.min_bid_amount
        bid_confirmation_duration = setting.bid_confirmation_duration if setting else 10
    except:
        selected_grade = 'U1'
        bidding_mode = False
        auction_active = False
        min_bid_amount = 1000
        bid_confirmation_duration = 10
        
    try:
        leader_student = Student.objects.filter(user=request.user).first()
        leader_amount = leader_student.amount if (leader_student and leader_student.amount is not None) else 0
    except:
        leader_amount = 0
        
    if not auction_active:
        students = Student.objects.none()
    elif selected_grade == 'All':
        students = Student.objects.filter(Q(house__isnull=True) | Q(house=''))
    else:
        students = Student.objects.filter(Q(house__isnull=True) | Q(house=''), grade=selected_grade)

    return render(request, 'auction.html', {
        'student': students,
        'bidding_mode': bidding_mode,
        'auction_active': auction_active,
        'min_bid_amount': min_bid_amount,
        'leader_amount': leader_amount,
        'bid_confirmation_duration': bid_confirmation_duration,
    })


def participants(request):
    students = Student.objects.all() 
    form = StudentForm()
    context = {
        'student': students,
        'form': form
    }
    return render(request, 'participants.html', context)


@user_passes_test(is_admin)
def add_student(request):
    if request.method == 'POST':
        form = StudentForm(request.POST)
        if form.is_valid():
            form.save()
            return JsonResponse({'success': True, 'message': 'Student added successfully.'})
        else:
            errors = form.errors.as_text()
            return JsonResponse({'success': False, 'message': f'Validation Error: {errors}'})
    return JsonResponse({'success': False, 'message': 'Invalid request method.'})


@user_passes_test(is_admin)
def edit_student(request, student_id):
    student = get_object_or_404(Student, id=student_id)
    if request.method == 'POST':
        form = StudentForm(request.POST, instance=student)
        if form.is_valid():
            student = form.save(commit=False)
            
            # Handle amount field editing/deleting
            amount_val = request.POST.get('amount')
            if amount_val is not None:
                if amount_val.strip() == '':
                    student.amount = None
                else:
                    try:
                        student.amount = int(amount_val)
                    except ValueError:
                        pass
            
            student.save()
            messages.success(request, f'Student "{student.name}" updated successfully.')
        else:
            messages.error(request, f'Error updating student: {form.errors.as_text()}')
    return redirect('participants')


@user_passes_test(is_admin)
def import_students(request):
    if request.method == 'POST' and request.FILES.get('excel_file'):
        file = request.FILES['excel_file']
        if not file.name.endswith('.xlsx'):
            return JsonResponse({'success': False, 'message': 'Only .xlsx files supported'})

        dataset = XLSX().create_dataset(file.read())
        resource = StudentResource()

        result = resource.import_data(dataset, dry_run=True, format=XLSX())
        if result.has_errors():
            return JsonResponse({'success': False, 'message': 'Import failed. Check your data.'})

        resource.import_data(dataset, dry_run=False, format=XLSX())
        return JsonResponse({'success': True, 'message': f'{len(dataset)} students imported successfully.'})

    return JsonResponse({'success': False, 'message': 'Invalid request'})


@user_passes_test(is_admin)
def export_students_template(request):
    headers = [
        'adno', 'name', 'father', 'section',
        'locality', 'state', 'village', 'grade',
        'scode', 'house', 'category', 'point'
    ]

    dataset = tablib.Dataset(headers=headers)

    response = HttpResponse(
        dataset.export('xlsx'),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = 'attachment; filename="student_import_template.xlsx"'
    return response


@user_passes_test(is_admin)
def import_programs(request):
    if request.method == 'POST' and request.FILES.get('excel_file'):
        file = request.FILES['excel_file']
        if not file.name.endswith('.xlsx'):
            return JsonResponse({'success': False, 'message': 'Only .xlsx files supported'})

        try:
            dataset = XLSX().create_dataset(file.read())
            resource = ProgramResource()

            result = resource.import_data(dataset, dry_run=True, format=XLSX())
            if result.has_errors():
                errors_list = []
                for row_result in result.rows:
                    for err in row_result.errors:
                        errors_list.append(str(err.error))
                error_msg = "; ".join(errors_list) if errors_list else "Validation error in excel data."
                return JsonResponse({'success': False, 'message': f'Import failed: {error_msg}'})

            resource.import_data(dataset, dry_run=False, format=XLSX())
            return JsonResponse({'success': True, 'message': f'{len(dataset)} programs imported successfully.'})
        except Exception as e:
            return JsonResponse({'success': False, 'message': f'Error importing file: {str(e)}'})

    return JsonResponse({'success': False, 'message': 'Invalid request'})


@user_passes_test(is_admin)
def export_programs_template(request):
    headers = [
        'code', 'name', 'mode', 'category',
        'section', 'type', 'skill', 'program_duration',
        'event_duration', 'count',
        'group_count', 'is_quiz', 'date'
    ]

    dataset = tablib.Dataset(headers=headers)

    response = HttpResponse(
        dataset.export('xlsx'),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = 'attachment; filename="program_import_template.xlsx"'
    return response


from datetime import timedelta

def check_active_bid_status(setting=None):
    if setting is None:
        setting = FestConfiguration.objects.first()
    if not setting:
        return None
    
    # Process any expired live auction states
    now = timezone.now()
    expired_states = LiveAuctionState.objects.filter(is_active=True, expires_at__isnull=False, expires_at__lte=now)
    for state in expired_states:
        student = state.student
        winner = state.current_highest_bidder
        if winner:
            try:
                # Get the winner's house name
                house_name = winner.username
                student_profile = Student.objects.filter(user=winner).first()
                if student_profile and student_profile.house:
                    house_name = student_profile.house
                
                student.house = house_name
                student.assigned_by = winner
                student.assigned_at = timezone.now()
                student.amount = state.current_highest_amount
                student.save()
                
                # Deduct winning leader's budget
                leader_student = Student.objects.filter(user=winner).first()
                if leader_student and leader_student.amount is not None:
                    leader_student.amount -= state.current_highest_amount
                    leader_student.save()
            except Exception as e:
                print("Error finalizing active bid:", e)
        
        # Mark inactive
        state.is_active = False
        state.save()
        
    return setting

@user_passes_test(is_leader)
def assign_student(request):
    if request.method == "POST":
        student_id = request.POST.get("student_id")
        try:
            s = Student.objects.get(id=student_id)
            
            try:
                setting = FestConfiguration.objects.first()
                setting = check_active_bid_status(setting)
                bidding_mode = setting.bidding_mode if setting else False
                auction_active = setting.auction_active if setting else False
            except Exception as e:
                print("Error fetching setting:", e)
                setting = None
                bidding_mode = False
                auction_active = False

            if not auction_active:
                return JsonResponse({'success': False, 'error': 'Auction is currently paused/inactive.'})

            if bidding_mode:
                bid = request.POST.get('bid')
                if bid is None:
                    return JsonResponse({'success': False, 'error': 'Bid amount required.'})
                
                try:
                    bid_val = int(bid)
                except ValueError:
                    return JsonResponse({'success': False, 'error': 'Invalid bid amount.'})

                leader_student = Student.objects.filter(user=request.user).first()
                leader_budget = leader_student.amount if (leader_student and leader_student.amount is not None) else 0

                if bid_val > leader_budget:
                    return JsonResponse({'success': False, 'error': f'Insufficient budget! You only have {leader_budget} rs left.'})

                # Bidding reserve budget restriction
                house_name = request.user.username
                if leader_student and leader_student.house:
                    house_name = leader_student.house

                assigned_count = Student.objects.filter(house=house_name, user__isnull=True).count()
                avg_biddable_count = setting.avg_biddable_count if (setting and setting.avg_biddable_count is not None) else 3
                min_bid_amount = setting.min_bid_amount if (setting and setting.min_bid_amount is not None) else 1000

                required_reserve = max(0, avg_biddable_count - 1 - assigned_count) * min_bid_amount
                if leader_budget - bid_val < required_reserve:
                    return JsonResponse({
                        'success': False,
                        'error': f'Bid rejected! You must keep a reserve of at least {required_reserve} rs for subsequent drafts (Remaining: {leader_budget - bid_val} rs, Required reserve: {required_reserve} rs).'
                    })

                # Find if there is any active live auction state
                active_state = LiveAuctionState.objects.filter(is_active=True).first()
                if active_state:
                    # An active auction is running
                    if active_state.student != s:
                        return JsonResponse({'success': False, 'error': f'Bidding is currently in progress for {active_state.student.name}.'})
                    
                    # Same student - must be higher bid
                    if bid_val <= active_state.current_highest_amount:
                        return JsonResponse({'success': False, 'error': f'Bid must be higher than the current bid of {active_state.current_highest_amount} rs.'})
                    
                    # Update active bid
                    active_state.current_highest_amount = bid_val
                    active_state.current_highest_bidder = request.user
                    active_state.expires_at = timezone.now() + timedelta(seconds=setting.bid_confirmation_duration)
                    active_state.save()
                else:
                    # Start a new active auction
                    if s.house:
                        return JsonResponse({'success': False, 'error': 'Student is already assigned to a house.'})
                    
                    if bid_val < setting.min_bid_amount:
                        return JsonResponse({'success': False, 'error': f'Bid must be at least the minimum bid of {setting.min_bid_amount} rs.'})

                    active_state, _ = LiveAuctionState.objects.get_or_create(student=s)
                    active_state.current_highest_amount = bid_val
                    active_state.current_highest_bidder = request.user
                    active_state.expires_at = timezone.now() + timedelta(seconds=setting.bid_confirmation_duration)
                    active_state.is_active = True
                    active_state.save()

                # Always create a BidLog entry upon every successful bid
                BidLog.objects.create(
                    student=s,
                    leader=request.user,
                    amount=bid_val
                )

                return JsonResponse({'success': True})
            
            else:
                # Bidding mode off
                if setting and setting.selection_round_active:
                    leaders = get_ordered_leaders(setting)
                    if not leaders:
                        return JsonResponse({'success': False, 'error': 'No leaders found.'})
                    N = len(leaders)
                    leader_idx = ((setting.current_round - 1) + setting.current_turn_step) % N
                    current_leader = leaders[leader_idx]
                    if request.user != current_leader:
                        return JsonResponse({'success': False, 'error': "It is not your turn to select."})

                if not s.house:
                    house_name = request.user.username
                    student_profile = Student.objects.filter(user=request.user).first()
                    if student_profile and student_profile.house:
                        house_name = student_profile.house
                    s.house = house_name
                    s.assigned_by = request.user
                    s.assigned_at = timezone.now()
                    s.save()

                    # Advance turn
                    if setting and setting.selection_round_active:
                        leaders = get_ordered_leaders(setting)
                        N = len(leaders)
                        setting.current_turn_step += 1
                        if setting.current_turn_step >= N:
                            setting.current_turn_step = 0
                            setting.current_round += 1
                        setting.save()

                    return JsonResponse({'success': True})
                else:
                    return JsonResponse({'success': False, 'error': 'Already assigned.'})

        except Student.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Student not found.'})
    return JsonResponse({'success': False, 'error': 'Invalid request'})

def get_unassigned_students(request):
    try:
        setting = FestConfiguration.objects.first()
        setting = check_active_bid_status(setting)
        selected_grade = setting.selected_grade
        bidding_mode = setting.bidding_mode
        auction_active = setting.auction_active
        min_bid_amount = setting.min_bid_amount
        bid_confirmation_duration = setting.bid_confirmation_duration if setting else 10
        selection_round_active = setting.selection_round_active
        current_round = setting.current_round
        current_turn_step = setting.current_turn_step
    except:
        setting = None
        selected_grade = 'U1'
        bidding_mode = False
        auction_active = False
        min_bid_amount = 1000
        bid_confirmation_duration = 10
        selection_round_active = False
        current_round = 1
        current_turn_step = 0

    if not auction_active:
        students = Student.objects.none()
    elif selected_grade == 'All':
        students = Student.objects.filter(Q(house__isnull=True) | Q(house=''))
    else:
        students = Student.objects.filter(Q(house__isnull=True) | Q(house=''), grade=selected_grade)

    response = render(request, 'partials/student_list.html', {'student': students, 'auction_active': auction_active})
    response['X-Bidding-Mode'] = 'true' if bidding_mode else 'false'
    response['X-Auction-Active'] = 'true' if auction_active else 'false'
    response['X-Min-Bid-Amount'] = str(min_bid_amount)
    response['X-Bid-Confirmation-Duration'] = str(bid_confirmation_duration)

    current_leader_id = ""
    current_leader_name = ""
    is_my_turn = "false"
    
    if selection_round_active and not bidding_mode:
        leaders = get_ordered_leaders(setting)
        if leaders:
            N = len(leaders)
            leader_idx = ((current_round - 1) + current_turn_step) % N
            current_leader = leaders[leader_idx]
            current_leader_id = str(current_leader.id)
            current_leader_name = current_leader.first_name if current_leader.first_name else current_leader.username
            is_my_turn = "true" if request.user == current_leader else "false"

    response['X-Selection-Round-Active'] = 'true' if selection_round_active else 'false'
    response['X-Current-Round'] = str(current_round)
    response['X-Current-Turn-Leader-Id'] = current_leader_id
    response['X-Current-Turn-Leader-Name'] = current_leader_name
    response['X-Is-My-Turn'] = is_my_turn

    try:
        leader_student = Student.objects.filter(user=request.user).first()
        leader_amount = leader_student.amount if (leader_student and leader_student.amount is not None) else 0
    except:
        leader_amount = 0
    response['X-Leader-Amount'] = str(leader_amount)

    active_state = LiveAuctionState.objects.filter(is_active=True).first()
    if auction_active and bidding_mode and active_state:
        response['X-Active-Bid-Student-Id'] = str(active_state.student.id)
        response['X-Active-Bid-Student-Name'] = active_state.student.name
        response['X-Active-Bid-Amount'] = str(active_state.current_highest_amount)
        response['X-Active-Bid-Leader-Id'] = str(active_state.current_highest_bidder.id if active_state.current_highest_bidder else '')
        
        if active_state.expires_at:
            delta = active_state.expires_at - timezone.now()
            time_left = max(0, delta.total_seconds())
            response['X-Active-Bid-Time-Left'] = f"{time_left:.1f}"
        else:
            response['X-Active-Bid-Time-Left'] = "0"
            
        winner_user = active_state.current_highest_bidder
        winner_house = "Unknown"
        if winner_user:
            winner_house = winner_user.username
            winner_profile = Student.objects.filter(user=winner_user).first()
            if winner_profile and winner_profile.house:
                winner_house = winner_profile.house
        response['X-Active-Bid-Winner-House'] = winner_house

    return response

def grouped_students_partial(request):
    try:
        setting = FestConfiguration.objects.first()
        setting = check_active_bid_status(setting)
        bidding_mode = setting.bidding_mode
        auction_active = setting.auction_active
        bid_confirmation_duration = setting.bid_confirmation_duration if setting else 10
    except:
        setting = None
        bidding_mode = False
        auction_active = False
        bid_confirmation_duration = 10

    leaders = User.objects.filter(groups__name='leader')
    grouped = {}

    for leader in leaders:
        house_name = leader.username
        student_profile = Student.objects.filter(user=leader).first()
        if student_profile and student_profile.house:
            house_name = student_profile.house
        grouped[house_name] = Student.objects.filter(house=house_name).order_by('-assigned_at', 'id')
    
    context = {
        'grouped_students': grouped,
    }

    response = render(request, 'partials/houses.html', context)
    response['X-Bidding-Mode'] = 'true' if bidding_mode else 'false'
    response['X-Auction-Active'] = 'true' if auction_active else 'false'
    response['X-Bid-Confirmation-Duration'] = str(bid_confirmation_duration)

    active_state = LiveAuctionState.objects.filter(is_active=True).first()
    if auction_active and bidding_mode and active_state:
        response['X-Active-Bid-Student-Id'] = str(active_state.student.id)
        response['X-Active-Bid-Student-Name'] = active_state.student.name
        response['X-Active-Bid-Amount'] = str(active_state.current_highest_amount)
        response['X-Active-Bid-Leader-Id'] = str(active_state.current_highest_bidder.id if active_state.current_highest_bidder else '')
        
        if active_state.expires_at:
            delta = active_state.expires_at - timezone.now()
            time_left = max(0, delta.total_seconds())
            response['X-Active-Bid-Time-Left'] = f"{time_left:.1f}"
        else:
            response['X-Active-Bid-Time-Left'] = "0"
            
        winner_user = active_state.current_highest_bidder
        winner_house = "Unknown"
        if winner_user:
            winner_house = winner_user.username
            winner_profile = Student.objects.filter(user=winner_user).first()
            if winner_profile and winner_profile.house:
                winner_house = winner_profile.house
        response['X-Active-Bid-Winner-House'] = winner_house

    return response

@user_passes_test(is_leader)
def skip_turn(request):
    if request.method == "POST":
        setting = FestConfiguration.objects.first()
        if not setting or not setting.selection_round_active or setting.bidding_mode:
            return JsonResponse({'success': False, 'error': 'Round-robin selection mode is not active.'})
        
        leaders = get_ordered_leaders(setting)
        if not leaders:
            return JsonResponse({'success': False, 'error': 'No leaders found.'})
        
        N = len(leaders)
        leader_idx = ((setting.current_round - 1) + setting.current_turn_step) % N
        current_leader = leaders[leader_idx]
        
        if request.user != current_leader:
            return JsonResponse({'success': False, 'error': 'It is not your turn.'})
        
        # Advance turn
        setting.current_turn_step += 1
        if setting.current_turn_step >= N:
            setting.current_turn_step = 0
            setting.current_round += 1
        setting.save()
        
        return JsonResponse({'success': True})
    return JsonResponse({'success': False, 'error': 'Invalid request method'})

@user_passes_test(is_admin)
def clear_house_assignments(request):
    if request.method == "POST":
        # Restore budgets to leaders
        assigned_students = Student.objects.filter(house__isnull=False).exclude(house='')
        for student in assigned_students:
            if student.amount and student.assigned_by:
                leader_student = Student.objects.filter(user=student.assigned_by).first()
                if leader_student and leader_student.amount is not None:
                    leader_student.amount += student.amount
                    leader_student.save()
        
        # Clear assignments and bid amounts
        Student.objects.update(house=None, amount=None, assigned_by=None, assigned_at=None)
        
        # Clear bidding states and logs
        LiveAuctionState.objects.all().delete()
        BidLog.objects.all().delete()
        
        return JsonResponse({'success': True})
    return JsonResponse({'success': False, 'error': 'Invalid request method'})

@user_passes_test(is_admin)
def delete_participant(request, user_id):
    if request.method == 'POST' or request.method == 'GET':  # allow GET if using a direct link
        try:
            bach = Student.objects.get(id=user_id)
            bach.delete()
            # return JsonResponse({'success': True, 'message': f'User {user_id} deleted successfully.'})
            # Or redirect if using in HTML
            return redirect('participants')
        except Student.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'User not found.'})
    return JsonResponse({'success': False, 'message': 'Invalid request'})



def export_students_excel(request):
    # Create workbook and sheet
    wb = Workbook()
    ws = wb.active
    ws.title = "Students"

    # Header row
    ws.append(['Adno', 'Name', 'Father', 'Locality', 'State', 'Village', 'Grade', 'House', 'Point', 'Bidded Amount'])

    # Data rows
    for student in Student.objects.all():
        ws.append([
            student.adno,
            student.name,
            student.father,
            student.locality,
            student.state,
            student.village,
            student.grade,
            student.house,
            student.point,
            student.amount
        ])

    # Prepare response
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename=students.xlsx'

    wb.save(response)
    return response

# You can also move these to settings.py
MAX_SINGLE_PROGRAMS = 7
MAX_GROUP_PROGRAMS = 5


def assign_students(request):
    is_admin = request.user.is_superuser or request.user.is_staff
    is_leader_user = is_leader(request.user)

    if not (is_admin or is_leader_user):
        messages.error(request, "Access denied.")
        return redirect("dashboard")

    # Fetch distinct houses to allow admin selection
    all_houses = sorted(list(Student.objects.exclude(house__isnull=True).exclude(house="").values_list("house", flat=True).distinct()))

    # Determine current house
    house_name = None
    if is_admin:
        house_name = request.GET.get("house")
        if not house_name and all_houses:
            house_name = all_houses[0]
    else:
        # It's a leader. Get their house.
        student_profile = Student.objects.filter(user=request.user).first()
        if student_profile and student_profile.house:
            house_name = student_profile.house
        else:
            house_name = request.user.username

    # Fetch students for this house
    house_students = Student.objects.filter(house=house_name) if house_name else Student.objects.none()

    # Get categories present in this house's students
    categories = sorted(list(house_students.exclude(category__isnull=True).exclude(category="").values_list("category", flat=True).distinct()))

    dropdown_categories = list(categories)
    if Program.objects.filter(category__iexact="all").exists():
        dropdown_categories.append("All")

    selected_category = request.GET.get("category")
    if not selected_category and dropdown_categories:
        selected_category = dropdown_categories[0]

    all_rules_list = list(ParticipationRule.objects.all())
    rules_by_category = {}
    for r in all_rules_list:
        cat_key = r.category.upper() if r.category else ""
        if cat_key:
            if cat_key not in rules_by_category:
                rules_by_category[cat_key] = []
            rules_by_category[cat_key].append(r)
        
    for student in house_students:
        student.rules = rules_by_category.get(student.category.upper() if student.category else "", [])

    def get_program_blocks(programs):
        def sort_key(p):
            m_val = 0 if (p.mode and p.mode.upper() == "STAGE") else 1
            t_val = 0 if (p.type and p.type.upper() == "INDIVIDUAL") else 1
            n_val = (p.name or "").lower()
            return (m_val, t_val, n_val)
        
        sorted_programs = sorted(programs, key=sort_key)
        for p in sorted_programs:
            p.team_limit = p.max_entries_per_house if p.max_entries_per_house is not None else (int(p.count) if p.count and p.count.isdigit() else None)
        
        order = [
            ("STAGE", "INDIVIDUAL"),
            ("STAGE", "GROUP"),
            ("NON STAGE", "INDIVIDUAL"),
            ("NON STAGE", "GROUP"),
        ]
        
        styles = {
            ("STAGE", "INDIVIDUAL"): {
                "label": "🎭 STAGE - INDIVIDUAL",
                "color": "#c084fc",
                "bg": "rgba(192, 132, 252, 0.08)",
            },
            ("STAGE", "GROUP"): {
                "label": "👥 STAGE - GROUP",
                "color": "#818cf8",
                "bg": "rgba(129, 140, 248, 0.08)",
            },
            ("NON STAGE", "INDIVIDUAL"): {
                "label": "📝 NON-STAGE - INDIVIDUAL",
                "color": "#fb923c",
                "bg": "rgba(251, 146, 60, 0.08)",
            },
            ("NON STAGE", "GROUP"): {
                "label": "🤝 NON-STAGE - GROUP",
                "color": "#2dd4bf",
                "bg": "rgba(45, 212, 191, 0.08)",
            },
        }
        
        blocks = []
        for key in order:
            mode_name, type_name = key
            block_programs = [
                p for p in sorted_programs 
                if (p.mode and p.mode.upper() == mode_name) and (p.type and p.type.upper() == type_name)
            ]
            if block_programs:
                style = styles[key]
                blocks.append({
                    "label": style["label"],
                    "color": style["color"],
                    "bg": style["bg"],
                    "colspan": len(block_programs),
                    "programs": block_programs,
                })
        
        other_programs = [
            p for p in sorted_programs
            if not any(
                (p.mode and p.mode.upper() == m) and (p.type and p.type.upper() == t)
                for m, t in order
            )
        ]
        if other_programs:
            blocks.append({
                "label": "⚙️ OTHER PROGRAMS",
                "color": "#94a3b8",
                "bg": "rgba(148, 163, 184, 0.08)",
                "colspan": len(other_programs),
                "programs": other_programs,
            })
            
        return sorted_programs, blocks

    # Fetch all rules and group by category for quick lookup
    rules_by_category = {}
    for rule in ParticipationRule.objects.all():
        cat_key = (rule.category or "").upper()
        if cat_key not in rules_by_category:
            rules_by_category[cat_key] = []
        rules_by_category[cat_key].append(rule)

    grids = []
    # Build grid only for the selected category
    if selected_category:
        if selected_category.upper() == "ALL":
            all_programs_raw = list(Program.objects.filter(category__iexact="all"))
            if all_programs_raw and house_students.exists():
                sorted_p, blocks = get_program_blocks(all_programs_raw)
                all_students = list(house_students.order_by("name"))
                for s in all_students:
                    s_cat = (s.category or "").upper()
                    s.rules = rules_by_category.get(s_cat, [])
                grids.append({
                    "category": "All",
                    "students": all_students,
                    "programs": sorted_p,
                    "blocks": blocks,
                })
        else:
            cat_students = list(house_students.filter(category=selected_category).order_by("name"))
            cat_programs_raw = list(Program.objects.filter(category=selected_category))
            if cat_students and cat_programs_raw:
                sorted_p, blocks = get_program_blocks(cat_programs_raw)
                for s in cat_students:
                    s_cat = (s.category or "").upper()
                    s.rules = rules_by_category.get(s_cat, [])
                grids.append({
                    "category": selected_category,
                    "students": cat_students,
                    "programs": sorted_p,
                    "blocks": blocks,
                })

    setting, _ = FestConfiguration.objects.get_or_create(pk=1)
    candidate_registration_active = setting.candidate_registration_active

    # Build a dictionary of student assignments: student_id -> list of program_ids
    assignments = {}
    for student in house_students:
        assignments[student.id] = list(
            ProgramParticipant.objects.filter(participant=student).values_list("program_id", flat=True)
        )

    if request.method == "POST":
        if not is_admin and not candidate_registration_active:
            messages.error(request, "Access denied: Candidate registration is currently closed.")
            return redirect("assign_students")

        # Parse request.POST keys
        to_create = []
        for key in request.POST:
            if key.startswith("assign_"):
                # Key format: assign_<student_id>_<program_id>
                try:
                    parts = key.split("_")
                    student_id = int(parts[1])
                    program_id = int(parts[2])
                    to_create.append(ProgramParticipant(participant_id=student_id, program_id=program_id))
                except (ValueError, IndexError):
                    continue

        from django.db import transaction
        from django.core.exceptions import ValidationError
        
        try:
            with transaction.atomic():
                # Clear existing ProgramParticipant records only for students/programs of the selected category
                if selected_category.upper() == "ALL":
                    all_program_ids = list(Program.objects.filter(category__iexact="all").values_list("id", flat=True))
                    student_ids = list(house_students.values_list("id", flat=True))
                    ProgramParticipant.objects.filter(participant_id__in=student_ids, program_id__in=all_program_ids).delete()
                else:
                    cat_students = house_students.filter(category=selected_category)
                    student_ids = list(cat_students.values_list("id", flat=True))
                    ProgramParticipant.objects.filter(participant_id__in=student_ids).delete()
                
                # Save each one-by-one to run clean() validations
                for pp in to_create:
                    pp.save()
        except ValidationError as e:
            for message in e.messages:
                messages.error(request, message)
            if is_admin:
                return redirect(f"/assign-students/?house={house_name}&category={selected_category}")
            else:
                return redirect(f"/assign-students/?category={selected_category}")

        messages.success(request, f"Assignments for house '{house_name}' (category '{selected_category}') updated successfully.")
        if is_admin:
            return redirect(f"/assign-students/?house={house_name}&category={selected_category}")
        else:
            return redirect(f"/assign-students/?category={selected_category}")

    return render(request, "assign_students.html", {
        "grids": grids,
        "is_admin": is_admin,
        "all_houses": all_houses,
        "selected_house": house_name,
        "assignments": assignments,
        "candidate_registration_active": candidate_registration_active,
        "dropdown_categories": dropdown_categories,
        "selected_category": selected_category,
    })