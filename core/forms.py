import re
from urllib.parse import urlsplit

from django import forms
from django.core.validators import URLValidator
from django.core.exceptions import ValidationError
from django.utils.text import slugify
from .models import Product,VipRequest,Banner,AgendaItem,Expense,SiteSettings,Order,CustomerAccess

class StyledModelForm(forms.ModelForm):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        for field in self.fields.values():
            field.widget.attrs["class"]="form-control"
        for name in ("price", "total", "amount"):
            if name in self.fields:
                self.fields[name].min_value = 0
                self.fields[name].widget.attrs["min"] = "0"

    def clean(self):
        data = super().clean()
        for name in ("price", "total", "amount"):
            if data.get(name) is not None and data[name] < 0:
                self.add_error(name, "Informe um valor igual ou maior que zero.")
        return data

    def clean_email(self):
        return self.cleaned_data["email"].strip().lower()

class ProductForm(StyledModelForm):
    class Meta:
        model=Product
        fields=["kind","title","slug","description","price","lessons","bonus","cover_url","checkout_url","vip_channel","featured","active"]
        labels={"kind":"Tipo", "title":"Título", "slug":"Endereço do produto", "description":"Descrição", "price":"Preço (R$)", "lessons":"Quantidade de aulas", "bonus":"Bônus", "cover_url":"URL da capa", "checkout_url":"Link de compra", "vip_channel":"Canal VIP", "featured":"Destaque", "active":"Ativo"}
        help_texts={"slug":"Pode ficar em branco: será criado a partir do título.", "checkout_url":"Use o endereço completo da página de pagamento existente."}

    def clean_slug(self):
        slug = self.cleaned_data.get("slug") or slugify(self.cleaned_data.get("title", ""))[:180]
        if not slug:
            raise forms.ValidationError("Informe um endereço válido para o produto.")
        duplicates = Product.objects.filter(slug=slug)
        if self.instance.pk:
            duplicates = duplicates.exclude(pk=self.instance.pk)
        if duplicates.exists():
            raise forms.ValidationError("Este endereço já pertence a outro produto. Escolha outro.")
        return slug

class VipRequestForm(StyledModelForm):
    class Meta:
        model=VipRequest
        fields=["full_name","phone","email"]
        labels={"full_name":"Nome completo","phone":"Celular","email":"E-mail (opcional)"}
        widgets={"full_name":forms.TextInput(attrs={"autocomplete":"name"}), "phone":forms.TextInput(attrs={"type":"tel", "autocomplete":"tel"}), "email":forms.EmailInput(attrs={"autocomplete":"email"})}

class BannerForm(StyledModelForm):
    class Meta:
        model=Banner
        fields=["title","subtitle","image_url","button_text","link","active","position"]
        labels={"title":"Título", "subtitle":"Subtítulo", "image_url":"URL da imagem", "button_text":"Texto do botão", "link":"Destino do botão", "active":"Ativo", "position":"Ordem de exibição"}

    def clean_link(self):
        link = self.cleaned_data["link"].strip()
        try:
            parsed = urlsplit(link)
        except ValueError:
            raise forms.ValidationError("Informe um endereço válido para o botão.")
        if any(char in link for char in ("\r", "\n", "\t")):
            raise forms.ValidationError("Informe um endereço válido para o botão.")
        if link.startswith("/") and not link.startswith("//") and not parsed.netloc and "\\" not in link:
            return link
        if link.startswith("#"):
            return link
        try:
            URLValidator(schemes=["http", "https"])(link)
        except ValidationError:
            raise forms.ValidationError("Use um link http/https, um caminho iniciado por / ou uma seção iniciada por #.")
        return link

class AgendaForm(StyledModelForm):
    class Meta:
        model=AgendaItem
        fields=["title","kind","starts_at","description","active"]
        labels={"title":"Título", "kind":"Tipo", "starts_at":"Data e horário", "description":"Descrição", "active":"Ativo"}
        widgets={"starts_at":forms.DateTimeInput(format="%Y-%m-%dT%H:%M", attrs={"type":"datetime-local"})}

class ExpenseForm(StyledModelForm):
    class Meta:
        model=Expense
        fields=["description","amount","date"]
        labels={"description":"Descrição", "amount":"Valor (R$)", "date":"Data"}
        widgets={"date":forms.DateInput(format="%Y-%m-%d", attrs={"type":"date"})}

class SettingsForm(StyledModelForm):
    class Meta:
        model=SiteSettings
        fields=["hero_title","hero_subtitle","hero_button","instagram","youtube","tiktok","whatsapp","partnership_whatsapp","pix_key","pix_name"]
        labels={"hero_title":"Título principal", "hero_subtitle":"Texto de apresentação", "hero_button":"Texto do botão principal", "instagram":"Instagram", "youtube":"YouTube", "tiktok":"TikTok", "whatsapp":"WhatsApp", "partnership_whatsapp":"WhatsApp de parcerias", "pix_key":"Chave Pix", "pix_name":"Nome do titular do Pix"}
        help_texts={"whatsapp":"Informe o país, DDD e número. Exemplo: 5511999999999.", "partnership_whatsapp":"Informe o país, DDD e número; pode usar o mesmo contato comercial."}

    def clean_whatsapp(self):
        return self._clean_whatsapp("whatsapp")

    def clean_partnership_whatsapp(self):
        return self._clean_whatsapp("partnership_whatsapp")

    def _clean_whatsapp(self, name):
        value = self.cleaned_data.get(name, "").strip()
        if not value:
            return ""
        if re.search(r"[^0-9+().\s-]", value):
            raise forms.ValidationError("Informe somente o número com país e DDD.")
        digits = re.sub(r"\D", "", value)
        if not 10 <= len(digits) <= 15:
            raise forms.ValidationError("Informe um número válido com país e DDD.")
        return digits

class OrderForm(StyledModelForm):
    class Meta:
        model=Order
        fields=["product","customer_name","email","phone","total","status"]
        labels={"product":"Produto", "customer_name":"Nome do cliente", "email":"E-mail", "phone":"Celular", "total":"Total (R$)", "status":"Situação"}

class CustomerAccessForm(StyledModelForm):
    class Meta:
        model=CustomerAccess
        fields=["email","product","active"]
        labels={"email":"E-mail", "product":"Produto", "active":"Acesso ativo"}

    def clean(self):
        data = super().clean()
        if data.get("email") and data.get("product"):
            duplicates = CustomerAccess.objects.filter(email__iexact=data["email"], product=data["product"])
            if self.instance.pk:
                duplicates = duplicates.exclude(pk=self.instance.pk)
            if duplicates.exists():
                self.add_error("email", "Este cliente já possui um acesso para o produto. Atualize o acesso existente na administração.")
        return data
