"""
Gera thumbnails WebP (1200px de largura, qualidade 82) para todas as fotos
em Portfolio/fotos/, salvando em Portfolio/fotos/thumbs/.

Pula fotos que já têm thumbnail atualizado (mtime mais recente que o original).
Executado automaticamente pelo GitHub Action após process_photos.py.
"""

from pathlib import Path
from PIL import Image

FOTOS_DIR  = Path('Portfolio/fotos')
THUMBS_DIR = FOTOS_DIR / 'thumbs'
EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp', '.tif', '.tiff',
              '.JPG', '.JPEG', '.PNG', '.WEBP', '.TIF', '.TIFF'}
MAX_WIDTH  = 1200
QUALITY    = 82


def should_regenerate(src: Path, dst: Path) -> bool:
    """Retorna True se o thumbnail não existe ou está desatualizado."""
    if not dst.exists():
        return True
    return src.stat().st_mtime > dst.stat().st_mtime


def generate_thumb(src: Path):
    stem = src.stem
    dst  = THUMBS_DIR / f"{stem}.webp"

    if not should_regenerate(src, dst):
        print(f"  ok (atualizado): {dst.name}")
        return

    with Image.open(src) as img:
        # Preserva orientação EXIF
        try:
            from PIL.ExifTags import TAGS
            exif = img._getexif()
            if exif:
                for tag, val in exif.items():
                    if TAGS.get(tag) == 'Orientation':
                        from PIL import ImageOps
                        img = ImageOps.exif_transpose(img)
                        break
        except Exception:
            pass

        # Redimensiona mantendo proporção, só se for maior que MAX_WIDTH
        if img.width > MAX_WIDTH:
            ratio  = MAX_WIDTH / img.width
            height = int(img.height * ratio)
            img    = img.resize((MAX_WIDTH, height), Image.LANCZOS)

        img.save(dst, format='WEBP', quality=QUALITY, method=6)
        print(f"  gerado: {dst.name} ({img.width}x{img.height})")


def remove_orphan_thumbs():
    """Remove thumbnails cujo original não existe mais."""
    originals = {f.stem for f in FOTOS_DIR.iterdir()
                 if f.suffix in EXTENSIONS and f.parent == FOTOS_DIR}
    for thumb in THUMBS_DIR.glob('*.webp'):
        if thumb.stem not in originals:
            thumb.unlink()
            print(f"  removido (orphan): {thumb.name}")


def main():
    THUMBS_DIR.mkdir(exist_ok=True)

    fotos = [f for f in FOTOS_DIR.iterdir()
             if f.suffix in EXTENSIONS and f.parent == FOTOS_DIR]

    print(f"Gerando thumbnails para {len(fotos)} foto(s)...")
    for foto in sorted(fotos):
        generate_thumb(foto)

    remove_orphan_thumbs()
    print("Pronto.")


if __name__ == '__main__':
    main()
