"""QR code generation helper used by document exports."""

import io

import qrcode


def generate_qr_image(data, box_size=4, border=2):
    """Return a BytesIO PNG buffer containing a QR code for `data`."""
    qr = qrcode.QRCode(box_size=box_size, border=border)
    qr.add_data(data)
    qr.make(fit=True)
    image = qr.make_image(fill_color="black", back_color="white")
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    buffer.seek(0)
    return buffer
