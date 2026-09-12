import base64, uuid
from django.core.files.base import ContentFile

def decode_base64_image(data, employee_id, action):
    try:
        fmt, imgstr = data.split(';base64,')
        from datetime import datetime
        ts       = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{employee_id}_{ts}_{action}.jpg"
        return ContentFile(base64.b64decode(imgstr), name=filename)
    except Exception:
        return None