from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User, Group
from django.core.exceptions import ValidationError
from controller.models import FestConfiguration, SystemSetting, Program, Student, ProgramParticipant, ParticipationRule, LiveAuctionState, BidLog

class AdminSettingCRUDTests(TestCase):
    def setUp(self):
        # Create admin user
        self.admin_user = User.objects.create_user(username='mishu_test', password='password123')
        self.admin_group, _ = Group.objects.get_or_create(name='Admin')
        self.admin_user.groups.add(self.admin_group)
        
        # Log in
        self.client = Client()
        self.client.login(username='mishu_test', password='password123')

    def test_dashboard_context(self):
        # Access dashboard
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('settings_sections', response.context)
        self.assertIn('settings_categories', response.context)

    def test_update_bidding_config_with_duration(self):
        post_data = {
            'update_bidding_config': '1',
            'min_bid': '1500',
            'bid_confirmation_duration': '25'
        }
        response = self.client.post(reverse('dashboard'), data=post_data)
        self.assertRedirects(response, reverse('dashboard'))
        
        setting = FestConfiguration.objects.first()
        self.assertEqual(setting.min_bid_amount, 1500)
        self.assertEqual(setting.bid_confirmation_duration, 25)

    def test_add_setting(self):
        post_data = {
            'setting_type_field': 'section',
            'section': 'test_sec_value'
        }
        response = self.client.post(reverse('add_setting'), data=post_data)
        self.assertRedirects(response, reverse('dashboard'))
        
        # Verify DB entry
        setting = SystemSetting.objects.get(setting_type='OTHER', key='section', value='test_sec_value')
        self.assertEqual(setting.value, 'test_sec_value')

    def test_edit_setting(self):
        # Create setting first
        setting = SystemSetting.objects.create(setting_type='OTHER', key='section', value='old_sec')
        post_data = {
            'setting_type_field': 'section',
            'section': 'new_sec'
        }
        response = self.client.post(reverse('edit_setting', args=[setting.id]), data=post_data)
        self.assertRedirects(response, reverse('dashboard'))
        
        # Verify updated entry
        setting.refresh_from_db()
        self.assertEqual(setting.value, 'new_sec')

    def test_delete_setting(self):
        # Ensure pk=1 exists so the test setting doesn't get pk=1 and get recreated on redirect to dashboard
        FestConfiguration.objects.get_or_create(pk=1)
        setting = SystemSetting.objects.create(setting_type='OTHER', key='section', value='to_delete')
        
        response = self.client.post(reverse('delete_setting', args=[setting.id]))
        self.assertRedirects(response, reverse('dashboard'))
        
        # Verify setting is deleted
        with self.assertRaises(SystemSetting.DoesNotExist):
            SystemSetting.objects.get(id=setting.id)

    def test_add_fest_name_and_house_setting(self):
        # 1. Test Fest Name
        post_data_fest = {
            'setting_type_field': 'fest_name',
            'fest_name': 'My Fest 2026'
        }
        response = self.client.post(reverse('add_setting'), data=post_data_fest)
        self.assertRedirects(response, reverse('dashboard'))
        setting_fest = SystemSetting.objects.get(setting_type='FEST_NAME')
        self.assertEqual(setting_fest.value, 'My Fest 2026')

        # 2. Test House
        post_data_house = {
            'setting_type_field': 'house',
            'house': 'Gryffindor'
        }
        response = self.client.post(reverse('add_setting'), data=post_data_house)
        self.assertRedirects(response, reverse('dashboard'))
        setting_house = SystemSetting.objects.get(setting_type='HOUSE')
        self.assertEqual(setting_house.value, 'Gryffindor')

    def test_edit_fest_name_and_house_setting(self):
        # 1. Test Fest Name
        setting_fest = SystemSetting.objects.create(setting_type='FEST_NAME', key='fest_name', value='Old Fest')
        post_data_fest = {
            'setting_type_field': 'fest_name',
            'fest_name': 'New Fest'
        }
        response = self.client.post(reverse('edit_setting', args=[setting_fest.id]), data=post_data_fest)
        self.assertRedirects(response, reverse('dashboard'))
        setting_fest.refresh_from_db()
        self.assertEqual(setting_fest.value, 'New Fest')

        # 2. Test House
        setting_house = SystemSetting.objects.create(setting_type='HOUSE', key='house', value='Slytherin')
        post_data_house = {
            'setting_type_field': 'house',
            'house': 'Hufflepuff'
        }
        response = self.client.post(reverse('edit_setting', args=[setting_house.id]), data=post_data_house)
        self.assertRedirects(response, reverse('dashboard'))
        setting_house.refresh_from_db()
        self.assertEqual(setting_house.value, 'Hufflepuff')


