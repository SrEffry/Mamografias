"""
00_seleccion_subconjunto.py
Elige un subconjunto de lesiones de CBIS-DDSM (masas) para descargar y lista
las series DICOM necesarias.

Criterios (documentar en la bitácora):
  - Se elige por PACIENTE: todas las lesiones de un paciente entran juntas.
  - Se estratifica por etiqueta (benigna/maligna) con StratifiedGroupKFold.
  - Se respeta la partición oficial: se toman lesiones del train oficial y del
    test oficial, para conservar una prueba que no comparte pacientes con train.
  - Los pacientes ya descargados se conservan siempre.
  - Solo se piden las series ROI (recorte + máscara). La mamografía completa no
    es necesaria porque el modelo usa el recorte.

Uso:
  python src/00_seleccion_subconjunto.py --data data --out seleccion \
      --ya_descargadas lesiones_descargadas.txt --objetivo_train 300 --objetivo_test 100

Salidas (en --out):
  seleccion_lesiones.csv   todas las lesiones elegidas (nuevas y ya descargadas)
  series_a_descargar.txt   SeriesInstanceUID de las series ROI de las lesiones NUEVAS
"""
import argparse
import os

import pandas as pd
from sklearn.model_selection import StratifiedGroupKFold

SEED = 42


def cargar(ruta_csv, particion):
    df = pd.read_csv(ruta_csv).rename(columns={"breast density": "breast_density"})
    for c in ["image file path", "cropped image file path", "ROI mask file path"]:
        df[c] = df[c].str.strip()
    df["label"] = (df["pathology"] == "MALIGNANT").astype(int)
    df["lesion_id"] = (df["patient_id"] + "_" + df["left or right breast"] + "_"
                       + df["image view"] + "_" + df["abnormality id"].astype(str))
    df["serie_crop"] = df["cropped image file path"].str.split("/").str[2]
    df["serie_mask"] = df["ROI mask file path"].str.split("/").str[2]
    df["particion_oficial"] = particion
    return df


def elegir(d, ya_pacientes, objetivo):
    """Devuelve el subconjunto de d: pacientes ya descargados + pacientes nuevos
    hasta aproximarse a 'objetivo' lesiones."""
    obligatorios = d[d.patient_id.isin(ya_pacientes)]
    falta = objetivo - len(obligatorios)
    if falta <= 0:
        return obligatorios
    pool = d[~d.patient_id.isin(ya_pacientes)].reset_index(drop=True)
    # Un fold de k particiones ~ len(pool)/k lesiones
    k = int(min(max(2, round(len(pool) / falta)), pool.patient_id.nunique()))
    sgkf = StratifiedGroupKFold(n_splits=k, shuffle=True, random_state=SEED)
    _, idx = next(sgkf.split(pool, pool["label"], groups=pool["patient_id"]))
    return pd.concat([obligatorios, pool.iloc[idx]], ignore_index=True)


def resumen(nombre, d):
    return (f"{nombre:<14} {len(d):>4} lesiones | {d.patient_id.nunique():>4} pacientes | "
            f"{int(d.label.sum()):>4} malignas / {int((1 - d.label).sum()):>4} benignas")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="data")
    ap.add_argument("--out", default="seleccion")
    ap.add_argument("--ya_descargadas", default=None, help="txt con lesion_id ya descargados")
    ap.add_argument("--objetivo_train", type=int, default=300)
    ap.add_argument("--objetivo_test", type=int, default=100)
    a = ap.parse_args()

    tr = cargar(os.path.join(a.data, "mass_case_description_train_set.csv"), "train")
    te = cargar(os.path.join(a.data, "mass_case_description_test_set.csv"), "test")
    assert set(tr.patient_id).isdisjoint(te.patient_id)

    ya = set()
    if a.ya_descargadas:
        with open(a.ya_descargadas) as f:
            ya = {l.strip() for l in f if l.strip()}
    todo = pd.concat([tr, te], ignore_index=True)
    ya_pacientes = set(todo[todo.lesion_id.isin(ya)].patient_id)

    sel = pd.concat([elegir(tr, ya_pacientes, a.objetivo_train),
                     elegir(te, ya_pacientes, a.objetivo_test)], ignore_index=True)
    assert sel.lesion_id.is_unique
    assert set(sel[sel.particion_oficial == "train"].patient_id).isdisjoint(
        sel[sel.particion_oficial == "test"].patient_id)

    sel["ya_descargada"] = sel.lesion_id.isin(ya)
    nuevas = sel[~sel.ya_descargada]
    series = sorted(set(nuevas.serie_crop) | set(nuevas.serie_mask))

    print(resumen("train oficial", sel[sel.particion_oficial == "train"]))
    print(resumen("test oficial", sel[sel.particion_oficial == "test"]))
    print(resumen("TOTAL", sel))
    print(f"Lesiones nuevas a descargar: {len(nuevas)} | series ROI a descargar: {len(series)}")

    os.makedirs(a.out, exist_ok=True)
    sel.drop(columns=["image file path"]).to_csv(os.path.join(a.out, "seleccion_lesiones.csv"), index=False)
    with open(os.path.join(a.out, "series_a_descargar.txt"), "w") as f:
        f.write("\n".join(series))


if __name__ == "__main__":
    main()
