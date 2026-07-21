from import_export import resources, fields
from django.contrib.auth.models import User, Group

class UserResource(resources.ModelResource):
    password = fields.Field(attribute='password', column_name='password')
    groups = fields.Field(column_name='groups')  # <- add groups column

    class Meta:
        model = User
        import_id_fields = ('username',)
        skip_unchanged = True
        fields = (
            'username', 'password', 'email',
            'first_name', 'last_name',
            'is_staff', 'is_superuser', 'is_active',
            'groups',  # <- include this field
        )

    def before_import_row(self, row, **kwargs):
        # Hash the password before importing
        raw_password = row.get('password')
        if raw_password:
            dummy = User()
            dummy.set_password(raw_password)
            row['password'] = dummy.password

    def after_import_row(self, row, row_result, **kwargs):
        """
        Assign user to groups after the user is saved.
        """
        try:
            username = row.get('username')
            group_str = row.get('groups')

            if username and group_str:
                user = User.objects.get(username=username)
                group_names = [g.strip() for g in group_str.split(',') if g.strip()]
                for group_name in group_names:
                    group, _ = Group.objects.get_or_create(name=group_name)
                    user.groups.add(group)
        except Exception as e:
            print(f"Group assignment error for user {row.get('username')}: {e}")


from .models import Student, Program

class StudentResource(resources.ModelResource):
    class Meta:
        model = Student
        import_id_fields = ('adno',)  # adno is student admission number, unique identifier
        skip_unchanged = True
        fields = (
            'adno', 'name', 'father', 'section',
            'locality', 'state', 'village', 'grade',
            'scode', 'house', 'category', 'point'
        )

class ProgramResource(resources.ModelResource):
    class Meta:
        model = Program
        import_id_fields = ('code',)
        skip_unchanged = True
        fields = (
            'code', 'name', 'mode', 'category',
            'section', 'type', 'skill', 'program_duration',
            'event_duration', 'count',
            'group_count', 'is_quiz', 'date'
        )
