from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError

class OnlineProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="online_profile")
    last_seen = models.DateTimeField(auto_now=True)  # Renamed to avoid confusion
    is_online = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.user.username} - {'Online' if self.is_online else 'Offline'}"


class FestConfiguration(models.Model):
    bidding_mode = models.BooleanField(default=False)
    auction_active = models.BooleanField(default=False)
    min_bid_amount = models.IntegerField(default=1000)
    bid_confirmation_duration = models.IntegerField(default=10)
    avg_biddable_count = models.IntegerField(default=3)
    selection_round_active = models.BooleanField(default=False)
    current_round = models.IntegerField(default=1)
    current_turn_step = models.IntegerField(default=0)
    leader_order = models.CharField(max_length=500, null=True, blank=True)
    candidate_registration_active = models.BooleanField(default=False)
    selected_grade = models.CharField(max_length=100, null=True, blank=True)
    judging_conditions = models.TextField(null=True, blank=True)

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Fest Configuration (Round: {self.current_round}, Bidding: {self.bidding_mode})"


class SystemSetting(models.Model):
    SETTING_TYPES = [
        ('CATEGORY', 'Category'),
        ('SKILL', 'Skill'),
        ('TYPE', 'Program Type'),
        ('MODE', 'Program Mode'),
        ('HOUSE', 'House'),
        ('FEST_NAME', 'Fest Name'),
        ('OTHER', 'Other')
    ]
    setting_type = models.CharField(max_length=50, choices=SETTING_TYPES)
    key = models.CharField(max_length=50)
    value = models.CharField(max_length=100)

    def __str__(self):
        return f"[{self.setting_type}] {self.key} = {self.value}"

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
    group_count = models.IntegerField(null=True)
    is_quiz = models.BooleanField(null=True, blank=True)
    date = models.DateField(null=True, blank=True)
    language = models.CharField(max_length=20, null=True, blank=True)
    is_multilingual = models.BooleanField(default=False)
    start_time = models.TimeField(null=True, blank=True)
    end_time = models.TimeField(null=True, blank=True)
    min_participants = models.IntegerField(default=1, null=True, blank=True)
    max_participants = models.IntegerField(default=1, null=True, blank=True)
    max_entries_per_house = models.IntegerField(null=True, blank=True, help_text="Max participants/teams a single house can send to this program")

    def __str__(self):
        return self.name or f"Program {self.id}"

class ProgramSectionCount(models.Model):
    program = models.ForeignKey(Program, on_delete=models.CASCADE, related_name='section_counts')
    section = models.CharField(max_length=50)
    count = models.IntegerField(default=0)

    class Meta:
        unique_together = ('program', 'section')

    def __str__(self):
        return f"{self.program.name} - {self.section}: {self.count}"

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


class LiveAuctionState(models.Model):
    student = models.OneToOneField(Student, on_delete=models.CASCADE, related_name='auction_state')
    current_highest_amount = models.IntegerField(default=0)
    current_highest_bidder = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)
    expires_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=False)

    def __str__(self):
        return f"Auction for {self.student.name}: {self.current_highest_amount} by {self.current_highest_bidder.username if self.current_highest_bidder else 'None'}"


class BidLog(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='bids')
    leader = models.ForeignKey(User, on_delete=models.CASCADE)
    amount = models.IntegerField()
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Bid of {self.amount} for {self.student.name} by {self.leader.username} at {self.timestamp}"


class ParticipationRule(models.Model):
    category = models.CharField(max_length=50)
    program_type = models.CharField(max_length=10, null=True, blank=True)
    program_mode = models.CharField(max_length=10, null=True, blank=True)
    language = models.CharField(max_length=20, null=True, blank=True)
    is_multilingual = models.BooleanField(null=True, blank=True)
    skill = models.CharField(max_length=50, null=True, blank=True)
    role = models.CharField(max_length=20, null=True, blank=True)
    min_count = models.IntegerField(default=0)
    max_count = models.IntegerField()

    def __str__(self):
        parts = [f"Category '{self.category}'"]
        if self.program_type:
            parts.append(f"Type: {self.program_type}")
        if self.program_mode:
            parts.append(f"Mode: {self.program_mode}")
        if self.language:
            parts.append(f"Language: {self.language}")
        if self.is_multilingual is not None:
            parts.append(f"Multilingual: {self.is_multilingual}")
        if self.skill:
            parts.append(f"Skill: {self.skill}")
        if self.role:
            parts.append(f"Role: {self.role}")
        return f"Rule: " + " | ".join(parts) + f" | Min: {self.min_count} | Max: {self.max_count}"

