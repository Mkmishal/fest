"""
URL configuration for housing project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from controller import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('',views.website, name='webpage'),
    path('login/', views.login, name="login"),
    path('logout/', views.logout, name="logout"),
    path('edit_password', views.edit_password, name='edit_password'),
    path('dashboard/',views.dashboard,name='dashboard'),
    path('program/',views.program,name='program'),
    path('timetable/',views.timetable,name='timetable'),
    path('users/', views.users , name="users"),
    path('auction/', views.auction, name="auction"),
    path('participants/', views.participants, name="participants"),
    path("assign-student/", views.assign_student, name="assign_student"),
    path("skip-turn/", views.skip_turn, name="skip_turn"),
    path('ajax/unassigned-students/', views.get_unassigned_students, name='unassigned_students_partial'),
    path('clear-house-assignments/', views.clear_house_assignments, name='clear_house_assignments'),
    path("grouped-students-partial/", views.grouped_students_partial, name="grouped_students_partial"),

    #User management
    path('createuser/', views.create_user, name='create_user'),
    path('import-users/', views.import_users, name='import_users'),
    path('export-user-template/', views.dummy_export_excel, name='dummy_export_excel'),
    path('delete-user/<int:user_id>/', views.delete_user, name='delete_user'),
    path('edit-user/<int:user_id>/', views.edit_user, name='edit_user'),
    path('delete-participant/<int:user_id>/', views.delete_participant, name='delete_participant'),
    path('export/students/excel/', views.export_students_excel, name='export_students_excel'),

    # Student management
    path('student/add/', views.add_student, name='add_student'),
    path('student/edit/<int:student_id>/', views.edit_student, name='edit_student'),
    path('student/import/', views.import_students, name='import_students'),
    path('student/export-template/', views.export_students_template, name='export_students_template'),

    # Admin settings management
    path('admin-settings/add/', views.add_setting, name='add_setting'),
    path('admin-settings/edit/<int:setting_id>/', views.edit_setting, name='edit_setting'),
    path('admin-settings/delete/<int:setting_id>/', views.delete_setting, name='delete_setting'),
    path('rule/add/', views.add_rule, name='add_rule'),
    path('rule/edit/<int:rule_id>/', views.edit_rule, name='edit_rule'),
    path('rule/delete/<int:rule_id>/', views.delete_rule, name='delete_rule'),

    # Program management
    path('program/add/', views.add_program, name='add_program'),
    path('program/edit/<int:program_id>/', views.edit_program, name='edit_program'),
    path('program/delete/<int:program_id>/', views.delete_program, name='delete_program'),
    path('program/import/', views.import_programs, name='import_programs'),
    path('program/export-template/', views.export_programs_template, name='export_programs_template'),

    #grouping setup
    path('group/', views.group, name='group'),
    path("assign-students/", views.assign_students, name="assign_students"),
    path('utilities/', views.utilities, name='utilities'),
]
