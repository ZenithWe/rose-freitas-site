from django import forms
from .models import Product,VipRequest,Banner,AgendaItem,Expense,SiteSettings,Order,CustomerAccess

class StyledModelForm(forms.ModelForm):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        for field in self.fields.values():
            field.widget.attrs["class"]="form-control"

class ProductForm(StyledModelForm):
    class Meta:
        model=Product
        fields=["kind","title","slug","description","price","lessons","bonus","cover_url","checkout_url","vip_channel","featured","active"]

class VipRequestForm(StyledModelForm):
    class Meta:
        model=VipRequest
        fields=["full_name","phone","email"]
        labels={"full_name":"Nome completo","phone":"Celular","email":"E-mail (opcional)"}

class BannerForm(StyledModelForm):
    class Meta:
        model=Banner
        fields=["title","subtitle","image_url","button_text","link","active","position"]

class AgendaForm(StyledModelForm):
    class Meta:
        model=AgendaItem
        fields=["title","kind","starts_at","description","active"]
        widgets={"starts_at":forms.DateTimeInput(attrs={"type":"datetime-local"})}

class ExpenseForm(StyledModelForm):
    class Meta:
        model=Expense
        fields=["description","amount","date"]
        widgets={"date":forms.DateInput(attrs={"type":"date"})}

class SettingsForm(StyledModelForm):
    class Meta:
        model=SiteSettings
        fields=["hero_title","hero_subtitle","hero_button","instagram","youtube","tiktok","whatsapp","partnership_whatsapp","pix_key","pix_name"]

class OrderForm(StyledModelForm):
    class Meta:
        model=Order
        fields=["product","customer_name","email","phone","total","status"]

class CustomerAccessForm(StyledModelForm):
    class Meta:
        model=CustomerAccess
        fields=["email","product","active"]
