from django import forms
from django.core.validators import URLValidator

from .models import Material, Product


class MaterialForm(forms.ModelForm):
    url = forms.URLField(
        label="Link do material",
        assume_scheme="https",
        validators=[URLValidator(schemes=["http", "https"])],
        help_text="Cole o endereço completo do vídeo, aula, PDF ou conteúdo complementar.",
        widget=forms.URLInput(attrs={"placeholder": "https://..."}),
    )

    class Meta:
        model = Material
        fields = ["product", "title", "url", "position", "active"]
        labels = {
            "product": "Curso ou produto",
            "title": "Nome do material",
            "position": "Ordem de exibição",
            "active": "Disponível para clientes",
        }
        help_texts = {
            "position": "Os materiais aparecem em ordem crescente dentro do produto.",
            "active": "Desmarque para ocultar o material da área do cliente.",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["product"].queryset = Product.objects.order_by("title", "pk")
        self.fields["product"].empty_label = "Selecione um curso ou produto"
        for field in self.fields.values():
            field.widget.attrs["class"] = "form-control"
        self.fields["position"].widget.attrs["min"] = "0"

    def clean_url(self):
        original = self.data.get(self.add_prefix("url"), "").strip()
        if not original.lower().startswith(("http://", "https://")):
            raise forms.ValidationError("Use um link completo iniciado por http:// ou https://.")
        return self.cleaned_data["url"]

