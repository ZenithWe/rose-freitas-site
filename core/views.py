import secrets
from xml.etree.ElementTree import Element, SubElement, tostring
from datetime import timedelta
from decimal import Decimal
from django.contrib import messages
from django.contrib.auth.hashers import make_password,check_password
from django.core.mail import send_mail
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Prefetch, Sum
from django.db import transaction
from django.db.models.deletion import ProtectedError
from django.http import HttpResponse, Http404
from django.shortcuts import get_object_or_404,redirect,render
from django.utils import timezone
from django.conf import settings
from django.urls import reverse
from django.views.decorators.http import require_POST, require_safe
from django.views.decorators.cache import never_cache
from .models import SiteSettings,Banner,Product,Material,VipRequest,Order,CustomerAccess,CustomerLoginCode,AgendaItem,Expense
from .forms import ProductForm,VipRequestForm,BannerForm,AgendaForm,ExpenseForm,SettingsForm,OrderForm,CustomerAccessForm
from .images import product_image

def site_settings():
    return SiteSettings.objects.get_or_create(pk=1)[0]

def product_queryset():
    return Product.objects.select_related("uploaded_cover").defer("uploaded_cover__data")

def home(request):
    return render(request,"core/home.html",{
        "site":site_settings(),
        "banners":Banner.objects.filter(active=True),
        "courses":product_queryset().filter(active=True,kind="course"),
        "products":product_queryset().filter(active=True,kind__in=["product","subscription"]),
        "vips":product_queryset().filter(active=True,kind="vip"),
        "agenda":AgendaItem.objects.filter(active=True,starts_at__gte=timezone.now())[:4],
    })

def catalog(request):
    return render(request,"core/catalog.html",{
        "site":site_settings(),
        "courses":product_queryset().filter(active=True,kind="course"),
        "products":product_queryset().filter(active=True,kind__in=["product","subscription"]),
    })

def vip(request):
    return render(request,"core/vip.html",{
        "site":site_settings(),
        "vips":product_queryset().filter(active=True,kind="vip"),
    })

def affiliates(request):
    return render(request,"core/affiliates.html",{
        "site":site_settings(),
        "courses":product_queryset().filter(active=True,kind="course"),
        "products":product_queryset().filter(active=True,kind__in=["product","subscription"]),
    })

def partnerships(request):
    return render(request,"core/partnerships.html",{"site":site_settings()})

@require_safe
def robots(request):
    sitemap_url = request.build_absolute_uri(reverse("sitemap"))
    body = "User-agent: *\nAllow: /\nDisallow: /admin/\nDisallow: /painel/\nDisallow: /area-do-cliente/\nDisallow: /vip/sucesso/\nSitemap: " + sitemap_url + "\n"
    return HttpResponse(body,content_type="text/plain; charset=utf-8")

@require_safe
def sitemap(request):
    root = Element("urlset",xmlns="http://www.sitemaps.org/schemas/sitemap/0.9")
    for name in ("home", "catalog", "vip", "affiliates", "partnerships"):
        node = SubElement(root,"url")
        SubElement(node,"loc").text = request.build_absolute_uri(reverse(name))
    for product in Product.objects.filter(active=True):
        node = SubElement(root,"url")
        SubElement(node,"loc").text = request.build_absolute_uri(reverse("product_detail",kwargs={"slug":product.slug}))
        SubElement(node,"lastmod").text = product.updated_at.date().isoformat()
    return HttpResponse(tostring(root,encoding="utf-8",xml_declaration=True),content_type="application/xml; charset=utf-8")

def product_detail(request,slug):
    product=get_object_or_404(product_queryset(),slug=slug,active=True)
    image_absolute_url=request.build_absolute_uri(product.image_url) if product.image_url else ""
    return render(request,"core/product_detail.html",{"site":site_settings(),"product":product,"image_absolute_url":image_absolute_url})

