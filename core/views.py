from decimal import Decimal
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Sum
from django.shortcuts import get_object_or_404,redirect,render
from django.utils import timezone
from django.views.decorators.http import require_POST
from .models import SiteSettings,Banner,Product,VipRequest,Order,CustomerAccess,AgendaItem,Expense
from .forms import ProductForm,VipRequestForm,BannerForm,AgendaForm,ExpenseForm,SettingsForm,OrderForm,CustomerAccessForm

def site_settings():
    return SiteSettings.objects.get_or_create(pk=1)[0]

def home(request):
    return render(request,"core/home.html",{
        "site":site_settings(),
        "banners":Banner.objects.filter(active=True),
        "courses":Product.objects.filter(active=True,kind="course"),
        "vips":Product.objects.filter(active=True,kind="vip"),
        "agenda":AgendaItem.objects.filter(active=True,starts_at__gte=timezone.now())[:4],
    })

def product_detail(request,slug):
    product=get_object_or_404(Product,slug=slug,active=True)
    return render(request,"core/product_detail.html",{"site":site_settings(),"product":product})

def vip_request(request,slug):
    product=get_object_or_404(Product,slug=slug,active=True,kind="vip")
    form=VipRequestForm(request.POST or None)
    if request.method=="POST" and form.is_valid():
        item=form.save(commit=False)
        item.channel=product.vip_channel or "whatsapp"
        item.save()
        return redirect("vip_success",pk=item.pk)
    return render(request,"core/vip_request.html",{"site":site_settings(),"product":product,"form":form})

def vip_success(request,pk):
    item=get_object_or_404(VipRequest,pk=pk)
    return render(request,"core/vip_success.html",{"site":site_settings(),"item":item})

def customer_area(request):
    email=(request.POST.get("email") or "").strip().lower()
    accesses=[]
    if request.method=="POST":
        accesses=CustomerAccess.objects.filter(email__iexact=email,active=True).select_related("product").prefetch_related("product__materials")
        if not accesses: messages.warning(request,"Nenhum acesso ativo foi encontrado para esse e-mail.")
    return render(request,"core/customer_area.html",{"site":site_settings(),"accesses":accesses,"email":email})

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
    })

@staff_member_required(login_url="/painel/entrar/")
def products(request):
    return render(request,"panel/products.html",{"items":Product.objects.all()})

@staff_member_required(login_url="/painel/entrar/")
def product_form(request,pk=None):
    obj=get_object_or_404(Product,pk=pk) if pk else None
    form=ProductForm(request.POST or None,instance=obj)
    if request.method=="POST" and form.is_valid():
        form.save(); messages.success(request,"Produto salvo."); return redirect("panel_products")
    return render(request,"panel/form.html",{"form":form,"title":"Editar produto" if obj else "Novo produto"})

@staff_member_required(login_url="/painel/entrar/")
@require_POST
def product_delete(request,pk):
    get_object_or_404(Product,pk=pk).delete()
    messages.success(request,"Produto excluído.")
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
def order_form(request,pk):
    obj=get_object_or_404(Order,pk=pk)
    form=OrderForm(request.POST or None,instance=obj)
    if request.method=="POST" and form.is_valid():
        order=form.save(commit=False)
        if order.status=="paid" and not order.paid_at: order.paid_at=timezone.now()
        order.save()
        if order.status=="paid":
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
