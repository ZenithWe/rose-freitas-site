from django.contrib import admin
from .forms import ProductForm
from .models import SiteSettings,Banner,Product,Material,VipRequest,Order,CustomerAccess,AgendaItem,Expense

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    form=ProductForm
    list_display=("title","kind","price","active","featured")
    list_filter=("kind","active","featured")
    search_fields=("title","description")
    def get_queryset(self,request):
        return super().get_queryset(request).select_related("uploaded_cover").defer("uploaded_cover__data")

@admin.register(VipRequest)
class VipRequestAdmin(admin.ModelAdmin):
    list_display=("full_name","channel","phone","status","created_at")
    list_filter=("channel","status")
    search_fields=("full_name","phone","email")

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display=("customer_name","product","total","status","created_at")
    list_filter=("status","product")
    search_fields=("customer_name","email","phone")

admin.site.register(SiteSettings)
admin.site.register(Banner)
admin.site.register(Material)
admin.site.register(CustomerAccess)
admin.site.register(AgendaItem)
admin.site.register(Expense)
admin.site.site_header="Rose Freitas • Administração"
admin.site.site_title="Rose Freitas"
