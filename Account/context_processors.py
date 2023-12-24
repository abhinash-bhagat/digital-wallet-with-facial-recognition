from Account.models import Account

def user_profile_context(request):
    user_profile = None
    if request.user.is_authenticated:
        user_profile = Account.objects.get_or_create(user=request.user)[0]
    return {'user_profile': user_profile}
