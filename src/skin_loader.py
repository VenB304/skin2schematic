import os
import requests
import io
import base64
import re
from PIL import Image

class SkinLoader:
    MOJANG_PROFILE_URL = "https://api.mojang.com/users/profiles/minecraft/{}"
    MOJANG_SESSION_URL = "https://sessionserver.mojang.com/session/minecraft/profile/{}"

    @staticmethod
    def load_skin(source: str) -> Image.Image:
        """
        Loads a skin from a file path, URL, or Minecraft username.
        """
        if os.path.exists(source):
            return SkinLoader._load_from_file(source)
        elif source.startswith("http://") or source.startswith("https://"):
            return SkinLoader._load_from_url(source)
        elif re.match(r"^[a-zA-Z0-9_]{3,16}$", source):
            return SkinLoader._load_from_username(source)
        else:
            raise ValueError(f"Invalid skin source: {source}")

    @staticmethod
    def _load_from_file(path: str) -> Image.Image:
        try:
            img = Image.open(path)
            img.load() # Force load
            return SkinLoader._validate_and_process(img)
        except Exception as e:
            raise ValueError(f"Failed to load skin from file: {e}")

    @staticmethod
    def _load_from_url(url: str) -> Image.Image:
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            img = Image.open(io.BytesIO(response.content))
            return SkinLoader._validate_and_process(img)
        except Exception as e:
            raise ValueError(f"Failed to load skin from URL: {e}")

    @staticmethod
    def _load_from_username(username: str) -> Image.Image:
        try:
            # 1. Get UUID
            resp = requests.get(SkinLoader.MOJANG_PROFILE_URL.format(username), timeout=10)
            resp.raise_for_status()
            data = resp.json()
            uuid = data.get("id")
            if not uuid:
                raise ValueError("User not found")

            # 2. Get Profile (Skin URL)
            resp = requests.get(SkinLoader.MOJANG_SESSION_URL.format(uuid), timeout=10)
            resp.raise_for_status()
            data = resp.json()
            properties = data.get("properties", [])
            texture_data = None
            for prop in properties:
                if prop.get("name") == "textures":
                    texture_data = prop.get("value")
                    break
            
            if not texture_data:
                raise ValueError("No texture data found")

            decoded = base64.b64decode(texture_data).decode('utf-8')
            # Use standard json lib if requests one is weird, but requests.utils should be fine or just standard json
            import json
            texture_json = json.loads(decoded)
            skin_url = texture_json.get("textures", {}).get("SKIN", {}).get("url")
            
            if not skin_url:
                raise ValueError("No skin URL found in texture data")
                
            return SkinLoader._load_from_url(skin_url)

        except Exception as e:
            raise ValueError(f"Failed to fetch skin for user '{username}': {e}")

    @staticmethod
    def _validate_and_process(img: Image.Image) -> Image.Image:
        """
        Validates dimensions and converts to RGBA.
        Attempts to upgrade 64x32 skins to 64x64.
        """
        if img.mode != 'RGBA':
            img = img.convert('RGBA')

        width, height = img.size
        
        if width == 64 and height == 64:
            return img
        elif width == 64 and height == 32:
            print("Detected 64x32 skin, converting to 64x64 (basic extension)...")
            new_img = Image.new('RGBA', (64, 64), (0, 0, 0, 0))
            new_img.paste(img, (0, 0))
            # Basic legacy upgrade logic could go here: mirroring legs/arms
            # For now, we return the canvas.
            # TODO: Implement full legacy conversion if needed
            return new_img
        else:
            raise ValueError(f"Unsupported skin dimensions: {width}x{height}. Must be 64x64.")

    @staticmethod
    def detect_model(img: Image.Image) -> str:
        """
        Detects if skin is Classic (Steve) or Slim (Alex).
        Checks pixel at (54, 20) (right arm back). If transparent -> Alex.
        """
        # (54, 20) is often used to detect slim model
        # 1-indexed: 55, 21. 0-indexed: 54, 20.
        try:
            r, g, b, a = img.getpixel((54, 20))
            if a == 0:
                return "slim"
        except Exception:
            pass # boundary check?
        return "classic"
