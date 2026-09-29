from django.apps import AppConfig
from django.db.models.signals import post_migrate

def seed(sender,**kwargs):
    from .models import SiteSettings,Product
    SiteSettings.objects.get_or_create(pk=1,defaults={
        "hero_title":"Método YouTube 360°",
        "hero_subtitle":"Da criação à monetização: desenvolva sua presença no YouTube com estratégia.",
        "instagram":"https://www.instagram.com/",
    })
    Product.objects.get_or_create(slug="metodo-youtube-360",defaults={
        "kind":"course","title":"Método YouTube 360°",
        "description":"Da criação à monetização: desenvolva sua presença no YouTube com estratégia.",
        "price":"0.00","lessons":10,"bonus":"5 bônus","featured":True,"active":True,
    })
    Product.objects.get_or_create(slug="coragem-de-falar",defaults={
        "kind":"course","title":"Coragem de Falar: O Despertar da sua Presença Autêntica",
        "description":"Encontre sua voz e dê espaço à sua expressão com mais confiança e autenticidade.",
        "price":"49.90","lessons":7,"bonus":"1 desafio final",
        "checkout_url":"https://pay.kiwify.com.br/ntgCTUk","active":True,
    })
    Product.objects.get_or_create(slug="vip-whatsapp",defaults={
        "kind":"vip","title":"VIP WhatsApp",
        "description":"Informações exclusivas sobre BTS e Jikook, novidades e conteúdos especiais da comunidade, com acesso mais próximo da Dani.",
        "price":"0.00","vip_channel":"whatsapp","active":True,
    })
    Product.objects.get_or_create(slug="vip-telegram",defaults={
        "kind":"vip","title":"VIP Telegram",
        "description":"Transmissões exclusivas, bate-papo direto com Rose, lives e outros conteúdos especiais.",
        "price":"0.00","vip_channel":"telegram","active":True,
    })

class CoreConfig(AppConfig):
    default_auto_field="django.db.models.BigAutoField"
    name="core"
    def ready(self):
        post_migrate.connect(seed,sender=self)