class UserManagementTests(TestCase):
    def setUp(self):
        self.admin_user = User.objects.create_user(username='mishu_admin', password='password123', is_staff=True)
        self.admin_group, _ = Group.objects.get_or_create(name='Admin')
        self.admin_user.groups.add(self.admin_group)
        
        self.client = Client()
        self.client.login(username='mishu_admin', password='password123')

    def test_create_user(self):
        post_data = {
            'username': 'new_user',
            'first_name': 'New',
            'email': 'new@example.com',
            'house': 'None',
            'number': '1234567890',
            'group': 'student',
            'amount': '5000'
        }
        response = self.client.post(reverse('create_user'), data=post_data)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['success'])
        
        # Verify user and student creation
        user = User.objects.get(username='new_user')
        self.assertEqual(user.first_name, 'New')
        self.assertEqual(user.last_name, '1234567890')
        self.assertIsNone(user.student.house)
        self.assertEqual(user.student.amount, 5000)

    def test_edit_user(self):
        # Create user and student profile first
        user = User.objects.create_user(username='to_edit', first_name='OldName')
        from controller.models import Student
        student = Student.objects.create(user=user, house='OldHouse', amount=1000)
        
        post_data = {
            'username': 'edited_user',
            'email': 'edited@example.com',
            'first_name': 'NewName',
            'last_name': '0987654321',
            'house': 'none',
            'amount': '6000',
            'is_active': 'on',
            'groups': 'Admin'
        }
        response = self.client.post(reverse('edit_user', args=[user.id]), data=post_data)
        self.assertRedirects(response, reverse('users'))
        
        user.refresh_from_db()
        student.refresh_from_db()
        self.assertEqual(user.username, 'edited_user')
        self.assertEqual(user.first_name, 'NewName')
        self.assertIsNone(student.house)
        self.assertEqual(student.amount, 6000)


