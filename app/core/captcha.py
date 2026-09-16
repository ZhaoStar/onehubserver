import secrets
import time
import uuid
from io import BytesIO

from PIL import Image, ImageDraw, ImageFont, ImageFilter


# 内存缓存：{key: (code, expire_time)}
_store: dict[str, tuple[str, float]] = {}
# 验证码有效期（秒）
CAPTCHA_TTL = 300  # 5 分钟


def _clean_expired():
    """清理过期的验证码"""
    now = time.time()
    expired = [k for k, (_, exp) in _store.items() if now > exp]
    for k in expired:
        del _store[k]


def generate_code(length: int = 4) -> str:
    """随机生成验证码文本（数字+大写字母，排除易混淆字符）"""
    chars = "23456789ABCDEFGHJKLMNPQRSTUVWXYZ"
    return "".join(secrets.choice(chars) for _ in range(length))


_cached_font: ImageFont.FreeTypeFont | ImageFont.ImageFont | None = None


def _get_font(size: int = 36) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    global _cached_font
    if _cached_font is not None:
        return _cached_font
    for name in ("LiberationSans-Regular.ttf", "DejaVuSans.ttf", "arial.ttf"):
        try:
            _cached_font = ImageFont.truetype(name, size)
            return _cached_font
        except OSError:
            continue
    _cached_font = ImageFont.load_default()
    return _cached_font


def generate_captcha_image(code: str) -> bytes:
    """根据验证码文本生成 PNG 图片，直接返回极速二进制字节数据"""
    width, height = 180, 64
    bg_color = (245, 245, 250)

    img = Image.new("RGB", (width, height), bg_color)
    draw = ImageDraw.Draw(img)

    # 适量随机干扰点
    for _ in range(80):
        x = secrets.randbelow(width)
        y = secrets.randbelow(height)
        draw.point((x, y), fill=_random_color())

    # 随机干扰线
    for _ in range(3):
        x1, y1 = secrets.randbelow(width), secrets.randbelow(height)
        x2, y2 = secrets.randbelow(width), secrets.randbelow(height)
        draw.line([(x1, y1), (x2, y2)], fill=_random_color(), width=1)

    font = _get_font(36)

    for i, ch in enumerate(code):
        x = 18 + i * 38 + secrets.randbelow(8)
        y = 10 + secrets.randbelow(10)
        draw.text((x, y), ch, font=font, fill=_random_color())

    buf = BytesIO()
    img.save(buf, format="PNG", optimize=False)
    return buf.getvalue()


def _random_color() -> tuple[int, int, int]:
    return secrets.randbelow(128), secrets.randbelow(128), secrets.randbelow(128)


def store_code(code: str) -> str:
    """存储验证码，返回唯一 key"""
    _clean_expired()
    key = uuid.uuid4().hex
    _store[key] = (code.lower(), time.time() + CAPTCHA_TTL)
    return key


def verify_code(key: str, user_input: str) -> bool:
    """校验验证码，无论成功与否都删除该 key（一次性使用）"""
    entry = _store.pop(key, None)
    if entry is None:
        return False
    code, expire = entry
    if time.time() > expire:
        return False
    return code == user_input.lower().strip()