def vip_request(request,slug):
    product=get_object_or_404(product_queryset(),slug=slug,active=True,kind="vip")
    form=VipRequestForm(request.POST or None)
    if request.method=="POST" and form.is_valid():
        item=form.save(commit=False)
        item.channel=product.vip_channel or "whatsapp"
        item.save()
        receipts = request.session.get("vip_receipts", {})
        receipts[str(item.pk)] = product.pk
        request.session["vip_receipts"] = dict(list(receipts.items())[-10:])
        return redirect("vip_success",pk=item.pk)
    return render(request,"core/vip_request.html",{"site":site_settings(),"product":product,"form":form})

@never_cache
def vip_success(request,pk):
    product_id = request.session.get("vip_receipts", {}).get(str(pk))
    if product_id is None:
        raise Http404
    item=get_object_or_404(VipRequest,pk=pk)
    product=product_queryset().filter(pk=product_id).first()
    return render(request,"core/vip_success.html",{"site":site_settings(),"item":item,"product":product})

@never_cache
def customer_area(request):
    if request.method=="POST":
        action=request.POST.get("action","request")
        if action=="logout":
            request.session.pop("customer_verified",None)
            request.session.pop("pending_customer_email",None)
            request.session.pop("customer_code_attempts",None)
            request.session.cycle_key()
            return redirect("customer_area")
        if action=="request":
            email=(request.POST.get("email") or "").strip().lower()
            try:
                validate_email(email)
                if len(email) > 254:
                    raise ValidationError("E-mail muito longo.")
            except ValidationError:
                messages.error(request,"Informe um e-mail válido.")
                return redirect("customer_area")
            request.session["pending_customer_email"]=email
            code = None
            # The existing access row serializes resends for an e-mail on PostgreSQL.
            with transaction.atomic():
                access = CustomerAccess.objects.select_for_update().filter(email__iexact=email,active=True).order_by("pk").first()
                recent = CustomerLoginCode.objects.filter(email__iexact=email,created_at__gt=timezone.now()-timedelta(seconds=60)).exists()
                if access and not recent:
                    code=f"{secrets.randbelow(1000000):06d}"
                    CustomerLoginCode.objects.filter(email__iexact=email,used=False).update(used=True)
                    CustomerLoginCode.objects.create(email=email,code_hash=make_password(code),expires_at=timezone.now()+timedelta(minutes=10))
            if code is not None:
                send_mail("Seu código de acesso • Rose Freitas",f"Seu código de acesso é {code}. Ele expira em 10 minutos.",settings.DEFAULT_FROM_EMAIL,[email],fail_silently=True)
            messages.success(request,"Se o e-mail tiver acesso liberado, um código foi enviado.")
            return redirect("customer_area")
        if action=="verify":
            email=request.session.get("pending_customer_email","")
            code=(request.POST.get("code") or "").strip()
            item=CustomerLoginCode.objects.filter(email__iexact=email,used=False,expires_at__gt=timezone.now()).first()
            attempts = request.session.get("customer_code_attempts", {})
            session_attempts = attempts.get("count", 0) if item and attempts.get("code_id") == item.pk else 0
            cache_key = f"customer-code-attempts:{item.pk}" if item else None
            cached_attempts = cache.get(cache_key, 0) if cache_key else 0
            valid = item and max(session_attempts,cached_attempts) < 5 and len(code)==6 and code.isascii() and code.isdigit() and check_password(code,item.code_hash)
            active_access = CustomerAccess.objects.filter(email__iexact=email,active=True).exists() if valid else False
            consumed = CustomerLoginCode.objects.filter(pk=item.pk,used=False,expires_at__gt=timezone.now()).update(used=True) if active_access else 0
            if consumed:
                request.session.cycle_key()
                request.session["customer_verified"]=email
                request.session.pop("pending_customer_email",None)
                request.session.pop("customer_code_attempts",None)
                cache.delete(cache_key)
                return redirect("customer_area")
            if item:
                timeout=max(1,int((item.expires_at-timezone.now()).total_seconds()))
                cache.add(cache_key,0,timeout=timeout)
                try:
                    cached_attempts=cache.incr(cache_key)
                except ValueError:
                    cached_attempts=1
                    cache.set(cache_key,cached_attempts,timeout=timeout)
                session_attempts+=1
                request.session["customer_code_attempts"]={"code_id":item.pk,"count":session_attempts}
                if max(session_attempts,cached_attempts)>=5:
                    CustomerLoginCode.objects.filter(pk=item.pk,used=False).update(used=True)
            messages.error(request,"Código inválido ou expirado. Solicite um novo código se necessário.")
            return redirect("customer_area")
    email=request.session.get("customer_verified","")
    pending_email=request.session.get("pending_customer_email","")
    accesses=CustomerAccess.objects.filter(email__iexact=email,active=True).select_related("product","product__uploaded_cover").defer("product__uploaded_cover__data").prefetch_related(Prefetch("product__materials",queryset=Material.objects.filter(active=True),to_attr="available_materials")) if email else []
    return render(request,"core/customer_area.html",{"site":site_settings(),"accesses":accesses,"email":email,"pending_email":pending_email})

