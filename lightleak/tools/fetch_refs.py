"""Baixa as fotografias de referência de alta resolução do Wikimedia Commons.

As 25 imagens que serviram de referência visual são pequenas — a maior tem 65 KB.
Extrair máscara delas e aplicar numa foto de 7000 px significa ampliar 8x, e o
vinco vira borrão chapado. Estas são scans de 3000 a 8000 px de fotografias com
dano real, do Commons, com licença que permite obra derivada.

A procedência de cada uma está em refs/SOURCES.md, inclusive quais exigem
atribuição.

    python3 tools/fetch_refs.py -o refs_hi
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import time
import urllib.request

# O Commons exige User-Agent descritivo com forma de contato, e limita taxa: sem
# intervalo entre os pedidos ele devolve 429 e grava um corpo de erro de 2 KB no
# lugar da imagem.
UA = "lightleak/1.0 (https://github.com/pedrohenriquefonseca/python; film damage masks)"
PAUSE = 2.0

FILES: dict[str, str] = {
    "nb-gruppebilde.jpg":
        "https://upload.wikimedia.org/wikipedia/commons/3/3a/"
        "Gruppebilde_med_blant_annet_Bj%C3%B8rnstjerne_Bj%C3%B8rnson_sterkt_skadet_"
        "-_no-nb_digifoto_20160609_00068_bldsa_BB1802.jpg",
    "fortepan-kavehaz.jpg":
        "https://upload.wikimedia.org/wikipedia/commons/0/04/"
        "New_York_k%C3%A1v%C3%A9h%C3%A1z._Fortepan_2033.jpg",
    "fortepan-girl.jpg":
        "https://upload.wikimedia.org/wikipedia/commons/6/63/"
        "Girl%2C_portrait_Fortepan_1999.jpg",
    "fortepan-beach.jpg":
        "https://upload.wikimedia.org/wikipedia/commons/5/5f/"
        "Beach%2C_kids%2C_smile_Fortepan_29088.jpg",
    "leguery.jpg":
        "https://upload.wikimedia.org/wikipedia/commons/0/0d/Jules_Charles_le_Gu%C3%A9ry.jpg",
    "wellcome-amoy.jpg":
        "https://upload.wikimedia.org/wikipedia/commons/3/35/"
        "Amoy_Woman_in_Shanghai._Wellcome_V0037201.jpg",
    "wallin-family.jpg":
        "https://upload.wikimedia.org/wikipedia/commons/8/82/Sofia_Jansdotter_Wallin_family.jpg",
    "dunesmobile.jpg":
        "https://upload.wikimedia.org/wikipedia/commons/0/03/"
        "Sleeping_Bear_Dunesmobile_%282981630709%29.jpg",
    "navy-80g.jpg":
        "https://upload.wikimedia.org/wikipedia/commons/7/73/80-G-27208_%2831323126572%29.jpg",
    "trutat-foire.jpg":
        "https://upload.wikimedia.org/wikipedia/commons/8/83/"
        "A_la_foire%2C_Foix%2C_novembre_1905_%282576873197%29.jpg",
    "trutat-velo.jpg":
        "https://upload.wikimedia.org/wikipedia/commons/4/4b/"
        "Courses_de_v%C3%A9locip%C3%A8des%2C_Luchon%2C_septembre_1896%2C_TRU_C_39_"
        "-_Fonds_Trutat.jpg",
    "trutat-cafe.jpg":
        "https://upload.wikimedia.org/wikipedia/commons/f/f0/"
        "Caf%C3%A9_de_la_Paix%2C_Ax-les-Thermes_%28Ari%C3%A8ge%29_%282567730284%29.jpg",
    "albi-archeveche.jpg":
        "https://upload.wikimedia.org/wikipedia/commons/a/ae/"
        "Archev%C3%AAch%C3%A9%2C_Albi%2C_20_avril_1895_-_btv1b105774362.jpg",
    "nara-colorado.jpg":
        "https://upload.wikimedia.org/wikipedia/commons/1/1f/"
        "Colorado_River._Grand_Canyon%2C_Tapeets_Creek._%28Note%2C_it_appears_that_"
        "the_glass_negative_may_have_broken_or_cracked_all..._-_NARA_-_518020.jpg",
    "oo-bloc.jpg":
        "https://upload.wikimedia.org/wikipedia/commons/2/2a/"
        "Oo_bloc_erratique%2C_Luchon_%28environs%29_%288189485429%29.jpg",
    "bhl-africa.jpg":
        "https://upload.wikimedia.org/wikipedia/commons/9/9e/"
        "In_wildest_Africa_%28Page_669%29_BHL23041556.jpg",
}


def _get(url: str, dest: str) -> None:
    """urllib primeiro; curl como reserva.

    Em rede que bloqueia o endpoint de OCSP, o schannel do Windows recusa a
    conexão por não *conseguir checar* revogação — a cadeia em si valida. O
    `--ssl-no-revoke` desliga só essa checagem, e não a verificação do
    certificado.
    """
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=120) as r, open(dest, "wb") as f:
            f.write(r.read())
        return
    except Exception as exc:
        curl = shutil.which("curl")
        if not curl:
            raise
        print(f"  urllib falhou ({type(exc).__name__}), tentando curl")
        subprocess.run(
            [curl, "-sS", "-L", "--ssl-no-revoke", "-A", UA, "-o", dest, url],
            check=True,
        )


def main() -> None:
    ap = argparse.ArgumentParser(description="Baixa as referências de alta resolução")
    ap.add_argument("-o", "--output", default="refs_hi")
    a = ap.parse_args()

    os.makedirs(a.output, exist_ok=True)
    for name, url in FILES.items():
        dest = os.path.join(a.output, name)
        # Um corpo de erro 429 tem uns 2 KB; qualquer scan de verdade tem megabytes.
        if os.path.exists(dest) and os.path.getsize(dest) > 100_000:
            print(f"{name:<24} já existe")
            continue

        for attempt in range(5):
            if attempt:
                time.sleep(PAUSE * 2**attempt)
            _get(url, dest)
            if os.path.getsize(dest) > 100_000:
                break
            print(f"{name:<24} tentativa {attempt+1} recusada, esperando")
        else:
            print(f"{name:<24} FALHOU")
            continue

        print(f"{name:<24} {os.path.getsize(dest)/1e6:6.2f} MB")
        time.sleep(PAUSE)


if __name__ == "__main__":
    main()
