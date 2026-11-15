import base64
import io

import requests
from PIL import Image

import config


def process_and_upload_sticker(raw_bytes):
    try:
        img = Image.open(raw_bytes).convert("RGBA")
        img.thumbnail((128, 128))
        canvas = Image.new("RGBA", (128, 128), (0, 0, 0, 0))
        canvas.paste(img, ((128 - img.width) // 2, (128 - img.height) // 2), mask=img)

        out = io.BytesIO()
        canvas.save(out, format="PNG")

        res = requests.post(
            "https://api.imgbb.com/1/upload",
            data={"key": config.IMGBB_KEY, "image": base64.b64encode(out.getvalue()).decode("utf-8")}, timeout=10).json()
        return res.get("data", {}).get("url")
    except Exception as e:
        print(e)
        return None
