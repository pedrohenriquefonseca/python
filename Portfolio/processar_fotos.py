"""
Processa fotos em Portfolio/fotos/:
- Lê EXIF e atualiza fotos.json (preservando metadados editados manualmente)
- Gera thumbnails WebP em Portfolio/fotos/thumbs/
- Remove thumbs órfãos

Executado automaticamente pelo git hook pre-commit.
"""

import subprocess
import json
from pathlib import Path
from PIL import Image, ImageOps

FOTOS_DIR   = Path(__file__).parent / 'fotos'
THUMBS_DIR  = FOTOS_DIR / 'thumbs'
OUTPUT_FILE = Path(__file__).parent / 'fotos.json'
EXTENSIONS  = {'.jpg', '.jpeg', '.png', '.webp', '.tif', '.tiff',
               '.JPG', '.JPEG', '.PNG', '.WEBP', '.TIF', '.TIFF'}
MAX_WIDTH   = 1200
QUALITY     = 82


# ─── EXIF ─────────────────────────────────────────────────────────────────────

def get_photo_files():
    return sorted([f for f in FOTOS_DIR.iterdir()
                   if f.is_file() and f.suffix in EXTENSIONS])


def run_exiftool(files):
    if not files:
        return []
    cmd = [
        'exiftool', '-json', '-charset', 'UTF8',
        '-FileName', '-Title', '-XPTitle', '-ObjectName',
        '-DateTimeOriginal', '-CreateDate',
        '-FNumber', '-ExposureTime', '-ISO', '-FocalLength',
        '-Make', '-Model', '-LensMake', '-LensModel',
        '-Keywords', '-Subject', '-XPKeywords',
    ] + [str(f) for f in files]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f'Erro no ExifTool: {result.stderr}')
        return []
    return json.loads(result.stdout)


def format_aperture(value):
    if not value:
        return ''
    try:
        n = float(value)
        return f'f/{n:.1f}'.rstrip('0').rstrip('.')
    except (ValueError, TypeError):
        return str(value)


def format_shutter(value):
    if not value:
        return ''
    s = str(value)
    if '/' in s:
        return f'{s}s'
    try:
        val = float(s)
        if val >= 1:
            return f'{val:.1f}s'.rstrip('0').rstrip('.') + 's'
        return f'1/{round(1 / val)}s'
    except (ValueError, TypeError):
        return s


def format_date(value):
    if not value:
        return ''
    return str(value)[:10].replace(':', '-')


def format_focal_length(value):
    if not value:
        return ''
    s = str(value)
    try:
        num = float(s.lower().replace('mm', '').strip())
        return f'{num:.0f}mm'
    except (ValueError, TypeError):
        return s


def build_camera_string(make, model):
    if not make and not model:
        return ''
    if not make:
        return model
    if not model:
        return make
    if model.upper().startswith(make.upper()):
        return model
    return f'{make} {model}'


def as_list(value):
    if not value:
        return []
    if isinstance(value, list):
        return value
    return [value]


def build_entry_from_exif(item):
    date_raw = item.get('DateTimeOriginal') or item.get('CreateDate', '')
    xp_keywords = []
    if item.get('XPKeywords'):
        xp_keywords = [k.strip() for k in str(item['XPKeywords']).split(';') if k.strip()]
    keywords = as_list(item.get('Keywords')) or as_list(item.get('Subject')) or xp_keywords
    tags = [k.strip() for k in keywords if k.strip()]
    name = (item.get('Title') or item.get('XPTitle') or item.get('ObjectName') or '').strip()
    return {
        'filename':    item.get('FileName', ''),
        'name':        name,
        'publicId':    '',
        'date':        format_date(date_raw),
        'aperture':    format_aperture(item.get('FNumber')),
        'shutter':     format_shutter(item.get('ExposureTime')),
        'iso':         item.get('ISO', ''),
        'focalLength': format_focal_length(item.get('FocalLength')),
        'camera':      build_camera_string(item.get('Make', ''), item.get('Model', '')),
        'lens':        (item.get('LensModel') or item.get('LensMake') or '').strip(),
        'tags':        tags,
    }


# ─── Campos editáveis manualmente (preservados ao reprocessar) ────────────────

MANUAL_FIELDS = {'name', 'tags', 'publicId'}


def load_existing_json():
    if OUTPUT_FILE.exists():
        try:
            return {e['filename']: e for e in json.loads(OUTPUT_FILE.read_text(encoding='utf-8'))}
        except Exception:
            pass
    return {}


# ─── Thumbnails ───────────────────────────────────────────────────────────────

def generate_thumb(src: Path):
    stem = src.stem
    dst  = THUMBS_DIR / f'{stem}.webp'
    if dst.exists() and src.stat().st_mtime <= dst.stat().st_mtime:
        return False  # já atualizado
    with Image.open(src) as img:
        try:
            img = ImageOps.exif_transpose(img)
        except Exception:
            pass
        if img.width > MAX_WIDTH:
            ratio  = MAX_WIDTH / img.width
            height = int(img.height * ratio)
            img    = img.resize((MAX_WIDTH, height), Image.LANCZOS)
        img.save(dst, format='WEBP', quality=QUALITY, method=6)
    print(f'  thumb gerado: {dst.name}')
    return True


def remove_orphan_thumbs(filenames):
    stems = {Path(f).stem for f in filenames}
    for thumb in THUMBS_DIR.glob('*.webp'):
        if thumb.stem not in stems:
            thumb.unlink()
            print(f'  thumb removido: {thumb.name}')


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    THUMBS_DIR.mkdir(exist_ok=True)

    files = get_photo_files()
    print(f'{len(files)} foto(s) encontrada(s).')

    # Carrega metadados existentes (preserva edições manuais)
    existing = load_existing_json()

    # Lê EXIF de todas as fotos
    exif_data = run_exiftool(files) if files else []
    exif_by_filename = {item['FileName']: item for item in exif_data}

    fotos = []
    for f in files:
        exif = exif_by_filename.get(f.name, {'FileName': f.name})
        new_entry = build_entry_from_exif(exif)

        # Preserva campos editados manualmente se a foto já existia no JSON
        if f.name in existing:
            old = existing[f.name]
            for field in MANUAL_FIELDS:
                if old.get(field):
                    new_entry[field] = old[field]

        fotos.append(new_entry)
        generate_thumb(f)

    # Remove thumbs de fotos que não existem mais
    remove_orphan_thumbs([f.name for f in files])

    # Ordena por data, mais recente primeiro
    fotos.sort(key=lambda x: x['date'], reverse=True)

    OUTPUT_FILE.write_text(
        json.dumps(fotos, ensure_ascii=False, indent=2),
        encoding='utf-8'
    )
    print(f'fotos.json atualizado com {len(fotos)} foto(s).')


if __name__ == '__main__':
    main()
