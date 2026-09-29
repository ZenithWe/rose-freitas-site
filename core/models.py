import secrets
from decimal import Decimal
from django.db import models
from django.utils.text import slugify

class SiteSettings(models.Model):
    id=models.PositiveSmallIntegerField(primary_key=True,default=1,editable=False)
    hero_title=models.CharField(max_length=180,default="Rose Freitas")
    hero_subtitle=models.CharField(max_length=400,blank=True)
    hero_button=models.CharField(max_length=80,default="Conheça meus conteúdos")
    instagram=models.URLField(blank=True)
    youtube=models.URLField(blank=True)
    tiktok=models.URLField(blank=True)
    whatsapp=models.CharField(max_length=20,blank=True)
    partnership_whatsapp=models.CharField(max_length=20,blank=True)
    pix_key=models.CharField(max_length=120,blank=True)
    pix_name=models.CharField(max_length=120,blank=True)
    updated_at=models.DateTimeField(auto_now=True)
    def save(self,*args,**kwargs):
        self.pk=1
        super().save(*args,**kwargs)
    def __str__(self): return "Configurações da Rose"

class Banner(models.Model):
    title=models.CharField(max_length=160)
    subtitle=models.CharField(max_length=320,blank=True)
    image_url=models.URLField(blank=True)
    button_text=models.CharField(max_length=60,default="Saiba mais")
    link=models.CharField(max_length=500,default="/")
    active=models.BooleanField(default=True)
    position=models.PositiveSmallIntegerField(default=0)
    class Meta: ordering=["position","id"]
    def __str__(self): return self.title

class Product(models.Model):
    KINDS=[("course","Curso"),("vip","VIP"),("product","Produto")]
    CHANNELS=[("","—"),("whatsapp","WhatsApp"),("telegram","Telegram")]
    kind=models.CharField(max_length=12,choices=KINDS,default="course")
    title=models.CharField(max_length=180)
    slug=models.SlugField(max_length=190,unique=True,blank=True)
    description=models.TextField(max_length=4000)
    price=models.DecimalField(max_digits=10,decimal_places=2,default=Decimal("0.00"))
    lessons=models.PositiveSmallIntegerField(default=0)
    bonus=models.CharField(max_length=120,blank=True)
    cover_url=models.URLField(blank=True)
    checkout_url=models.URLField(blank=True)
    vip_channel=models.CharField(max_length=12,choices=CHANNELS,blank=True)
    featured=models.BooleanField(default=False)
    active=models.BooleanField(default=True)
    created_at=models.DateTimeField(auto_now_add=True)
    updated_at=models.DateTimeField(auto_now=True)
    class Meta: ordering=["-featured","id"]
    def save(self,*args,**kwargs):
        if not self.slug: self.slug=slugify(self.title)[:180]
        super().save(*args,**kwargs)
    def __str__(self): return self.title

class Material(models.Model):
    product=models.ForeignKey(Product,on_delete=models.CASCADE,related_name="materials")
    title=models.CharField(max_length=180)
    url=models.URLField()
    active=models.BooleanField(default=True)
    position=models.PositiveSmallIntegerField(default=0)
    class Meta: ordering=["position","id"]
    def __str__(self): return f"{self.product} • {self.title}"

class VipRequest(models.Model):
    STATUSES=[("pending","Pendente"),("confirmed","Confirmado"),("cancelled","Cancelado")]
    CHANNELS=[("whatsapp","WhatsApp"),("telegram","Telegram")]
    channel=models.CharField(max_length=12,choices=CHANNELS)
    full_name=models.CharField(max_length=160)
    phone=models.CharField(max_length=20)
    email=models.EmailField(blank=True)
    status=models.CharField(max_length=12,choices=STATUSES,default="pending")
    note=models.CharField(max_length=400,blank=True)
    created_at=models.DateTimeField(auto_now_add=True)
    updated_at=models.DateTimeField(auto_now=True)
    class Meta: ordering=["-created_at"]
    def __str__(self): return f"{self.full_name} • {self.get_channel_display()}"

class Order(models.Model):
    STATUSES=[("pending","Aguardando"),("paid","Confirmado"),("cancelled","Cancelado"),("refunded","Reembolsado")]
    token=models.CharField(max_length=64,unique=True,editable=False,default=lambda:secrets.token_urlsafe(24))
    product=models.ForeignKey(Product,on_delete=models.PROTECT,related_name="orders")
    customer_name=models.CharField(max_length=160)
    email=models.EmailField()
    phone=models.CharField(max_length=20,blank=True)
    total=models.DecimalField(max_digits=10,decimal_places=2)
    status=models.CharField(max_length=12,choices=STATUSES,default="pending")
    created_at=models.DateTimeField(auto_now_add=True)
    paid_at=models.DateTimeField(null=True,blank=True)
    class Meta: ordering=["-created_at"]
    def __str__(self): return f"{self.customer_name} • {self.product}"

class CustomerAccess(models.Model):
    email=models.EmailField()
    product=models.ForeignKey(Product,on_delete=models.CASCADE,related_name="accesses")
    active=models.BooleanField(default=True)
    created_at=models.DateTimeField(auto_now_add=True)
    class Meta:
        constraints=[models.UniqueConstraint(fields=["email","product"],name="unique_customer_product")]
    def __str__(self): return f"{self.email} • {self.product}"

class AgendaItem(models.Model):
    KINDS=[("live","Live"),("release","Lançamento"),("event","Evento"),("other","Outro")]
    title=models.CharField(max_length=180)
    kind=models.CharField(max_length=12,choices=KINDS,default="other")
    starts_at=models.DateTimeField()
    description=models.CharField(max_length=500,blank=True)
    active=models.BooleanField(default=True)
    class Meta: ordering=["starts_at"]
    def __str__(self): return self.title

class Expense(models.Model):
    description=models.CharField(max_length=180)
    amount=models.DecimalField(max_digits=10,decimal_places=2)
    date=models.DateField()
    created_at=models.DateTimeField(auto_now_add=True)
    class Meta: ordering=["-date","-id"]
    def __str__(self): return self.description
