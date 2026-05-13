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


def _load_font(size: int) -> ImageFont.FreeTypeFont:
    for name in ("LiberationSans-Regular.ttf", "DejaVuSans.ttf", "arial.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def generate_captcha_image(code: str) -> BytesIO:
    """根据验证码文本生成 PNG 图片，返回二进制流"""
    width, height = 180, 64
    bg_color = (245, 245, 250)
    font_size = 36

    img = Image.new("RGB", (width, height), bg_color)
    draw = ImageDraw.Draw(img)

    # 随机干扰点
    for _ in range(150):
        x = secrets.randbelow(width)
        y = secrets.randbelow(height)
        draw.point((x, y), fill=_random_color())

    # 随机干扰线
    for _ in range(3):
        x1, y1 = secrets.randbelow(width), secrets.randbelow(height)
        x2, y2 = secrets.randbelow(width), secrets.randbelow(height)
        draw.line([(x1, y1), (x2, y2)], fill=_random_color(), width=1)

    font = _load_font(font_size)

    for i, ch in enumerate(code):
        x = 15 + i * 40 + secrets.randbelow(10)
        y = 10 + secrets.randbelow(12)
        draw.text((x, y), ch, font=font, fill=_random_color())

    img = img.filter(ImageFilter.GaussianBlur(radius=0.5))

    buf = BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf


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
