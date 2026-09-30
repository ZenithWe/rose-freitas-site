from datetime import date, timedelta
from decimal import Decimal
import re
from xml.etree import ElementTree

from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from django.core import mail
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from .apps import seed
from .forms import AgendaForm, BannerForm, CustomerAccessForm, ExpenseForm, ProductForm
from .models import AgendaItem, Banner, CustomerAccess, CustomerLoginCode, Expense, Material, Order, Product, SiteSettings, VipRequest


TEST_SETTINGS = {
    "STORAGES": {"staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"}},
    "EMAIL_BACKEND": "django.core.mail.backends.locmem.EmailBackend",
    "PASSWORD_HASHERS": ["django.contrib.auth.hashers.MD5PasswordHasher"],
    "CACHES": {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache", "LOCATION": "rose-tests"}},
}


def make_product(**kwargs):
    fields = {"title": "Conteúdo de teste", "slug": "conteudo-teste", "description": "Descrição do conteúdo", "price": Decimal("49.90")}
    fields.update(kwargs)
    return Product.objects.create(**fields)


@override_settings(**TEST_SETTINGS)
class PublicFlowsTests(TestCase):
    def setUp(self):
        Product.objects.all().delete()
        self.course = make_product(checkout_url="https://pay.kiwify.com.br/ntgCTUk")
        self.product = make_product(title="Produto publicado", slug="produto-publicado", kind="product")
        self.vip = make_product(title="VIP Telegram", slug="telegram-teste", kind="vip", vip_channel="telegram", price=Decimal("29.90"))
        self.hidden = make_product(title="Conteúdo oculto", slug="conteudo-oculto", active=False)

    def test_public_collections_only_show_active_products_of_their_kind(self):
        response = self.client.get(reverse("home"))
        self.assertEqual(list(response.context["courses"]), [self.course])
        self.assertEqual(list(response.context["products"]), [self.product])
        self.assertEqual(list(response.context["vips"]), [self.vip])
        response = self.client.get(reverse("catalog"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(list(response.context["products"]), [self.product])
        self.assertEqual(self.client.get(reverse("vip")).status_code, 200)
        self.assertEqual(self.client.get(reverse("affiliates")).status_code, 200)
        self.assertEqual(self.client.get(reverse("partnerships")).status_code, 200)

    def test_product_detail_preserves_existing_checkout_and_hides_inactive_records(self):
        response = self.client.get(reverse("product_detail", args=[self.course.slug]))
        self.assertContains(response, "https://pay.kiwify.com.br/ntgCTUk")
        self.assertEqual(self.client.get(reverse("product_detail", args=[self.hidden.slug])).status_code, 404)

    def test_vip_detail_preserves_checkout_and_existing_request_flow(self):
        self.vip.checkout_url = "https://checkout.example.com/vip-existente"
        self.vip.save()
        response = self.client.get(reverse("product_detail", args=[self.vip.slug]))
        self.assertContains(response, self.vip.checkout_url)
        self.assertContains(response, reverse("vip_request", args=[self.vip.slug]))

    def test_vip_submission_preserves_channel_price_and_private_receipt(self):
        settings = SiteSettings.objects.get(pk=1)
        settings.pix_key = "pix-cadastrado@example.com"
        settings.pix_name = "Titular cadastrado"
        settings.whatsapp = "5511999999999"
        settings.save()
        response = self.client.post(reverse("vip_request", args=[self.vip.slug]), {"full_name": "Cliente VIP", "phone": "5511999999999", "email": "VIP@EXAMPLE.COM"})
        item = VipRequest.objects.get()
        self.assertEqual(item.channel, "telegram")
        self.assertEqual(item.email, "vip@example.com")
        self.assertRedirects(response, reverse("vip_success", args=[item.pk]))
        receipt = self.client.get(response.url)
        self.assertEqual(receipt.context["product"], self.vip)
        self.assertEqual(receipt.context["product"].price, Decimal("29.90"))
        self.assertContains(receipt, "29,90")
        self.assertContains(receipt, settings.pix_key)
        self.assertContains(receipt, settings.pix_name)
        self.assertContains(receipt, "https://wa.me/5511999999999")
        self.assertContains(receipt, item.get_status_display())
        self.assertIn("no-store", receipt.headers["Cache-Control"])
        self.assertEqual(Client().get(response.url).status_code, 404)

    def test_confirmed_and_cancelled_vip_receipts_show_actual_status_without_payment_instructions(self):
        settings = SiteSettings.objects.get(pk=1)
        settings.pix_key = "pix-nao-pagar@example.com"
        settings.pix_name = "Titular do Pix"
        settings.whatsapp = "5511999999999"
        settings.save()
        submission = self.client.post(reverse("vip_request", args=[self.vip.slug]), {"full_name": "Cliente VIP", "phone": "5511999999999", "email": "vip@example.com"})
        item = VipRequest.objects.get()
        for status in ("confirmed", "cancelled"):
            with self.subTest(status=status):
                item.status = status
                item.save(update_fields=["status", "updated_at"])
                receipt = self.client.get(submission.url)
                self.assertContains(receipt, item.get_status_display())
                self.assertNotContains(receipt, "Aguardando confirmação")
                self.assertNotContains(receipt, settings.pix_key)
                self.assertNotContains(receipt, settings.pix_name)
                self.assertNotContains(receipt, "data-copy-pix")
                self.assertNotContains(receipt, "Enviar comprovante")

    def test_affiliate_and_partnership_pages_use_configured_commercial_contact(self):
        settings = SiteSettings.objects.get(pk=1)
        settings.whatsapp = "5511888888888"
        settings.partnership_whatsapp = "5511999999999"
        settings.save()
        for name in ("affiliates", "partnerships"):
            self.assertContains(self.client.get(reverse(name)), "https://wa.me/5511999999999")
        settings.partnership_whatsapp = ""
        settings.save()
        self.assertContains(self.client.get(reverse("partnerships")), "https://wa.me/5511888888888")

    def test_vip_form_does_not_accept_course_or_invalid_customer_data(self):
        self.assertEqual(self.client.get(reverse("vip_request", args=[self.course.slug])).status_code, 404)
        response = self.client.post(reverse("vip_request", args=[self.vip.slug]), {"full_name": "", "phone": "", "email": "inválido"})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(VipRequest.objects.exists())

    def test_seo_endpoints_follow_host_and_exclude_private_inactive_routes(self):
        response = self.client.get(reverse("sitemap"), secure=True)
        self.assertEqual(response.status_code, 200)
        nodes = ElementTree.fromstring(response.content)
        urls = [node.text for node in nodes.findall("{*}url/{*}loc")]
        self.assertIn("https://testserver/cursos/", urls)
        self.assertIn("https://testserver/produto/conteudo-teste/", urls)
        self.assertFalse(any(self.hidden.slug in url or "/painel/" in url or "/area-do-cliente/" in url for url in urls))
        robots = self.client.get(reverse("robots"), secure=True)
        self.assertContains(robots, "Sitemap: https://testserver/sitemap.xml")
        self.assertContains(robots, "Disallow: /painel/")
        self.assertEqual(self.client.post(reverse("sitemap")).status_code, 405)

    def test_seed_does_not_overwrite_existing_settings_products_or_checkout(self):
        settings = SiteSettings.objects.get(pk=1)
        settings.hero_title = "Título editado pela Rose"
        settings.save()
        self.course.slug = "coragem-de-falar"
        self.course.title = "Título personalizado"
        self.course.checkout_url = "https://checkout.example.com/pagina-existente"
        self.course.save()
        seed(None)
        settings.refresh_from_db()
        self.course.refresh_from_db()
        self.assertEqual(settings.hero_title, "Título editado pela Rose")
        self.assertEqual(self.course.title, "Título personalizado")
        self.assertEqual(self.course.checkout_url, "https://checkout.example.com/pagina-existente")


@override_settings(**TEST_SETTINGS)
class CustomerLoginTests(TestCase):
    def setUp(self):
        cache.clear()
        self.product = make_product(slug="curso-cliente")
        self.access = CustomerAccess.objects.create(email="Cliente@Example.com", product=self.product)
        Material.objects.create(product=self.product, title="Aula liberada", url="https://example.com/aula")
        Material.objects.create(product=self.product, title="Aula ainda oculta", url="https://example.com/oculta", active=False)
        self.url = reverse("customer_area")

    def pending_client(self, email="cliente@example.com"):
        client = Client()
        session = client.session
        session["pending_customer_email"] = email
        session.save()
        return client

    def make_code(self, code="123456", **kwargs):
        fields = {"email": "cliente@example.com", "code_hash": make_password(code), "expires_at": timezone.now() + timedelta(minutes=10)}
        fields.update(kwargs)
        return CustomerLoginCode.objects.create(**fields)

    def test_valid_email_code_login_rotates_session_and_releases_only_active_materials(self):
        self.client.post(self.url, {"action": "request", "email": " CLIENTE@EXAMPLE.COM "})
        self.assertEqual(len(mail.outbox), 1)
        code = re.search(r"\b\d{6}\b", mail.outbox[0].body).group()
        item = CustomerLoginCode.objects.get()
        self.assertNotEqual(item.code_hash, code)
        original_key = self.client.session.session_key
        response = self.client.post(self.url, {"action": "verify", "code": code}, follow=True)
        self.assertNotEqual(self.client.session.session_key, original_key)
        self.assertEqual(self.client.session["customer_verified"], "cliente@example.com")
        self.assertNotIn("pending_customer_email", self.client.session)
        item.refresh_from_db()
        self.assertTrue(item.used)
        self.assertContains(response, "Aula liberada")
        self.assertNotContains(response, "Aula ainda oculta")
        self.assertIn("no-store", response.headers["Cache-Control"])

    def test_all_inactive_materials_show_empty_hint_without_exposing_hidden_content(self):
        Material.objects.filter(product=self.product).update(active=False)
        session = self.client.session
        session["customer_verified"] = "cliente@example.com"
        session.save()
        response = self.client.get(self.url)
        self.assertContains(response, "Os materiais deste conteúdo serão adicionados em breve.")
        self.assertNotContains(response, "Aula liberada")
        self.assertNotContains(response, "Aula ainda oculta")
        self.assertEqual(response.context["accesses"][0].product.available_materials, [])

    def test_resend_cooldown_is_shared_by_browsers_and_new_code_invalidates_previous(self):
        self.client.post(self.url, {"action": "request", "email": "cliente@example.com"})
        first = CustomerLoginCode.objects.get()
        Client().post(self.url, {"action": "request", "email": "cliente@example.com"})
        self.assertEqual(CustomerLoginCode.objects.count(), 1)
        self.assertEqual(len(mail.outbox), 1)
        CustomerLoginCode.objects.filter(pk=first.pk).update(created_at=timezone.now()-timedelta(seconds=61))
        self.client.post(self.url, {"action": "request", "email": "cliente@example.com"})
        first.refresh_from_db()
        self.assertTrue(first.used)
        self.assertEqual(CustomerLoginCode.objects.filter(used=False).count(), 1)
        self.assertEqual(len(mail.outbox), 2)

    def test_code_is_single_use_across_browsers(self):
        self.make_code()
        first, second = self.pending_client(), self.pending_client()
        first.post(self.url, {"action": "verify", "code": "123456"})
        second.post(self.url, {"action": "verify", "code": "123456"})
        self.assertIn("customer_verified", first.session)
        self.assertNotIn("customer_verified", second.session)

    def test_five_wrong_guesses_invalidate_code_across_browsers(self):
        item = self.make_code()
        for _ in range(5):
            self.pending_client().post(self.url, {"action": "verify", "code": "999999"})
        item.refresh_from_db()
        self.assertTrue(item.used)
        client = self.pending_client()
        client.post(self.url, {"action": "verify", "code": "123456"})
        self.assertNotIn("customer_verified", client.session)

    def test_expired_and_revoked_access_codes_cannot_log_in(self):
        self.make_code(expires_at=timezone.now()-timedelta(seconds=1))
        client = self.pending_client()
        client.post(self.url, {"action": "verify", "code": "123456"})
        self.assertNotIn("customer_verified", client.session)
        self.make_code()
        self.access.active = False
        self.access.save()
        client.post(self.url, {"action": "verify", "code": "123456"})
        self.assertNotIn("customer_verified", client.session)

    def test_unknown_email_receives_same_generic_message_and_invalid_email_is_rejected(self):
        known = self.client.post(self.url, {"action": "request", "email": "cliente@example.com"}, follow=True)
        unknown = Client().post(self.url, {"action": "request", "email": "nao-cadastrado@example.com"}, follow=True)
        generic = "Se o e-mail tiver acesso liberado, um código foi enviado."
        self.assertContains(known, generic)
        self.assertContains(unknown, generic)
        self.assertFalse(CustomerLoginCode.objects.filter(email="nao-cadastrado@example.com").exists())
        invalid_client = Client()
        invalid_client.post(self.url, {"action": "request", "email": "email inválido"})
        self.assertNotIn("pending_customer_email", invalid_client.session)

    def test_customer_logout_clears_customer_access_and_preserves_staff_login(self):
        staff = get_user_model().objects.create_user("staff-logout", password="test", is_staff=True)
        self.client.force_login(staff)
        session = self.client.session
        session["customer_verified"] = "cliente@example.com"
        session["pending_customer_email"] = "cliente@example.com"
        session.save()
        self.client.post(self.url, {"action": "logout"})
        self.assertNotIn("customer_verified", self.client.session)
        self.assertNotIn("pending_customer_email", self.client.session)
        self.assertIn("_auth_user_id", self.client.session)


@override_settings(**TEST_SETTINGS)
class PanelFlowsTests(TestCase):
    def setUp(self):
        self.staff = get_user_model().objects.create_user("rose-test", password="test", is_staff=True)
        self.product = make_product(slug="produto-painel")
        self.client.force_login(self.staff)

    def test_all_panel_lists_require_staff_login(self):
        anonymous = Client()
        for name in ("dashboard", "panel_products", "panel_vip", "panel_banners", "panel_agenda", "panel_orders", "panel_customers", "panel_finance", "panel_settings"):
            response = anonymous.get(reverse(name))
            self.assertEqual(response.status_code, 302)
            self.assertTrue(response.url.startswith(reverse("panel_login")))
            self.assertEqual(self.client.get(reverse(name)).status_code, 200)
        ordinary = get_user_model().objects.create_user("cliente-painel", password="test")
        anonymous.force_login(ordinary)
        self.assertEqual(anonymous.get(reverse("dashboard")).status_code, 302)

    def test_product_crud_validates_slug_and_deletes_unreferenced_product(self):
        payload = {"kind": "course", "title": "Novo curso", "slug": "", "description": "Descrição", "price": "10.00", "lessons": "3", "active": "on"}
        self.client.post(reverse("panel_product_new"), payload)
        product = Product.objects.get(slug="novo-curso")
        payload.update({"title": "Curso atualizado", "slug": product.slug})
        self.client.post(reverse("panel_product_edit", args=[product.pk]), payload)
        product.refresh_from_db()
        self.assertEqual(product.title, "Curso atualizado")
        self.assertEqual(self.client.get(reverse("panel_product_delete", args=[product.pk])).status_code, 405)
        self.client.post(reverse("panel_product_delete", args=[product.pk]))
        self.assertFalse(Product.objects.filter(pk=product.pk).exists())

    def test_product_delete_preserves_existing_orders_customer_access_and_materials(self):
        order = Order.objects.create(product=self.product, customer_name="Cliente", email="cliente@example.com", total="49.90", status="paid")
        access = CustomerAccess.objects.create(email=order.email, product=self.product)
        material = Material.objects.create(product=self.product, title="Aula", url="https://example.com/aula")
        response = self.client.post(reverse("panel_product_delete", args=[self.product.pk]))
        self.assertEqual(response.status_code, 302)
        self.product.refresh_from_db()
        self.assertFalse(self.product.active)
        self.assertTrue(Order.objects.filter(pk=order.pk).exists())
        self.assertTrue(CustomerAccess.objects.filter(pk=access.pk, active=True).exists())
        self.assertTrue(Material.objects.filter(pk=material.pk).exists())

    def test_product_delete_preserves_access_even_without_an_order(self):
        access = CustomerAccess.objects.create(email="liberacao-manual@example.com", product=self.product)
        self.client.post(reverse("panel_product_delete", args=[self.product.pk]))
        self.product.refresh_from_db()
        self.assertFalse(self.product.active)
        self.assertTrue(CustomerAccess.objects.filter(pk=access.pk, active=True).exists())

    def test_paid_order_sets_timestamp_and_reactivates_same_case_insensitive_access(self):
        order = Order.objects.create(product=self.product, customer_name="Cliente", email="CLIENTE@example.com", total="49.90")
        access = CustomerAccess.objects.create(email="Cliente@Example.com", product=self.product, active=False)
        payload = {"product": self.product.pk, "customer_name": "Cliente", "email": "CLIENTE@example.com", "phone": "", "total": "49.90", "status": "paid"}
        self.client.post(reverse("panel_order_edit", args=[order.pk]), payload)
        order.refresh_from_db()
        access.refresh_from_db()
        paid_at = order.paid_at
        self.assertEqual(order.status, "paid")
        self.assertIsNotNone(paid_at)
        self.assertTrue(access.active)
        self.assertEqual(CustomerAccess.objects.filter(product=self.product).count(), 1)
        self.client.post(reverse("panel_order_edit", args=[order.pk]), payload)
        order.refresh_from_db()
        self.assertEqual(order.paid_at, paid_at)

    def test_payment_confirmation_grants_access_and_pending_order_does_not(self):
        order = Order.objects.create(product=self.product, customer_name="Novo cliente", email="novo@example.com", total="49.90")
        payload = {"product": self.product.pk, "customer_name": "Novo cliente", "email": order.email, "phone": "", "total": "49.90", "status": "pending"}
        self.client.post(reverse("panel_order_edit", args=[order.pk]), payload)
        self.assertFalse(CustomerAccess.objects.filter(email=order.email, product=self.product).exists())
        payload["status"] = "paid"
        self.client.post(reverse("panel_order_edit", args=[order.pk]), payload)
        self.assertTrue(CustomerAccess.objects.filter(email=order.email, product=self.product, active=True).exists())

    def test_administrative_login_and_post_logout_preserve_existing_contract(self):
        client = Client()
        response = client.post(reverse("panel_login"), {"username": self.staff.username, "password": "test"})
        self.assertRedirects(response, reverse("dashboard"))
        self.assertEqual(client.get(reverse("panel_logout")).status_code, 405)
        self.assertRedirects(client.post(reverse("panel_logout")), reverse("home"))
        self.assertNotIn("_auth_user_id", client.session)

    def test_staff_mutations_require_csrf(self):
        guarded = Client(enforce_csrf_checks=True)
        guarded.force_login(self.staff)
        response = guarded.post(reverse("panel_product_delete", args=[self.product.pk]))
        self.assertEqual(response.status_code, 403)
        self.assertTrue(Product.objects.filter(pk=self.product.pk).exists())

    def test_vip_status_filters_and_finance_use_real_rows(self):
        vip = VipRequest.objects.create(channel="telegram", full_name="Cliente", phone="5511999999999")
        self.client.post(reverse("panel_vip_status", args=[vip.pk, "confirmed"]))
        vip.refresh_from_db()
        self.assertEqual(vip.status, "confirmed")
        self.assertEqual(list(self.client.get(reverse("panel_vip"), {"canal": "whatsapp"}).context["items"]), [])
        Order.objects.create(product=self.product, customer_name="Pago", email="pago@example.com", total="100.00", status="paid")
        Order.objects.create(product=self.product, customer_name="Pendente", email="pendente@example.com", total="900.00")
        self.client.post(reverse("panel_expense_new"), {"description": "Despesa", "amount": "25.00", "date": "2026-09-30"})
        response = self.client.get(reverse("panel_finance"))
        self.assertEqual(response.context["revenue"], Decimal("100.00"))
        self.assertEqual(response.context["expenses"], Decimal("25.00"))
        self.assertEqual(response.context["balance"], Decimal("75.00"))

    def test_banner_agenda_access_and_settings_forms_save_and_preserve_existing_data(self):
        self.client.post(reverse("panel_banner_new"), {"title": "Novidade", "subtitle": "", "image_url": "", "button_text": "Ver cursos", "link": "/cursos/", "active": "on", "position": "0"})
        self.assertEqual(Banner.objects.get().link, "/cursos/")
        future = timezone.localtime(timezone.now()+timedelta(days=1)).strftime("%Y-%m-%dT%H:%M")
        self.client.post(reverse("panel_agenda_new"), {"title": "Encontro", "kind": "live", "starts_at": future, "description": "Agenda real", "active": "on"})
        self.assertTrue(AgendaItem.objects.filter(title="Encontro").exists())
        self.assertEqual(self.client.get(reverse("dashboard")).context["upcoming_agenda_count"], 1)
        self.client.post(reverse("panel_customer_new"), {"email": "NOVO@EXAMPLE.COM", "product": self.product.pk, "active": "on"})
        self.assertTrue(CustomerAccess.objects.filter(email="novo@example.com", product=self.product, active=True).exists())
        settings = SiteSettings.objects.get(pk=1)
        self.client.post(reverse("panel_settings"), {"hero_title": "Rose", "hero_subtitle": "Apresentação", "hero_button": "Ver cursos", "instagram": "https://instagram.com/rose", "youtube": "", "tiktok": "", "whatsapp": "+55 (11) 99999-9999", "partnership_whatsapp": "", "pix_key": "pix-existente@example.com", "pix_name": "Rose"})
        settings.refresh_from_db()
        self.assertEqual(settings.whatsapp, "5511999999999")
        self.assertEqual(settings.pix_key, "pix-existente@example.com")
        self.product.refresh_from_db()
        self.assertEqual(self.product.price, Decimal("49.90"))


@override_settings(**TEST_SETTINGS)
class FormValidationTests(TestCase):
    def test_existing_model_url_fields_reject_script_schemes_and_preserve_valid_links(self):
        for model, field_name in ((Product, "checkout_url"), (Product, "cover_url"), (Material, "url")):
            field = model._meta.get_field(field_name)
            for unsafe in ("javascript:alert(1)", "data:text/html,test", "//example.com/conteudo"):
                with self.assertRaises(ValidationError):
                    field.clean(unsafe, model())
            for valid in ("https://example.com/conteudo", "http://example.com/conteudo", "ftp://example.com/conteudo", "ftps://example.com/conteudo"):
                self.assertEqual(field.clean(valid, model()), valid)

    def test_date_widgets_render_browser_compatible_values(self):
        expense = Expense(description="Teste", amount="10.00", date=date(2026, 9, 30))
        self.assertIn('value="2026-09-30"', str(ExpenseForm(instance=expense)["date"]))
        starts = timezone.make_aware(timezone.datetime(2026, 9, 30, 19, 30))
        self.assertIn('value="2026-09-30T19:30"', str(AgendaForm(instance=AgendaItem(title="Live", starts_at=starts))["starts_at"]))

    def test_negative_money_and_unsafe_banner_links_are_rejected(self):
        self.assertFalse(ExpenseForm({"description": "Teste", "amount": "-1.00", "date": "2026-09-30"}).is_valid())
        for link in ("javascript:alert(1)", "//example.com", "/\\example.com", "data:text/html,test", "http://[bad", "/path\nexample"):
            form = BannerForm({"title": "Teste", "button_text": "Ver", "link": link, "position": "0"})
            self.assertFalse(form.is_valid(), link)
            self.assertIn("link", form.errors)

    def test_blank_slug_collision_and_case_insensitive_customer_duplicate_are_form_errors(self):
        product = make_product(title="Curso repetido", slug="curso-repetido")
        form = ProductForm({"kind": "course", "title": "Curso repetido", "slug": "", "description": "Teste", "price": "10.00", "lessons": "0"})
        self.assertFalse(form.is_valid())
        self.assertIn("slug", form.errors)
        CustomerAccess.objects.create(email="Cliente@Example.com", product=product)
        access_form = CustomerAccessForm({"email": "cliente@example.com", "product": product.pk, "active": "on"})
        self.assertFalse(access_form.is_valid())
        self.assertIn("email", access_form.errors)
