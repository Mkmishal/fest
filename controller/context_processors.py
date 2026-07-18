from django.contrib.auth.models import Group

def user_groups(request):
    if request.user.is_authenticated:
        return {
            'groups': list(request.user.groups.values_list('name', flat=True))
        }
    return {'groups': []}
