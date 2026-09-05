"""QR code generator for secure share links and tokens."""

from __future__ import annotations

import io

try:
    import qrcode
    from qrcode.main import QRCode
except ImportError:
    qrcode = None  # type: ignore[assignment]
    QRCode = None  # type: ignore[assignment, misc]


def generate_qr_ascii(data: str) -> str:
    """Generate ASCII representation of QR code suitable for terminal display."""
    if qrcode is None:
        return f"[QR Code: {data}]"

    qr = QRCode(box_size=1, border=1)
    qr.add_data(data)
    qr.make(fit=True)

    # Use StringIO to capture terminal ASCII
    buf = io.StringIO()
    qr.print_ascii(out=buf)
    return buf.getvalue()


def generate_qr_png(data: str, box_size: int = 10, border: int = 4) -> bytes:
    """Generate PNG image bytes for web display or download."""
    if qrcode is None:
        raise ImportError("qrcode package is required. Install with `uv pip install qrcode[pil]`.")

    qr = QRCode(box_size=box_size, border=border)
    qr.add_data(data)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()