@staff_member_required(login_url="/painel/entrar/")
def dashboard(request):
    paid=Order.objects.filter(status="paid")
    revenue=paid.aggregate(v=Sum("total"))["v"] or Decimal("0")
    expenses=Expense.objects.aggregate(v=Sum("amount"))["v"] or Decimal("0")
    return render(request,"panel/dashboard.html",{
        "revenue":revenue,"expenses":expenses,"balance":revenue-expenses,
        "orders_count":Order.objects.count(),"customers_count":CustomerAccess.objects.values("email").distinct().count(),
        "vip_pending":VipRequest.objects.filter(status="pending").count(),
        "latest_orders":Order.objects.select_related("product")[:6],
        "latest_vip":VipRequest.objects.all()[:6],
        "upcoming_agenda":AgendaItem.objects.filter(active=True,starts_at__gte=timezone.now())[:4],
        "upcoming_agenda_count":AgendaItem.objects.filter(active=True,starts_at__gte=timezone.now()).count(),
    })

@staff_member_required(login_url="/painel/entrar/")
def products(request):
    return render(request,"panel/products.html",{"items":product_queryset()})

@staff_member_required(login_url="/painel/entrar/")
def product_form(request,pk=None):
    obj=get_object_or_404(product_queryset(),pk=pk) if pk else None
    form=ProductForm(request.POST or None,request.FILES or None,instance=obj)
    if request.method=="POST" and form.is_valid():
        form.save(); messages.success(request,"Produto salvo."); return redirect("panel_products")
    return render(request,"panel/form.html",{"form":form,"title":"Editar produto" if obj else "Novo produto"})

@staff_member_required(login_url="/painel/entrar/")
@require_POST
def product_delete(request,pk):
    product=get_object_or_404(Product,pk=pk)
    if product.orders.exists() or product.accesses.exists():
        product.active=False
        product.save(update_fields=["active","updated_at"])
        messages.success(request,"Produto desativado. O histórico de pedidos e os acessos foram preservados.")
    else:
        try:
            product.delete()
            messages.success(request,"Produto excluído.")
        except ProtectedError:
            product.active=False
            product.save(update_fields=["active","updated_at"])
            messages.success(request,"Produto desativado para preservar o histórico de pedidos.")
    return redirect("panel_products")

@staff_member_required(login_url="/painel/entrar/")
def vip_requests(request):
    channel=request.GET.get("canal","")
    qs=VipRequest.objects.all()
    if channel in ["whatsapp","telegram"]: qs=qs.filter(channel=channel)
    return render(request,"panel/vip_requests.html",{"items":qs,"channel":channel})

@staff_member_required(login_url="/painel/entrar/")
@require_POST
def vip_status(request,pk,status):
    item=get_object_or_404(VipRequest,pk=pk)
    if status in ["pending","confirmed","cancelled"]:
        item.status=status; item.save(update_fields=["status","updated_at"])
    return redirect("panel_vip")

