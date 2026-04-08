"""
Lê os metadados EXIF/IPTC de todas as fotos em Portfolio/fotos/
e gera/atualiza Portfolio/fotos.json.

Executado automaticamente pelo GitHub Action ao fazer push de novas fotos.
Requer: ExifTool instalado no sistema (sudo apt-get install libimage-exiftool-perl)
"""

import subprocess
import json
from pathlib import Path

FOTOS_DIR   = Path('Projetos/Portfolio/fotos')
OUTPUT_FILE = Path('Projetos/Portfolio/fotos.json')
EXTENSIONS  = {'.jpg', '.jpeg', '.png', '.webp', '.tif', '.tiff',
               '.JPG', '.JPEG', '.PNG', '.WEBP', '.TIF', '.TIFF'}


def get_photo_files():
    return sorted([f for f in FOTOS_DIR.iterdir() if f.suffix in EXTENSIONS])


def run_exiftool(files):
    if not files:
        return []
    cmd = [
        'exiftool', '-json', '-charset', 'UTF8',
        '-FileName',
        '-Title',          # Nome/título da foto (XMP)
        '-ObjectName',     # Nome/título da foto (IPTC, alternativa)
        '-DateTimeOriginal', '-CreateDate',
        '-FNumber',
        '-ExposureTime',
        '-ISO',
        '-FocalLength',    # Distância focal
        '-Make',           # Marca da câmera
        '-Model',          # Modelo da câmera
        '-LensMake',       # Marca da lente
        '-LensModel',      # Modelo da lente
        '-Keywords',       # IPTC tags (Lightroom exporta aqui)
        '-Subject',        # XMP tags (alternativa)
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
        # Remove zeros desnecessários: f/2.8 não f/2.80
        formatted = f'{n:.1f}'.rstrip('0').rstrip('.')
        return f'f/{formatted}'
    except (ValueError, TypeError):
        return str(value)


def format_shutter(value):
    """Converte ExposureTime para formato legível: 1/500s, 1.3s, etc."""
    if not value:
        return ''
    s = str(value)
    if '/' in s:
        return f'{s}s'
    try:
        val = float(s)
        if val >= 1:
            return f'{val:.1f}s'.rstrip('0').rstrip('.')  + 's'
        denom = round(1 / val)
        return f'1/{denom}s'
    except (ValueError, TypeError):
        return s


def format_date(value):
    """Converte '2024:03:15 10:30:00' para '2024-03-15'."""
    if not value:
        return ''
    try:
        return str(value)[:10].replace(':', '-')
    except Exception:
        return str(value)


def format_focal_length(value):
    """Converte FocalLength para formato legível: '85mm', '24mm', etc."""
    if not value:
        return ''
    s = str(value)
    if 'mm' in s.lower():
        # ExifTool já retorna com unidade, ex: "85.0 mm"
        try:
            num = float(s.lower().replace('mm', '').strip())
            return f'{num:.0f}mm'
        except (ValueError, TypeError):
            return s
    try:
        return f'{float(s):.0f}mm'
    except (ValueError, TypeError):
        return s


def build_camera_string(make, model):
    """Combina marca e modelo evitando duplicação (ex: 'SONY' + 'SONY A7 IV')."""
    if not make and not model:
        return ''
    if not make:
        return model
    if not model:
        return make
    # Se o modelo já começa com a marca, não duplica
    if model.upper().startswith(make.upper()):
        return model
    return f'{make} {model}'


def as_list(value):
    """Garante que keywords seja sempre uma lista."""
    if not value:
        return []
    if isinstance(value, list):
        return value
    return [value]


def build_entry(item):
    date_raw = item.get('DateTimeOriginal') or item.get('CreateDate', '')

    keywords = as_list(item.get('Keywords')) or as_list(item.get('Subject'))
    tags = [k.strip().lower() for k in keywords if k.strip()]

    name = (item.get('Title') or item.get('ObjectName') or '').strip()

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


def main():
    files = get_photo_files()
    print(f'Encontradas {len(files)} foto(s) em {FOTOS_DIR}')

    if not files:
        OUTPUT_FILE.write_text('[]', encoding='utf-8')
        print('fotos.json limpo (sem fotos).')
        return

    exif_data = run_exiftool(files)
    fotos = [build_entry(item) for item in exif_data]

    # Ordena por data, mais recente primeiro
    fotos.sort(key=lambda x: x['date'], reverse=True)

    OUTPUT_FILE.write_text(
        json.dumps(fotos, ensure_ascii=False, indent=2),
        encoding='utf-8'
    )
    print(f'fotos.json atualizado com {len(fotos)} foto(s).')


if __name__ == '__main__':
    main()
