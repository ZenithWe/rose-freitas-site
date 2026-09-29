import os
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help="Cria/atualiza o administrador a partir de variáveis de ambiente."
    def handle(self,*args,**kwargs):
        username=os.getenv("ADMIN_USERNAME","")
        password=os.getenv("ADMIN_PASSWORD","")
        email=os.getenv("ADMIN_EMAIL","")
        if not username or not password:
            self.stdout.write("ADMIN_USERNAME/ADMIN_PASSWORD ausentes; admin não alterado.")
            return
        User=get_user_model()
        user,_=User.objects.get_or_create(username=username,defaults={"email":email,"is_staff":True,"is_superuser":True})
        user.email=email or user.email
        user.is_staff=True
        user.is_superuser=True
        user.set_password(password)
        user.save()
        self.stdout.write(self.style.SUCCESS("Administrador configurado."))