@staff_member_required(login_url="/painel/entrar/")
def banners(request):
    return render(request,"panel/banners.html",{"items":Banner.objects.all()})

@staff_member_required(login_url="/painel/entrar/")
def banner_form(request,pk=None):
    obj=get_object_or_404(Banner,pk=pk) if pk else None
    form=BannerForm(request.POST or None,instance=obj)
    if request.method=="POST" and form.is_valid():
        form.save(); messages.success(request,"Banner salvo."); return redirect("panel_banners")
    return render(request,"panel/form.html",{"form":form,"title":"Editar banner" if obj else "Novo banner"})

@staff_member_required(login_url="/painel/entrar/")
def agenda(request):
    return render(request,"panel/agenda.html",{"items":AgendaItem.objects.all()})

@staff_member_required(login_url="/painel/entrar/")
def agenda_form(request,pk=None):
    obj=get_object_or_404(AgendaItem,pk=pk) if pk else None
    form=AgendaForm(request.POST or None,instance=obj)
    if request.method=="POST" and form.is_valid():
        form.save(); messages.success(request,"Item da agenda salvo."); return redirect("panel_agenda")
    return render(request,"panel/form.html",{"form":form,"title":"Editar agenda" if obj else "Novo item da agenda"})

@staff_member_required(login_url="/painel/entrar/")
def orders(request):
    return render(request,"panel/orders.html",{"items":Order.objects.select_related("product")})

@staff_member_required(login_url="/painel/entrar/")
@transaction.atomic
def order_form(request,pk):
    obj=get_object_or_404(Order,pk=pk)
    form=OrderForm(request.POST or None,instance=obj)
    if request.method=="POST" and form.is_valid():
        order=form.save(commit=False)
        if order.status=="paid" and not order.paid_at: order.paid_at=timezone.now()
        order.save()
        if order.status=="paid":
            access=CustomerAccess.objects.filter(email__iexact=order.email,product=order.product).first()
            if access:
                if not access.active:
                    access.active=True
                    access.save(update_fields=["active"])
            else:
                CustomerAccess.objects.get_or_create(email=order.email,product=order.product,defaults={"active":True})
        messages.success(request,"Pedido atualizado."); return redirect("panel_orders")
    return render(request,"panel/form.html",{"form":form,"title":"Editar pedido"})

@staff_member_required(login_url="/painel/entrar/")
def customers(request):
    return render(request,"panel/customers.html",{"items":CustomerAccess.objects.select_related("product").order_by("-created_at")})

@staff_member_required(login_url="/painel/entrar/")
def customer_form(request):
    form=CustomerAccessForm(request.POST or None)
    if request.method=="POST" and form.is_valid():
        form.save(); messages.success(request,"Acesso liberado."); return redirect("panel_customers")
    return render(request,"panel/form.html",{"form":form,"title":"Liberar acesso"})

@staff_member_required(login_url="/painel/entrar/")
def finance(request):
    revenue=Order.objects.filter(status="paid").aggregate(v=Sum("total"))["v"] or Decimal("0")
    expenses=Expense.objects.aggregate(v=Sum("amount"))["v"] or Decimal("0")
    return render(request,"panel/finance.html",{"revenue":revenue,"expenses":expenses,"balance":revenue-expenses,"items":Expense.objects.all()[:30]})

@staff_member_required(login_url="/painel/entrar/")
def expense_form(request):
    form=ExpenseForm(request.POST or None)
    if request.method=="POST" and form.is_valid():
        form.save(); messages.success(request,"Despesa registrada."); return redirect("panel_finance")
    return render(request,"panel/form.html",{"form":form,"title":"Nova despesa"})

@staff_member_required(login_url="/painel/entrar/")
def settings_view(request):
    obj=site_settings()
    form=SettingsForm(request.POST or None,instance=obj)
    if request.method=="POST" and form.is_valid():
        form.save(); messages.success(request,"Configurações salvas."); return redirect("panel_settings")
    return render(request,"panel/form.html",{"form":form,"title":"Configurações do site"})