class ProgramCRUDTests(TestCase):
    def setUp(self):
        self.admin_user = User.objects.create_user(username='mishu_admin', password='password123', is_staff=True)
        self.admin_group, _ = Group.objects.get_or_create(name='Admin')
        self.admin_user.groups.add(self.admin_group)
        
        SystemSetting.objects.create(setting_type='MODE', key='mode', value='Offline')
        SystemSetting.objects.create(setting_type='MODE', key='mode', value='Online')
        
        self.client = Client()
        self.client.login(username='mishu_admin', password='password123')

    def test_add_program(self):
        post_data = {
            'code': 'P99',
            'name': 'New Program',
            'mode': 'Offline',
            'category': '',
            'section': '',
            'type': '',
            'skill': '',
            'is_quiz': False,
            'event_duration': '60',
            'count': '1',
            'mlm_count': 1,
            'urd_count': 1,
            'group_count': 1,
            'program_duration': '60',
            'date': '2026-07-16'
        }
        response = self.client.post(reverse('add_program'), data=post_data)
        self.assertEqual(response.status_code, 200)
        if not response.json().get('success'):
            print("ADD PROGRAM ERROR MESSAGE:", response.json())
        self.assertTrue(response.json()['success'])
        
        # Verify db
        prog = Program.objects.get(code='P99')
        self.assertEqual(prog.name, 'New Program')
        self.assertEqual(prog.event_duration, '60')

    def test_edit_program(self):
        prog = Program.objects.create(code='P1', name='Old Program')
        post_data = {
            'code': 'P1_new',
            'name': 'Updated Program',
            'mode': 'Online',
            'category': '',
            'section': '',
            'type': '',
            'skill': '',
            'is_quiz': True,
            'event_duration': '90',
            'count': '2',
            'mlm_count': 2,
            'urd_count': 2,
            'group_count': 2,
            'program_duration': '90',
            'date': '2026-07-16'
        }
        response = self.client.post(reverse('edit_program', args=[prog.id]), data=post_data)
        self.assertRedirects(response, reverse('program'))
        
        prog.refresh_from_db()
        self.assertEqual(prog.code, 'P1_new')
        self.assertEqual(prog.name, 'Updated Program')
        self.assertTrue(prog.is_quiz)

    def test_delete_program(self):
        prog = Program.objects.create(code='P3', name='To Delete')
        response = self.client.post(reverse('delete_program', args=[prog.id]))
        self.assertRedirects(response, reverse('program'))
        
        with self.assertRaises(Program.DoesNotExist):
            Program.objects.get(id=prog.id)

    def test_export_programs_template(self):
        response = self.client.get(reverse('export_programs_template'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

    def test_import_programs(self):
        import io
        import tablib
        headers = [
            'code', 'name', 'mode', 'category',
            'section', 'type', 'skill', 'program_duration',
            'event_duration', 'count', 'mlm_count', 'urd_count',
            'group_count', 'is_quiz', 'date'
        ]
        data = [
            ('P200', 'Imported Program', 'Offline', 'Cat A', 'Sec A', 'Type A', 'Skill A', '60', '60', '1', 1, 1, 1, False, '2026-07-20')
        ]
        dataset = tablib.Dataset(*data, headers=headers)
        excel_file = io.BytesIO(dataset.export('xlsx'))
        excel_file.name = 'programs.xlsx'

        response = self.client.post(reverse('import_programs'), {'excel_file': excel_file})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['success'])

        prog = Program.objects.get(code='P200')
        self.assertEqual(prog.name, 'Imported Program')
        self.assertEqual(prog.date.strftime('%Y-%m-%d'), '2026-07-20')


class StudentCRUDTests(TestCase):
    def setUp(self):
        self.admin_user = User.objects.create_user(username='mishu_admin', password='password123', is_staff=True)
        self.admin_group, _ = Group.objects.get_or_create(name='Admin')
        self.controller_group, _ = Group.objects.get_or_create(name='controller')
        self.admin_user.groups.add(self.admin_group, self.controller_group)
        
        self.client = Client()
        self.client.login(username='mishu_admin', password='password123')

    def test_add_student(self):
        post_data = {
            'adno': 'S001',
            'name': 'John Doe',
            'father': 'Richard Doe',
            'section': '',
            'locality': 'Locality A',
            'state': 'State B',
            'village': 'Village C',
            'grade': 'U1',
            'scode': 'SC01',
            'house': 'Red House',
            'category': '',
            'point': 10
        }
        response = self.client.post(reverse('add_student'), data=post_data)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['success'])
        
        # Verify db
        student = Student.objects.get(adno='S001')
        self.assertEqual(student.name, 'John Doe')
        self.assertEqual(student.point, 10)

    def test_edit_student(self):
        student = Student.objects.create(adno='S002', name='Original Name')
        post_data = {
            'adno': 'S2NEW',
            'name': 'Updated Name',
            'father': 'Father Name',
            'section': '',
            'locality': 'Locality X',
            'state': 'State Y',
            'village': 'Village Z',
            'grade': 'U2',
            'scode': 'SC02',
            'house': 'Blue House',
            'category': '',
            'point': 20
        }
        response = self.client.post(reverse('edit_student', args=[student.id]), data=post_data)
        from django.contrib.messages import get_messages
        msgs = [msg.message for msg in get_messages(response.wsgi_request)]
        if msgs:
            print("EDIT STUDENT MESSAGES:", msgs)
        self.assertRedirects(response, reverse('participants'))
        
        student.refresh_from_db()
        self.assertEqual(student.adno, 'S2NEW')
        self.assertEqual(student.name, 'Updated Name')
        self.assertEqual(student.point, 20)

    def test_delete_student(self):
        student = Student.objects.create(adno='S003', name='To Delete')
        response = self.client.post(reverse('delete_participant', args=[student.id]))
        self.assertRedirects(response, reverse('participants'))
        
        with self.assertRaises(Student.DoesNotExist):
            Student.objects.get(id=student.id)

    def test_export_template(self):
        response = self.client.get(reverse('export_students_template'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

    def test_export_students_excel(self):
        Student.objects.create(adno='S009', name='Export Test', grade='G1', house='House Test')
        response = self.client.get(reverse('export_students_excel'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        self.assertIn('attachment; filename=students.xlsx', response['Content-Disposition'])


class AuctionTests(TestCase):
    def setUp(self):
        # Create leader user
        self.leader_user = User.objects.create_user(username='leader_user', password='password123')
        self.leader_group, _ = Group.objects.get_or_create(name='leader')
        self.leader_user.groups.add(self.leader_group)
        
        # Create setting
        self.setting, _ = FestConfiguration.objects.get_or_create(pk=1)
        self.setting.auction_active = True
        self.setting.save()
        
        # Create some students with different grades
        Student.objects.create(adno='S01', name='Alice', grade='U1')
        Student.objects.create(adno='S02', name='Bob', grade='U2')
        Student.objects.create(adno='S03', name='Charlie', grade='U1', house='LeaderHouse') # already assigned
        
        self.client = Client()
        
    def test_get_unassigned_students_specific_grade(self):
        # Set selected grade to U1
        self.setting.selected_grade = 'U1'
        self.setting.save()
        
        self.client.login(username='leader_user', password='password123')
        response = self.client.get(reverse('unassigned_students_partial'))
        self.assertEqual(response.status_code, 200)
        
        # Should contain Alice (U1 unassigned) but not Bob (U2) nor Charlie (assigned)
        self.assertContains(response, 'Alice')
        self.assertNotContains(response, 'Bob')
        self.assertNotContains(response, 'Charlie')
        
    def test_get_unassigned_students_all_grades(self):
        # Set selected grade to All
        self.setting.selected_grade = 'All'
        self.setting.save()
        
        self.client.login(username='leader_user', password='password123')
        response = self.client.get(reverse('unassigned_students_partial'))
        self.assertEqual(response.status_code, 200)
        
        # Should contain both Alice (U1) and Bob (U2) but not Charlie (assigned)
        self.assertContains(response, 'Alice')
        self.assertContains(response, 'Bob')
        self.assertNotContains(response, 'Charlie')

    def test_assign_student_uses_username_when_no_house_configured(self):
        self.client.login(username='leader_user', password='password123')
        alice = Student.objects.get(adno='S01')
        
        response = self.client.post(reverse('assign_student'), data={'student_id': alice.id})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['success'])
        
        alice.refresh_from_db()
        self.assertEqual(alice.house, 'leader_user')

    def test_assign_student_uses_custom_house_when_configured(self):
        # Create student profile for leader_user and assign house
        Student.objects.create(user=self.leader_user, house='Gryffindor')
        
        self.client.login(username='leader_user', password='password123')
        alice = Student.objects.get(adno='S01')
        
        response = self.client.post(reverse('assign_student'), data={'student_id': alice.id})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['success'])
        
        alice.refresh_from_db()
        self.assertEqual(alice.house, 'Gryffindor')

    def test_grouped_students_partial_groups_by_custom_house(self):
        # Create student profile for leader_user and assign house
        Student.objects.create(user=self.leader_user, house='Gryffindor')
        
        # Assign Alice to Gryffindor
        alice = Student.objects.get(adno='S01')
        alice.house = 'Gryffindor'
        alice.save()
        
        self.client.login(username='leader_user', password='password123')
        response = self.client.get(reverse('grouped_students_partial'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Gryffindor')
        self.assertContains(response, 'Alice')

    def test_assign_student_with_bidding_mode_on(self):
        from django.utils import timezone
        from datetime import timedelta
        # Enable bidding_mode
        self.setting.bidding_mode = True
        self.setting.min_bid_amount = 100
        self.setting.save()

        # Create student profile for leader_user and give them budget
        leader_student = Student.objects.create(user=self.leader_user, house='Gryffindor', amount=1000)

        self.client.login(username='leader_user', password='password123')
        alice = Student.objects.get(adno='S01')

        response = self.client.post(reverse('assign_student'), data={'student_id': alice.id, 'bid': '150'})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['success'])

        # Verify active auction state is set
        state = LiveAuctionState.objects.filter(is_active=True).first()
        self.assertIsNotNone(state)
        self.assertEqual(state.student, alice)
        self.assertEqual(state.current_highest_amount, 150)
        self.assertEqual(state.current_highest_bidder, self.leader_user)

        # Verify bid log was created
        log = BidLog.objects.filter(student=alice).first()
        self.assertIsNotNone(log)
        self.assertEqual(log.amount, 150)
        self.assertEqual(log.leader, self.leader_user)

        # Verify student not assigned yet
        alice.refresh_from_db()
        self.assertIsNone(alice.house)

        # Verify budget not deducted yet
        leader_student.refresh_from_db()
        self.assertEqual(leader_student.amount, 1000)

        # Fast forward time to expire active bid
        state.expires_at = timezone.now() - timedelta(seconds=1)
        state.save()

        # Poll the page to trigger check_active_bid_status
        self.client.get(reverse('unassigned_students_partial'))

        # Verify student is now assigned and budget is deducted
        alice.refresh_from_db()
        self.assertEqual(alice.house, 'Gryffindor')
        self.assertEqual(alice.amount, 150)

        leader_student.refresh_from_db()
        self.assertEqual(leader_student.amount, 850)

        state.refresh_from_db()
        self.assertFalse(state.is_active)

    def test_assign_student_with_bidding_mode_off(self):
        # Disable bidding_mode
        self.setting.bidding_mode = False
        self.setting.save()

        self.client.login(username='leader_user', password='password123')
        alice = Student.objects.get(adno='S01')
        alice.amount = 10
        alice.save()

        response = self.client.post(reverse('assign_student'), data={'student_id': alice.id, 'bid': '150'})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['success'])

        alice.refresh_from_db()
        self.assertEqual(alice.amount, 10) # should remain unchanged

    def test_assign_student_insufficient_budget(self):
        self.setting.bidding_mode = True
        self.setting.save()

        # Leader has small budget
        Student.objects.create(user=self.leader_user, house='Gryffindor', amount=100)

        self.client.login(username='leader_user', password='password123')
        alice = Student.objects.get(adno='S01')

        response = self.client.post(reverse('assign_student'), data={'student_id': alice.id, 'bid': '150'})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()['success'])
        self.assertEqual(response.json()['error'], 'Insufficient budget! You only have 100 rs left.')

    def test_get_unassigned_students_headers(self):
        # Set bidding mode and min bid amount
        self.setting.bidding_mode = True
        self.setting.min_bid_amount = 50000
        self.setting.save()

        # Create leader student profile and budget
        Student.objects.create(user=self.leader_user, house='Gryffindor', amount=15000)

        self.client.login(username='leader_user', password='password123')
        response = self.client.get(reverse('unassigned_students_partial'))
        self.assertEqual(response.status_code, 200)
        
        # Verify custom headers are set and correct
        self.assertEqual(response.headers.get('X-Bidding-Mode'), 'true')
        self.assertEqual(response.headers.get('X-Min-Bid-Amount'), '50000')
        self.assertEqual(response.headers.get('X-Leader-Amount'), '15000')

    def test_get_unassigned_students_headers_with_bid_duration(self):
        self.setting.bidding_mode = True
        self.setting.min_bid_amount = 2000
        self.setting.bid_confirmation_duration = 35
        self.setting.save()

        Student.objects.create(user=self.leader_user, house='Gryffindor', amount=10000)

        self.client.login(username='leader_user', password='password123')
        response = self.client.get(reverse('unassigned_students_partial'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers.get('X-Bid-Confirmation-Duration'), '35')

    def test_assign_student_with_configurable_bid_duration(self):
        from django.utils import timezone
        from datetime import timedelta
        
        self.setting.bidding_mode = True
        self.setting.min_bid_amount = 200
        self.setting.bid_confirmation_duration = 45
        self.setting.save()

        leader_student = Student.objects.create(user=self.leader_user, house='Gryffindor', amount=1000)

        self.client.login(username='leader_user', password='password123')
        alice = Student.objects.get(adno='S01')

        response = self.client.post(reverse('assign_student'), data={'student_id': alice.id, 'bid': '250'})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['success'])

        state = LiveAuctionState.objects.filter(is_active=True).first()
        self.assertIsNotNone(state)
        self.assertEqual(state.current_highest_amount, 250)
        
        # Verify expires_at is roughly now + 45 seconds
        expires = state.expires_at
        expected_expires = timezone.now() + timedelta(seconds=45)
        self.assertAlmostEqual((expires - expected_expires).total_seconds(), 0, delta=2)

    def test_bidding_reserve_budget_restriction(self):
        # Setup settings
        self.setting.bidding_mode = True
        self.setting.min_bid_amount = 1000
        self.setting.avg_biddable_count = 3
        self.setting.save()

        # Create leader student with Gryffindor house and 5000 budget
        leader_student = Student.objects.create(user=self.leader_user, house='Gryffindor', amount=5000)

        self.client.login(username='leader_user', password='password123')
        alice = Student.objects.get(adno='S01')
        bob = Student.objects.get(adno='S02')

        # 1. First bid (assigned_count = 0)
        # Bidding 3500: remaining is 1500, but required reserve is 2 * 1000 = 2000. Should fail.
        response = self.client.post(reverse('assign_student'), data={'student_id': alice.id, 'bid': '3500'})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()['success'])
        self.assertIn('reserve of at least 2000', response.json()['error'])

        # Bidding 3000: remaining is 2000 >= 2000. Should succeed.
        response = self.client.post(reverse('assign_student'), data={'student_id': alice.id, 'bid': '3000'})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['success'])

        # Finalize/assign Alice to Gryffindor to increase assigned_count to 1
        alice.house = 'Gryffindor'
        alice.amount = 3000
        alice.save()
        
        # Deduct leader's budget by 3000. Leader now has 2000.
        leader_student.amount = 2000
        leader_student.save()

        # Clear active auction state
        LiveAuctionState.objects.all().delete()

        # 2. Second bid (assigned_count = 1)
        # Bidding 1500: remaining is 500, but required reserve is 1 * 1000 = 1000. Should fail.
        response = self.client.post(reverse('assign_student'), data={'student_id': bob.id, 'bid': '1500'})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()['success'])
        self.assertIn('reserve of at least 1000', response.json()['error'])

        # Bidding 1000: remaining is 1000 >= 1000. Should succeed.
        response = self.client.post(reverse('assign_student'), data={'student_id': bob.id, 'bid': '1000'})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['success'])

    def test_selection_round_turn_enforcement_and_advancement(self):
        # Create second leader user
        leader_user_2 = User.objects.create_user(username='leader_user_2', password='password123')
        leader_user_2.groups.add(self.leader_group)

        # Enable selection round mode, disable bidding
        self.setting.bidding_mode = False
        self.setting.selection_round_active = True
        self.setting.current_round = 1
        self.setting.current_turn_step = 0
        self.setting.save()

        # Get list of leaders ordered by ID: self.leader_user and leader_user_2
        leaders = list(User.objects.filter(groups__name='leader').order_by('id'))
        first_leader = leaders[0]
        second_leader = leaders[1]

        alice = Student.objects.get(adno='S01')
        bob = Student.objects.get(adno='S02')

        # Log in as the second leader when it is the first leader's turn
        self.client.login(username=second_leader.username, password='password123')
        response = self.client.post(reverse('assign_student'), data={'student_id': alice.id})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()['success'])
        self.assertEqual(response.json()['error'], "It is not your turn to select.")

        # Log in as the first leader and select Alice
        self.client.login(username=first_leader.username, password='password123')
        response = self.client.post(reverse('assign_student'), data={'student_id': alice.id})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['success'])

        # Verify Alice is assigned to first leader's house
        alice.refresh_from_db()
        self.assertEqual(alice.house, first_leader.username)

        # Verify turn has advanced to the second leader
        self.setting.refresh_from_db()
        self.assertEqual(self.setting.current_turn_step, 1)
        self.assertEqual(self.setting.current_round, 1)

        # Verify first leader cannot select Bob now (since it is second leader's turn)
        response = self.client.post(reverse('assign_student'), data={'student_id': bob.id})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()['success'])

        # Log in as second leader and select Bob
        self.client.login(username=second_leader.username, password='password123')
        response = self.client.post(reverse('assign_student'), data={'student_id': bob.id})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['success'])

        # Verify Bob is assigned
        bob.refresh_from_db()
        self.assertEqual(bob.house, second_leader.username)

        # Verify round has advanced and turn step reset
        self.setting.refresh_from_db()
        self.assertEqual(self.setting.current_turn_step, 0)
        self.assertEqual(self.setting.current_round, 2)

    def test_skip_turn_selection_round(self):
        # Create second leader user
        leader_user_2 = User.objects.create_user(username='leader_user_2', password='password123')
        leader_user_2.groups.add(self.leader_group)

        # Enable selection round mode, disable bidding
        self.setting.bidding_mode = False
        self.setting.selection_round_active = True
        self.setting.current_round = 1
        self.setting.current_turn_step = 0
        self.setting.save()

        leaders = list(User.objects.filter(groups__name='leader').order_by('id'))
        first_leader = leaders[0]
        second_leader = leaders[1]

        # Try to skip turn with second leader (not their turn)
        self.client.login(username=second_leader.username, password='password123')
        response = self.client.post(reverse('skip_turn'))
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()['success'])

        # Skip turn with first leader (their turn)
        self.client.login(username=first_leader.username, password='password123')
        response = self.client.post(reverse('skip_turn'))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['success'])

        # Verify turn advanced to second leader
        self.setting.refresh_from_db()
        self.assertEqual(self.setting.current_turn_step, 1)
        self.assertEqual(self.setting.current_round, 1)

    def test_manual_leader_order(self):
        # Create second leader user
        leader_user_2 = User.objects.create_user(username='leader_user_2', password='password123')
        leader_user_2.groups.add(self.leader_group)

        # Enable selection round mode, disable bidding
        self.setting.bidding_mode = False
        self.setting.selection_round_active = True
        self.setting.current_round = 1
        self.setting.current_turn_step = 0
        
        # Save a manual order: second leader first, first leader second
        leaders = list(User.objects.filter(groups__name='leader').order_by('id'))
        first_leader = leaders[0]
        second_leader = leaders[1]
        self.setting.leader_order = f"{second_leader.id},{first_leader.id}"
        self.setting.save()

        alice = Student.objects.get(adno='S01')

        # Log in as the first leader (historically database order 0, but custom position 2)
        self.client.login(username=first_leader.username, password='password123')
        response = self.client.post(reverse('assign_student'), data={'student_id': alice.id})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()['success'])
        self.assertEqual(response.json()['error'], "It is not your turn to select.")

        # Log in as the second leader (custom position 1) and select Alice
        self.client.login(username=second_leader.username, password='password123')
        response = self.client.post(reverse('assign_student'), data={'student_id': alice.id})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['success'])

        # Verify Alice is assigned to second leader's house
        alice.refresh_from_db()
        self.assertEqual(alice.house, second_leader.username)

    def test_assign_students_grid_view_and_post(self):
        # Create a staff user
        admin_user = User.objects.create_user(username='admin_test', password='password123', is_staff=True)
        self.client.login(username='admin_test', password='password123')

        # Check page access
        response = self.client.get(reverse('assign_students'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Candidate Registration")

        # Create a Student and a Program in the same category
        student = Student.objects.create(
            name="Grid Student",
            adno="GS1",
            category="THANIYA-URD",
            house="leader_user"
        )
        program = Program.objects.create(
            code="P100",
            name="Grid Program",
            category="THANIYA-URD"
        )

        # Get grid page for this house
        response = self.client.get(reverse('assign_students') + "?house=leader_user")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Category: THANIYA-URD")
        self.assertContains(response, "Grid Student")
        self.assertContains(response, "Grid Program")

        # Submit checkbox assignment
        post_data = {
            f"assign_{student.id}_{program.id}": "on"
        }
        response = self.client.post(reverse('assign_students') + "?house=leader_user", data=post_data)
        self.assertEqual(response.status_code, 302)

        # Verify entry created
        self.assertTrue(ProgramParticipant.objects.filter(participant=student, program=program).exists())

        # Submit empty to delete entry
        response = self.client.post(reverse('assign_students') + "?house=leader_user", data={})
        self.assertEqual(response.status_code, 302)
        self.assertFalse(ProgramParticipant.objects.filter(participant=student, program=program).exists())

    def test_assign_students_registration_inactive_prevents_leader_edits(self):
        # Create leader user
        leader_user_2 = User.objects.create_user(username='leader_user_2', password='password123')
        leader_user_2.groups.add(self.leader_group)

        # Set candidate registration active to False
        self.setting.candidate_registration_active = False
        self.setting.save()

        # Create a Student and Program in the same category
        student = Student.objects.create(
            name="Grid Student",
            adno="GS1",
            category="THANIYA-URD",
            house="leader_user_2"
        )
        program = Program.objects.create(
            code="P100",
            name="Grid Program",
            category="THANIYA-URD"
        )

        # Log in as leader
        self.client.login(username='leader_user_2', password='password123')

        # Check grid page can be viewed (GET works)
        response = self.client.get(reverse('assign_students'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Candidate registration is currently closed.")

        # Attempt to save assignments (POST is blocked)
        post_data = {
            f"assign_{student.id}_{program.id}": "on"
        }
        response = self.client.post(reverse('assign_students'), data=post_data)
        self.assertEqual(response.status_code, 302)
        
        # Verify NO ProgramParticipant entry is created
        self.assertFalse(ProgramParticipant.objects.filter(participant=student, program=program).exists())

    def test_assign_students_all_category_program(self):
        # Create a staff user
        admin_user = User.objects.create_user(username='admin_test_all', password='password123', is_staff=True)
        self.client.login(username='admin_test_all', password='password123')

        # Create two students with different categories
        student_junior = Student.objects.create(
            name="Junior Student",
            adno="JS1",
            category="JUNIOR",
            house="leader_user"
        )
        student_senior = Student.objects.create(
            name="Senior Student",
            adno="SS1",
            category="SENIOR",
            house="leader_user"
        )

        # Create a program with category "All"
        program_all = Program.objects.create(
            code="PALL",
            name="All Category Program",
            category="All",
            max_participants=5
        )

        # Get grid page for this house
        response = self.client.get(reverse('assign_students') + "?house=leader_user")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Category: All")
        self.assertContains(response, "Junior Student")
        self.assertContains(response, "Senior Student")
        self.assertContains(response, "All Category Program")

        # Submit checkbox assignments for both students to the "All" category program
        post_data = {
            f"assign_{student_junior.id}_{program_all.id}": "on",
            f"assign_{student_senior.id}_{program_all.id}": "on"
        }
        response = self.client.post(reverse('assign_students') + "?house=leader_user", data=post_data)
        self.assertEqual(response.status_code, 302)

        # Verify entries created in db
        self.assertTrue(ProgramParticipant.objects.filter(participant=student_junior, program=program_all).exists())
        self.assertTrue(ProgramParticipant.objects.filter(participant=student_senior, program=program_all).exists())

class ParticipationRuleTests(TestCase):
    def setUp(self):
        self.student = Student.objects.create(
            name="Rule Test Student",
            adno="RT1",
            category="ULA"
        )
        self.program_stage_single = Program.objects.create(
            code="PST1",
            name="Stage Single Program",
            type="individual",
            mode="stage",
            category="ULA"
        )
        self.program_stage_group = Program.objects.create(
            code="PST2",
            name="Stage Group Program",
            type="group",
            mode="stage",
            category="ULA"
        )
        self.program_off_stage = Program.objects.create(
            code="PST3",
            name="Off Stage Program",
            type="individual",
            mode="off-stage",
            category="ULA"
        )

    def test_participation_rule_max_limit_enforced(self):
        # Create a rule: Max 1 stage-mode program
        rule = ParticipationRule.objects.create(
            category="ULA",
            program_mode="stage",
            max_count=1
        )

        # First stage program assignment should succeed
        pp1 = ProgramParticipant.objects.create(
            participant=self.student,
            program=self.program_stage_single
        )

        # Second stage program assignment should fail
        with self.assertRaises(ValidationError):
            ProgramParticipant.objects.create(
                participant=self.student,
                program=self.program_stage_group
            )

        # Off-stage program assignment should succeed as it is off-stage
        pp2 = ProgramParticipant.objects.create(
            participant=self.student,
            program=self.program_off_stage
        )

    def test_audit_minimum_requirements_action(self):
        from django.contrib.admin.sites import AdminSite
        from controller.admin import students
        
        # Create a rule: Min 2 stage-mode programs
        rule = ParticipationRule.objects.create(
            category="ULA",
            program_mode="stage",
            min_count=2,
            max_count=5
        )

        # Instantiate admin class and test action
        site = AdminSite()
        student_admin = students(Student, site)
        
        # Scenario 1: Student has 0 stage programs (unmet)
        # Create a mock request
        from django.test import RequestFactory
        factory = RequestFactory()
        request = factory.get('/')
        
        # Mock request._messages to be a dummy storage to bypass session middleware issues
        class DummyMessageStorage:
            def add(self, level, message, extra_tags=''):
                pass
        setattr(request, '_messages', DummyMessageStorage())
        
        # Call action on a queryset containing self.student
        queryset = Student.objects.filter(pk=self.student.pk)
        
        # We can mock message_user or let it run. Let's patch/mock message_user to inspect the result
        from unittest.mock import MagicMock
        student_admin.message_user = MagicMock()
        
        student_admin.audit_minimum_requirements(request, queryset)
        
        # Check that message_user was called and reported unmet requirement
        student_admin.message_user.assert_called_once()
        args, kwargs = student_admin.message_user.call_args
        self.assertIn("did not meet their minimum requirements", args[1])
        self.assertIn("needs 2", args[1])

        # Scenario 2: Student has 2 stage programs assigned (met)
        ProgramParticipant.objects.create(
            participant=self.student,
            program=self.program_stage_single
        )
        ProgramParticipant.objects.create(
            participant=self.student,
            program=self.program_stage_group
        )
        
        student_admin.message_user.reset_mock()
        student_admin.audit_minimum_requirements(request, queryset)
        args, kwargs = student_admin.message_user.call_args
        self.assertIn("met their minimum requirements", args[1])

    def test_rule_crud_views(self):
        # Create an admin user for request authentication
        admin_user = User.objects.create_user(username='rule_admin_crud', password='password123', is_staff=True)
        # Create Admin group and assign user to it (required by is_admin user_passes_test decorator)
        from django.contrib.auth.models import Group
        admin_group, _ = Group.objects.get_or_create(name='Admin')
        admin_user.groups.add(admin_group)
        self.client.login(username='rule_admin_crud', password='password123')

        # 1. Test add_rule POST view
        response = self.client.post(reverse('add_rule'), data={
            'category': 'ULA',
            'program_type': 'individual',
            'program_mode': 'stage',
            'language': 'Malayalam',
            'is_multilingual': 'true',
            'skill': 'Speech',
            'role': 'Lead',
            'min_count': '1',
            'max_count': '3'
        })
        self.assertEqual(response.status_code, 302)
        
        # Verify rule is created in database
        rule = ParticipationRule.objects.filter(category='ULA', program_type='individual').first()
        self.assertIsNotNone(rule)
        self.assertEqual(rule.min_count, 1)
        self.assertEqual(rule.max_count, 3)
        self.assertEqual(rule.language, 'Malayalam')
        self.assertTrue(rule.is_multilingual)
        self.assertEqual(rule.skill, 'Speech')
        self.assertEqual(rule.role, 'Lead')

        # 2. Test edit_rule POST view
        response = self.client.post(reverse('edit_rule', args=[rule.id]), data={
            'category': 'ULA',
            'program_type': 'individual',
            'program_mode': 'off-stage',
            'language': 'English',
            'is_multilingual': 'false',
            'skill': 'Elocution',
            'role': 'Accompanist',
            'min_count': '2',
            'max_count': '4'
        })
        self.assertEqual(response.status_code, 302)
        
        rule.refresh_from_db()
        self.assertEqual(rule.program_mode, 'off-stage')
        self.assertEqual(rule.min_count, 2)
        self.assertEqual(rule.max_count, 4)
        self.assertEqual(rule.language, 'English')
        self.assertFalse(rule.is_multilingual)
        self.assertEqual(rule.skill, 'Elocution')
        self.assertEqual(rule.role, 'Accompanist')

        # 3. Test delete_rule view
        response = self.client.post(reverse('delete_rule', args=[rule.id]))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(ParticipationRule.objects.filter(id=rule.id).exists())

    def test_expanded_rules_and_validations(self):
        # Create a student
        student = Student.objects.create(
            name="Expanded Rule Student",
            adno="ER1",
            category="ULA",
            house="Gryffindor"
        )
        
        # 1. Test Expanded Rule matching (with language, is_multilingual, skill, and role)
        rule = ParticipationRule.objects.create(
            category="ULA",
            language="English",
            is_multilingual=True,
            skill="Elocution",
            role="Lead",
            max_count=1
        )
        
        # Create a program matching these criteria
        program_matching = Program.objects.create(
            code="PEXP1",
            name="Multilingual English Elocution",
            language="English",
            is_multilingual=True,
            skill="Elocution",
            category="ULA"
        )
        
        # Create another program matching these criteria
        program_matching_2 = Program.objects.create(
            code="PEXP2",
            name="Another English Elocution",
            language="English",
            is_multilingual=True,
            skill="Elocution",
            category="ULA"
        )
        
        # First assignment as "Lead" should succeed
        pp1 = ProgramParticipant.objects.create(
            participant=student,
            program=program_matching,
            role="Lead"
        )
        
        # Second assignment as "Lead" should fail because max_count=1
        with self.assertRaises(ValidationError):
            ProgramParticipant.objects.create(
                participant=student,
                program=program_matching_2,
                role="Lead"
            )
            
        # Assignment as "Accompanist" to second program should succeed since role is different
        pp2 = ProgramParticipant.objects.create(
            participant=student,
            program=program_matching_2,
            role="Accompanist"
        )
        
        # 2. Test House Quota check
        program_quota = Program.objects.create(
            code="PQ1",
            name="Quota Program",
            max_entries_per_house=1
        )
        # Create another student in same house
        student_housemate = Student.objects.create(
            name="Housemate Student",
            adno="HM1",
            category="ULA",
            house="Gryffindor"
        )
        # Assign first student to program_quota
        ProgramParticipant.objects.create(
            participant=student,
            program=program_quota
        )
        # Assign housemate to program_quota should fail
        with self.assertRaises(ValidationError):
            ProgramParticipant.objects.create(
                participant=student_housemate,
                program=program_quota
            )
            
        # 3. Test Time/Schedule Clash check
        from datetime import date, time
        prog_time_1 = Program.objects.create(
            code="PT1",
            name="Time Program 1",
            date=date(2026, 7, 20),
            start_time=time(10, 0),
            end_time=time(11, 30)
        )
        prog_time_2 = Program.objects.create(
            code="PT2",
            name="Time Program 2",
            date=date(2026, 7, 20),
            start_time=time(11, 0), # overlaps
            end_time=time(12, 0)
        )
        # Assign student to time program 1
        ProgramParticipant.objects.create(
            participant=student,
            program=prog_time_1
        )
        # Assign student to overlapping time program 2 should fail
        with self.assertRaises(ValidationError):
            ProgramParticipant.objects.create(
                participant=student,
                program=prog_time_2
            )
            
        # 4. Test Program Capacity check
        prog_cap = Program.objects.create(
            code="PC1",
            name="Capacity Program",
            max_entries_per_house=1
        )
        # Assign student to prog_cap
        ProgramParticipant.objects.create(
            participant=student,
            program=prog_cap
        )
        # Assign housemate should fail because max_entries_per_house=1
        with self.assertRaises(ValidationError):
            ProgramParticipant.objects.create(
                participant=student_housemate,
                program=prog_cap
            )
