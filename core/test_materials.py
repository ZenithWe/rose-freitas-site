from decimal import Decimal
from urllib.parse import urlencode

from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from .material_forms import MaterialForm
from .models import CustomerAccess, Material, Order, Product
from .tests import TEST_SETTINGS


@override_settings(**TEST_SETTINGS)
class MaterialManagementTests(TestCase):
    def setUp(self):
        self.staff = get_user_model().objects.create_user("materials-staff", password="test", is_staff=True)
        self.client.force_login(self.staff)
        self.product = Product.objects.create(
            title="Curso com acesso existente", slug="materiais-curso", description="Conteúdo",
            price=Decimal("49.90"), active=False,
        )
        self.other_product = Product.objects.create(title="Outro curso", slug="materiais-outro", description="Conteúdo")
        self.material = Material.objects.create(
            product=self.product, title="Aula já cadastrada", url="https://content.example.com/aula?ref=original",
            position=1,
        )
        self.access = CustomerAccess.objects.create(email="cliente-materiais@example.com", product=self.product, active=True)
        self.order = Order.objects.create(
            product=self.product, customer_name="Cliente", email=self.access.email, total="49.90", status="paid",
        )

    def payload(self, **updates):
        data = {
            "product": self.product.pk, "title": "PDF complementar", "url": "https://files.example.com/apoio.pdf?download=1",
            "position": "2", "active": "on",
        }
        data.update(updates)
        return data

    def test_material_routes_require_staff_and_anonymous_mutation_does_not_change_records(self):
        routes = [
            reverse("panel_materials"), reverse("panel_material_new"),
            reverse("panel_material_edit", args=[self.material.pk]), reverse("panel_material_delete", args=[self.material.pk]),
        ]
        anonymous = Client()
        ordinary = get_user_model().objects.create_user("materials-customer", password="test")
        for client in (anonymous, Client()):
            if client is not anonymous:
                client.force_login(ordinary)
            for route in routes:
                with self.subTest(route=route, authenticated=client is not anonymous):
                    response = client.get(route)
                    self.assertEqual(response.status_code, 302)
                    self.assertTrue(response.url.startswith(reverse("panel_login")))
            self.assertEqual(client.post(routes[-1]).status_code, 302)
        self.assertTrue(Material.objects.filter(pk=self.material.pk).exists())

    def test_filters_keep_inactive_product_materials_and_use_real_counts(self):
        hidden = Material.objects.create(product=self.other_product, title="Conteúdo oculto", url="https://content.example.com/oculto", active=False)
        response = self.client.get(reverse("panel_materials"), {"produto": self.product.pk})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(list(response.context["items"]), [self.material])
        self.assertEqual(response.context["total_materials"], 2)
        self.assertEqual(response.context["active_materials"], 1)
        self.assertEqual(response.context["linked_products"], 2)
        self.assertContains(response, self.material.url.replace("&", "&amp;"))
        response = self.client.get(reverse("panel_materials"), {"situacao": "hidden"})
        self.assertEqual(list(response.context["items"]), [hidden])

    def test_malformed_filter_values_are_ignored_without_server_error(self):
        for product_id in ("invalid", "-1", "9" * 100, "١", "9999999999999999999"):
            with self.subTest(product=product_id):
                response = self.client.get(reverse("panel_materials"), {"produto": product_id, "situacao": "unexpected"})
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.context["product_filter"], "")
                self.assertEqual(response.context["status_filter"], "")

    def test_create_and_edit_preserve_filters_links_and_customer_history(self):
        query = urlencode({"produto": self.product.pk, "situacao": "active"})
        return_url = f"{reverse('panel_materials')}?{query}"
        new_url = f"{reverse('panel_material_new')}?{query}"
        response = self.client.get(new_url)
        self.assertEqual(str(response.context["form"].initial["product"]), str(self.product.pk))
        self.assertContains(response, "Curso com acesso existente")
        self.assertContains(response, return_url.replace("&", "&amp;"))
        response = self.client.post(new_url, self.payload())
        self.assertRedirects(response, return_url)
        material = Material.objects.get(title="PDF complementar")
        self.assertEqual(material.product_id, self.product.pk)
        self.assertEqual(material.url, self.payload()["url"])
        edit_url = f"{reverse('panel_material_edit', args=[material.pk])}?{query}"
        response = self.client.post(edit_url, self.payload(title="PDF revisado", position="3", active=""))
        self.assertRedirects(response, return_url)
        material.refresh_from_db()
        self.assertEqual(material.title, "PDF revisado")
        self.assertEqual(material.position, 3)
        self.assertFalse(material.active)
        self.access.refresh_from_db()
        self.order.refresh_from_db()
        self.assertTrue(self.access.active)
        self.assertEqual(self.order.status, "paid")
        self.assertTrue(Material.objects.filter(pk=self.material.pk, url=self.material.url).exists())

    def test_delete_requires_post_and_csrf_and_preserves_product_orders_and_access(self):
        url = reverse("panel_material_delete", args=[self.material.pk])
        self.assertEqual(self.client.get(url).status_code, 405)
        guarded = Client(enforce_csrf_checks=True)
        guarded.force_login(self.staff)
        self.assertEqual(guarded.post(url).status_code, 403)
        guarded.get(reverse("panel_material_edit", args=[self.material.pk]))
        token = guarded.cookies["csrftoken"].value
        response = guarded.post(f"{url}?produto={self.product.pk}", HTTP_X_CSRFTOKEN=token)
        self.assertRedirects(response, f"{reverse('panel_materials')}?produto={self.product.pk}")
        self.assertFalse(Material.objects.filter(pk=self.material.pk).exists())
        self.assertTrue(Product.objects.filter(pk=self.product.pk).exists())
        self.assertTrue(Order.objects.filter(pk=self.order.pk, status="paid").exists())
        self.assertTrue(CustomerAccess.objects.filter(pk=self.access.pk, active=True).exists())

    def test_material_urls_reject_unsafe_schemes_and_non_http_links(self):
        for url in ("javascript:alert(1)", "data:text/html,test", "ftp://example.com/file", "//example.com/file", "example.com/file"):
            with self.subTest(url=url):
                form = MaterialForm(data=self.payload(url=url))
                self.assertFalse(form.is_valid())
                self.assertIn("url", form.errors)
        form = MaterialForm(data=self.payload())
        self.assertTrue(form.is_valid(), form.errors)

    def test_invalid_material_form_has_linked_field_errors_and_keeps_existing_record(self):
        response = self.client.post(reverse("panel_material_edit", args=[self.material.pk]), self.payload(url="javascript:alert(1)", position="-1"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="id_url_error"')
        self.assertContains(response, 'id="id_position_error"')
        self.assertContains(response, "Revise as informações")
        self.material.refresh_from_db()
        self.assertEqual(self.material.url, "https://content.example.com/aula?ref=original")
        self.assertEqual(self.material.position, 1)

