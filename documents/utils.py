"""Filigrane de confidentialité appliqué avant l'enregistrement GED."""

from io import BytesIO
from pathlib import Path

from django.core.files.base import ContentFile
from PIL import Image, ImageDraw, ImageFont


WATERMARK_TEXT = "DOCUMENT CONFIDENTIAL - EQDOM"


def apply_confidential_watermark(uploaded_file):
    """Retourne un fichier image filigrané; les PDF sont préservés si pypdf est absent."""
    suffix = Path(uploaded_file.name).suffix.lower()
    if suffix == ".pdf":
        return _watermark_pdf(uploaded_file)
    try:
        return _watermark_image(uploaded_file, suffix)
    except (OSError, ValueError):
        uploaded_file.seek(0)
        return uploaded_file


def _watermark_image(uploaded_file, suffix):
    uploaded_file.seek(0)
    image = Image.open(uploaded_file).convert("RGBA")
    overlay = Image.new("RGBA", image.size, (255, 255, 255, 0))
    drawer = ImageDraw.Draw(overlay)
    font = ImageFont.load_default()
    box = drawer.textbbox((0, 0), WATERMARK_TEXT, font=font)
    x = max(12, (image.width - (box[2] - box[0])) // 2)
    y = max(12, (image.height - (box[3] - box[1])) // 2)
    drawer.text((x, y), WATERMARK_TEXT, font=font, fill=(180, 0, 0, 115))
    result = Image.alpha_composite(image, overlay)
    output = BytesIO()
    image_format = "PNG" if suffix == ".png" else "JPEG"
    if image_format == "JPEG":
        result = result.convert("RGB")
    result.save(output, format=image_format, quality=92)
    return ContentFile(output.getvalue(), name=uploaded_file.name)


def _watermark_pdf(uploaded_file):
    """Ajoute un calque texte à chaque page PDF avec pypdf + ReportLab."""
    from pypdf import PdfReader, PdfWriter
    from reportlab.pdfgen import canvas

    uploaded_file.seek(0)
    reader = PdfReader(uploaded_file)
    writer = PdfWriter()
    for page in reader.pages:
        width, height = float(page.mediabox.width), float(page.mediabox.height)
        layer = BytesIO()
        stamp = canvas.Canvas(layer, pagesize=(width, height))
        stamp.setFillColorRGB(0.7, 0, 0)
        stamp.setFillAlpha(0.25)
        stamp.setFont("Helvetica-Bold", 18)
        stamp.translate(width / 2, height / 2)
        stamp.rotate(35)
        stamp.drawCentredString(0, 0, WATERMARK_TEXT)
        stamp.save()
        layer.seek(0)
        page.merge_page(PdfReader(layer).pages[0])
        writer.add_page(page)
    output = BytesIO()
    writer.write(output)
    return ContentFile(output.getvalue(), name=uploaded_file.name)
