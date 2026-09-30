from urllib.parse import urlencode, urlsplit

from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from .material_forms import MaterialForm
from .models import Material, Product


def _filters(request):
    product_id = request.GET.get("produto", "")
    if len(product_id) > 19 or not product_id.isascii() or not product_id.isdigit():
        product_id = ""
    elif not Product.objects.filter(pk=product_id).exists():
        product_id = ""
    else:
        product_id = str(int(product_id))
    status = request.GET.get("situacao", "")
    if status not in ("active", "hidden"):
        status = ""
    return product_id, status


def _query(product_id, status):
    values = {}
    if product_id:
        values["produto"] = product_id
    if status:
        values["situacao"] = status
    return urlencode(values)


def _return_url(request):
    query = _query(*_filters(request))
    url = reverse("panel_materials")
    return f"{url}?{query}" if query else url


@staff_member_required(login_url="/painel/entrar/")
def materials(request):
    product_id, status = _filters(request)
    all_materials = Material.objects.all()
    items = all_materials.select_related("product").order_by("product__title", "position", "pk")
    if product_id:
        items = items.filter(product_id=product_id)
    if status:
        items = items.filter(active=status == "active")
    items = list(items)
    for item in items:
        try:
            parsed = urlsplit(item.url)
            item.source_host = parsed.netloc or item.url
            item.has_safe_link = parsed.scheme.lower() in ("http", "https", "ftp", "ftps") and bool(parsed.netloc)
        except ValueError:
            item.source_host = item.url
            item.has_safe_link = False
    return render(request, "panel/materials.html", {
        "items": items,
        "products": Product.objects.order_by("title", "pk"),
        "product_filter": product_id,
        "status_filter": status,
        "filter_query": _query(product_id, status),
        "total_materials": all_materials.count(),
        "active_materials": all_materials.filter(active=True).count(),
        "linked_products": all_materials.values("product_id").distinct().count(),
    })


@staff_member_required(login_url="/painel/entrar/")
def material_form(request, pk=None):
    instance = get_object_or_404(Material, pk=pk) if pk is not None else None
    product_id, _ = _filters(request)
    initial = {"product": product_id} if product_id and instance is None else None
    form = MaterialForm(request.POST if request.method == "POST" else None, instance=instance, initial=initial)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Material atualizado." if instance else "Material cadastrado.")
        return redirect(_return_url(request))
    return render(request, "panel/form.html", {
        "form": form,
        "title": "Editar material" if instance else "Novo material",
        "return_url": _return_url(request),
    })


@staff_member_required(login_url="/painel/entrar/")
@require_POST
def material_delete(request, pk):
    get_object_or_404(Material, pk=pk).delete()
    messages.success(request, "Material excluído.")
    return redirect(_return_url(request))

