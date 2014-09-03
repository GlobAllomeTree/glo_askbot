"""management command that
creates the askbot user account programmatically
the command can add password, but it will not create
associations with any of the federated login providers
"""
from pprint import pprint
from optparse import make_option
from django.core.management.base import BaseCommand, CommandError
from askbot import models, forms
from django.db import connections

def dictfetchall(cursor):
    "Returns all rows from a cursor as a dict"
    desc = cursor.description
    return [
        dict(zip([col[0] for col in desc], row))
        for row in cursor.fetchall()
    ]

class Command(BaseCommand):
    
    help = """
        syncs one or all of the globallometree users, as needed
    """


    def handle(self, *args, **options):
        
        cursor = connections['globallometree'].cursor()
        cursor.execute("SELECT * FROM auth_user")
        user_list = dictfetchall(cursor)
        print "Number of users to be synced: %s" % len(user_list)

        for glo_user in user_list:    
            try:
                user = models.User.objects.get(id=glo_user['id'])
                is_new_user = False
            except models.User.DoesNotExist:
                user = models.User()
                user.id = glo_user['id']
                is_new_user = True

            user.date_joined = glo_user['date_joined']
            user.email = glo_user['email']
            user.first_name = glo_user['first_name']
            user.is_active = glo_user['is_active']
            user.is_staff = glo_user['is_staff']
            user.is_superuser = glo_user['is_superuser']
            user.last_login = glo_user['last_login']
            user.last_name = glo_user['last_name']
            user.password = glo_user['password']
            user.username = glo_user['username']

            user.save(force_insert=is_new_user)

            if is_new_user:
                subscription = {'subscribe': 'n'}
                email_feeds_form = forms.SimpleEmailSubscribeForm(subscription)
                if email_feeds_form.is_valid():
                    email_feeds_form.save(user)
                else:
                    raise CommandError('\n'.join(email_feeds_form.errors))
