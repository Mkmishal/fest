from django.db import models
from django.contrib.auth.models import User

class OnlineProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="online_profile")
    last_seen = models.DateTimeField(auto_now=True)  # Renamed to avoid confusion
    is_online = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.user.username} - {'Online' if self.is_online else 'Offline'}"


class AdminSetting(models.Model):
    key = models.CharField(max_length=25, null=True)
    value = models.CharField(max_length=25, null=True)
    section = models.CharField(max_length=25, null=True)
    category = models.CharField(max_length=25, null=True)
    type = models.CharField(max_length=25, null=True)
    skill = models.CharField(max_length=25, null=True)
    judging_conditions = models.CharField(max_length=25, null=True)
    selected_grade = models.CharField(max_length=100, null=True)
    bidding_mode = models.BooleanField(default=False)
    auction_active = models.BooleanField(default=False)
    min_bid_amount = models.IntegerField(default=1000)
    bid_confirmation_duration = models.IntegerField(default=10)
    avg_biddable_count = models.IntegerField(default=3)
    
    # Selection Round Mode fields
    selection_round_active = models.BooleanField(default=False)
    current_round = models.IntegerField(default=1)
    current_turn_step = models.IntegerField(default=0)
    leader_order = models.CharField(max_length=500, null=True, blank=True)
    candidate_registration_active = models.BooleanField(default=False)
    
    # Active auction fields
    active_bid_student_id = models.IntegerField(null=True, blank=True)
    active_bid_amount = models.IntegerField(null=True, blank=True)
    active_bid_leader_id = models.IntegerField(null=True, blank=True)
    active_bid_expires = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Selected Grade: {self.selected_grade}"

class Program(models.Model):
    code = models.CharField(max_length=10, null=True, blank=True)
    name = models.CharField(max_length=100, null=True, blank=True)
    mode = models.CharField(max_length=10, null=True, blank=True)
    category = models.CharField(max_length=20, null=True, blank=True)
    section = models.CharField(max_length=10, null=True, blank=True)
    type = models.CharField(max_length=10, null=True, blank=True)
    skill = models.CharField(max_length=100, null=True, blank=True)
    program_duration = models.CharField(max_length=2, null=True, blank=True)
    event_duration = models.CharField(max_length=3, null=True, blank=True)
    count = models.CharField(max_length=3, null=True)
    mlm_count = models.IntegerField(null=True)
    urd_count = models.IntegerField(null=True)
    group_count = models.IntegerField(null=True)
    is_quiz = models.BooleanField(null=True, blank=True)
    date = models.DateField(null=True)

    def __str__(self):
        return self.name or f"Program {self.id}"

class Student(models.Model):
    user = models.OneToOneField(User, null=True, on_delete=models.CASCADE, related_name="student")
    adno = models.CharField(max_length=5, null=True, blank=True)
    name = models.CharField(max_length=50, null=True, blank=True)
    father = models.CharField(max_length=50, null=True, blank=True)
    section = models.CharField(max_length=10, null=True, blank=True)
    locality = models.CharField(max_length=50, null=True, blank=True)
    state = models.CharField(max_length=50, null=True, blank=True)
    village = models.CharField(max_length=50, null=True, blank=True)
    grade = models.CharField(max_length=3, null=True, blank=True)
    scode = models.CharField(max_length=5, null=True, blank=True)
    house = models.CharField(max_length=50, null=True, blank=True)
    category = models.CharField(max_length=50, null=True, blank=True)
    point = models.IntegerField(null=True, blank=True)
    amount = models.IntegerField(null=True, blank=True)
    assigned_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name="assigned_students")
    assigned_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.name} ({self.adno})" if self.name else f"Student {self.id}"

class ProgramParticipant(models.Model):
    program = models.ForeignKey(Program, on_delete=models.CASCADE, related_name="program_participants", null=True)
    participant = models.ForeignKey(Student, on_delete=models.CASCADE, related_name="student_programs", null=True)

    class Meta:
        unique_together = ('program', 'participant')

    def __str__(self):
        return f"{self.participant} in {self.program}"

class ProgramJudge(models.Model):
    program = models.ForeignKey(Program, on_delete=models.CASCADE, related_name="program_judges")
    judge = models.ForeignKey(User, on_delete=models.CASCADE, related_name="judged_programs")

    class Meta:
        unique_together = ('program', 'judge')

    def __str__(self):
        return f"{self.judge.username} for {self.program}"

class Marks(models.Model):
    program = models.ForeignKey(Program, on_delete=models.CASCADE, related_name="marks")
    participant = models.ForeignKey(Student, on_delete=models.CASCADE, related_name="marks")
    judge = models.ForeignKey(User, on_delete=models.CASCADE, related_name="given_marks")
    score = models.DecimalField(max_digits=5, decimal_places=2)
    remarks = models.TextField(blank=True, null=True)

    class Meta:
        unique_together = ('program', 'participant', 'judge')

    def __str__(self):
        return f"{self.participant} - {self.program} ({self.judge.username}): {self.score}"