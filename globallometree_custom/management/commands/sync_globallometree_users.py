"""management command that
creates the askbot user account programmatically
the command can add password, but it will not create
associations with any of the federated login providers
"""
from pprint import pprint
from optparse import make_option
from django.core.management.base import BaseCommand, CommandError
from askbot import models, forms
from django.db import connections, transaction, IntegrityError

def dictfetchall(cursor):
    "Returns all rows from a cursor as a dict"
    desc = cursor.description
    return [
        dict(zip([col[0] for col in desc], row))
        for row in cursor.fetchall()
    ]

class Command(BaseCommand):
    
    help = """
        syncs globallometree users as listed in the accounts_userchanged table in the 
        globallometree database
    """

    def handle(self, *args, **options):
        
        cursor = connections['globallometree'].cursor()
        cursor.execute("SELECT DISTINCT(user_id) FROM accounts_userchanged;")
        user_list = dictfetchall(cursor)
        print "Number of users to be synced: %s" % len(user_list)

        for user_to_update in user_list:    
            try:
                try:
                    user = models.User.objects.get(id=user_to_update['user_id'])
                    is_new_user = False
                except models.User.DoesNotExist:
                    user = models.User()
                    user.id = user_to_update['user_id']
                    is_new_user = True


                cursor.execute("SELECT * FROM auth_user WHERE id=%s;", (user_to_update['user_id'],))
                
                glo_users = dictfetchall(cursor)

                if len(glo_users) == 0:
                    #deleted user
                    if not is_new_user:
                        user.is_active = False
                        user.save()
                        print "Deactivated user %s (was deleted in globallometree database)" % user.username
                else:
                    #changed user
                    glo_user = glo_users[0]

                    if not is_new_user or glo_user['is_active']:
                        user.date_joined = glo_user['date_joined']
                        user.email = glo_user['email']
                        user.first_name = glo_user['first_name']
                        user.is_active = glo_user['is_active']
                        user.is_staff = glo_user['is_staff']
                        user.is_superuser = glo_user['is_superuser']
                        user.last_name = glo_user['last_name']
                        user.password = glo_user['password']
                        user.username = glo_user['username']

                        user.save(force_insert=is_new_user)

                        print "Synced user %s" % user.username

                        if is_new_user:
                            subscription = {'subscribe': 'n'}
                            email_feeds_form = forms.SimpleEmailSubscribeForm(subscription)
                            if email_feeds_form.is_valid():
                                email_feeds_form.save(user)
                            else:
                                raise CommandError('\n'.join(email_feeds_form.errors))

                cursor.execute("DELETE FROM accounts_userchanged WHERE user_id=%s;", (user_to_update['user_id'],))
                transaction.commit_unless_managed(using="globallometree")

            except IntegrityError as e:
                print "Failed to sync user %s " %  user_to_update['user_id']
                print "Exception was %s" % e


