"""Normalize uploaded product photos and serve only the stored raster bytes."""

from dataclasses import dataclass
from hashlib import sha256
from io import BytesIO
import warnings

from django.core.exceptions import ValidationError
from django.http import HttpResponse, HttpResponseNotModified, Http404
from django.shortcuts import get_object_or_404
from django.utils.cache import patch_vary_headers
from django.utils.http import parse_etags
from django.views.decorators.http import require_safe
from PIL import Image, ImageOps, UnidentifiedImageError

from .models import CustomerAccess, ProductImage


MAX_UPLOAD_BYTES = 5 * 1024 * 1024
MAX_IMAGE_PIXELS = 20_000_000
MAX_IMAGE_EDGE = 1600
MAX_STORED_BYTES = 600 * 1024
ALLOWED_FORMATS = ("JPEG", "PNG", "WEBP")


@dataclass(frozen=True)
class NormalizedImage:
    data: bytes
    checksum: str
    width: int
    height: int
    content_type: str = "image/webp"

    def model_values(self):
        return {"data": self.data, "checksum": self.checksum, "width": self.width,
                "height": self.height, "content_type": self.content_type, "byte_size": len(self.data)}


def normalize_upload(upload):
    if upload.size > MAX_UPLOAD_BYTES:
        raise ValidationError("A foto deve ter no máximo 5 MB.")
    upload.seek(0)
    data = upload.read(MAX_UPLOAD_BYTES + 1)
    upload.seek(0)
    if len(data) > MAX_UPLOAD_BYTES:
        raise ValidationError("A foto deve ter no máximo 5 MB.")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(BytesIO(data), formats=ALLOWED_FORMATS) as source:
                if source.width * source.height > MAX_IMAGE_PIXELS:
                    raise ValidationError("A foto deve ter no máximo 20 milhões de pixels.")
                if getattr(source, "is_animated", False) or getattr(source, "n_frames", 1) != 1:
                    raise ValidationError("Envie uma foto estática. Imagens animadas não são aceitas.")
                source.verify()
            with Image.open(BytesIO(data), formats=ALLOWED_FORMATS) as source:
                source.draft("RGB", (MAX_IMAGE_EDGE, MAX_IMAGE_EDGE))
                source.load()
                source.thumbnail((MAX_IMAGE_EDGE, MAX_IMAGE_EDGE), Image.Resampling.LANCZOS)
                ImageOps.exif_transpose(source, in_place=True)
                mode = "RGBA" if source.mode in ("RGBA", "LA") or "transparency" in source.info else "RGB"
                # A new pixel-only image ensures EXIF, GPS, ICC, comments and XMP are not retained.
                normalized = Image.new(mode, source.size)
                normalized.paste(source.convert(mode))
                previous_size = None
                for edge in (MAX_IMAGE_EDGE, 1280, 1024, 800, 640, 512):
                    normalized.thumbnail((edge, edge), Image.Resampling.LANCZOS)
                    if normalized.size == previous_size:
                        continue
                    previous_size = normalized.size
                    for quality in (82, 66, 50, 40):
                        output = BytesIO()
                        normalized.save(output, format="WEBP", quality=quality, method=4,
                                        exif=b"", icc_profile=b"", xmp=b"")
                        encoded = output.getvalue()
                        if len(encoded) <= MAX_STORED_BYTES:
                            return NormalizedImage(encoded, sha256(encoded).hexdigest(),
                                                   normalized.width, normalized.height)
    except (UnidentifiedImageError, OSError, ValueError, SyntaxError, Image.DecompressionBombWarning, Image.DecompressionBombError):
        raise ValidationError("Não foi possível ler esta foto. Envie um arquivo JPEG, PNG ou WebP válido.")
    raise ValidationError("Não foi possível reduzir esta foto. Tente enviar outra imagem.")


@require_safe
def product_image(request, pk, checksum):
    image = get_object_or_404(ProductImage.objects.select_related("product").defer("data"),
                              product_id=pk, checksum=checksum)
    private = not image.product.active
    if private:
        staff = request.user.is_active and request.user.is_staff
        email = request.session.get("customer_verified", "")
        customer = bool(email) and CustomerAccess.objects.filter(email__iexact=email,
                                                                product_id=pk, active=True).exists()
        if not staff and not customer:
            raise Http404
    etag = f'"{image.checksum}"'
    matches = parse_etags(request.headers.get("If-None-Match", ""))
    if not private and ("*" in matches or etag in [value.removeprefix("W/") for value in matches]):
        response = HttpResponseNotModified()
    else:
        data = bytes(image.data)
        response = HttpResponse(data if request.method != "HEAD" else b"", content_type="image/webp")
        response["Content-Length"] = str(len(data))
    response["ETag"] = etag
    response["X-Content-Type-Options"] = "nosniff"
    response["Cache-Control"] = "private, no-store" if private else "public, max-age=0, must-revalidate"
    patch_vary_headers(response, ("Cookie",))
    return response