class ProgramParticipant(models.Model):
    program = models.ForeignKey(Program, on_delete=models.CASCADE, related_name="program_participants", null=True)
    participant = models.ForeignKey(Student, on_delete=models.CASCADE, related_name="student_programs", null=True)
    role = models.CharField(max_length=20, default='Participant')

    class Meta:
        unique_together = ('program', 'participant')

    def clean(self):
        super().clean()
        if not self.participant or not self.program:
            return



        # 2. House Quota Check
        house_limit = None
        if self.program.max_entries_per_house is not None:
            house_limit = self.program.max_entries_per_house
        elif self.program.count and self.program.count.isdigit():
            house_limit = int(self.program.count)

        if house_limit is not None and self.participant.house:
            house_query = ProgramParticipant.objects.filter(
                program=self.program,
                participant__house=self.participant.house
            )
            if self.pk:
                house_query = house_query.exclude(pk=self.pk)
            if house_query.count() >= house_limit:
                raise ValidationError(
                    f"House '{self.participant.house}' has reached the maximum entry limit of "
                    f"{house_limit} for the program '{self.program.name}'."
                )

        # 3. Time/Schedule Clash Check
        if self.program.date and self.program.start_time and self.program.end_time:
            clash_query = ProgramParticipant.objects.filter(
                participant=self.participant,
                program__date=self.program.date,
                program__start_time__isnull=False,
                program__end_time__isnull=False
            )
            if self.pk:
                clash_query = clash_query.exclude(pk=self.pk)
            for p in clash_query:
                if self.program.start_time < p.program.end_time and p.program.start_time < self.program.end_time:
                    raise ValidationError(
                        f"Schedule clash! Student {self.participant.name} is already registered in "
                        f"'{p.program.name}' which overlaps in time ({p.program.start_time} - {p.program.end_time})."
                    )

        # 4. Expanded Participation Rules Checks
        student_category = self.participant.category
        if student_category:
            rules = ParticipationRule.objects.filter(category__iexact=student_category)
            
            for rule in rules:
                # Check if current program & role match the rule's criteria
                p_type = self.program.type.lower() if self.program.type else ""
                r_type = rule.program_type.lower() if rule.program_type else ""
                if p_type in ("single", "individual"): p_type = "single"
                if r_type in ("single", "individual"): r_type = "single"
                type_matches = not rule.program_type or (p_type == r_type)
                
                mode_matches = not rule.program_mode or (self.program.mode and self.program.mode.lower() == rule.program_mode.lower())
                lang_matches = not rule.language or (self.program.language and self.program.language.lower() == rule.language.lower())
                multi_matches = rule.is_multilingual is None or (self.program.is_multilingual == rule.is_multilingual)
                skill_matches = not rule.skill or (self.program.skill and self.program.skill.lower() == rule.skill.lower())
                role_matches = not rule.role or (self.role and self.role.lower() == rule.role.lower())
                
                if type_matches and mode_matches and lang_matches and multi_matches and skill_matches and role_matches:
                    # Count current participant assignments matching the rule criteria
                    query = ProgramParticipant.objects.filter(participant=self.participant)
                    if self.pk:
                        query = query.exclude(pk=self.pk)
                    
                    current_count = 0
                    for p in query:
                        p_t = p.program.type.lower() if p.program.type else ""
                        r_t = rule.program_type.lower() if rule.program_type else ""
                        if p_t in ("single", "individual"): p_t = "single"
                        if r_t in ("single", "individual"): r_t = "single"
                        p_type_matches = not rule.program_type or (p_t == r_t)
                        
                        p_mode_matches = not rule.program_mode or (p.program.mode and p.program.mode.lower() == rule.program_mode.lower())
                        p_lang_matches = not rule.language or (p.program.language and p.program.language.lower() == rule.language.lower())
                        p_multi_matches = rule.is_multilingual is None or (p.program.is_multilingual == rule.is_multilingual)
                        p_skill_matches = not rule.skill or (p.program.skill and p.program.skill.lower() == rule.skill.lower())
                        p_role_matches = not rule.role or (p.role and p.role.lower() == rule.role.lower())
                        
                        if p_type_matches and p_mode_matches and p_lang_matches and p_multi_matches and p_skill_matches and p_role_matches:
                            current_count += 1
                    
                    if current_count >= rule.max_count:
                        desc_parts = []
                        if rule.program_type: desc_parts.append(f"type='{rule.program_type}'")
                        if rule.program_mode: desc_parts.append(f"mode='{rule.program_mode}'")
                        if rule.language: desc_parts.append(f"language='{rule.language}'")
                        if rule.is_multilingual is not None: desc_parts.append(f"multilingual={rule.is_multilingual}")
                        if rule.skill: desc_parts.append(f"skill='{rule.skill}'")
                        if rule.role: desc_parts.append(f"role='{rule.role}'")
                        desc = ", ".join(desc_parts) or "overall limits"
                        raise ValidationError(
                            f"Student {self.participant.name} cannot participate in {self.program.name}. "
                            f"This exceeds the maximum limit of {rule.max_count} programs for category '{self.participant.category}' "
                            f"with {desc}."
                        )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

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