"""
01_particion.py
Prepara la tabla de lesiones de CBIS-DDSM (masas) y la divide en
entrenamiento / validación / prueba POR PACIENTE.

Decisiones (ver BITACORA.md):
  - Unidad de análisis: la lesión.
  - Etiqueta binaria: MALIGNANT -> 1; BENIGN y BENIGN_WITHOUT_CALLBACK -> 0.
  - Ningún paciente aparece en más de una partición (StratifiedGroupKFold
    agrupando por patient_id, estratificado por etiqueta).
  - La prueba NO se usa para elegir hiperparámetros ni umbral.

Modos (--modo):
  oficial : prueba = test oficial; validación = ~1/6 del train oficial.
  propio  : se juntan las lesiones disponibles de train y test oficiales y se
            reparten por paciente en ~5/7 train, ~1/7 val y ~1/7 test.
            (Train y test oficiales no comparten pacientes, así que juntar
            sus lesiones no introduce fuga.)

Uso:
  python src/01_particion.py --data data --out particiones --modo propio \
      --disponibles lesiones_descargadas.txt
"""
import argparse
import os

import pandas as pd
from sklearn.model_selection import StratifiedGroupKFold

SEED = 42
MIN_MALIGNAS = 15  # por debajo de esto se avisa: la sensibilidad será muy inestable


def cargar(ruta_csv, particion_oficial):
    df = pd.read_csv(ruta_csv)
    df = df.rename(columns={"breast density": "breast_density"})
    for c in ["image file path", "cropped image file path", "ROI mask file path"]:
        df[c] = df[c].str.strip()
    df["label"] = (df["pathology"] == "MALIGNANT").astype(int)
    df["lesion_id"] = (
        df["patient_id"] + "_" + df["left or right breast"] + "_"
        + df["image view"] + "_" + df["abnormality id"].astype(str)
    )
    df["carpeta_roi"] = df["cropped image file path"].str.split("/").str[0]
    df["particion_oficial"] = particion_oficial
    return df


def dividir(d, n_splits):
    """Separa d en (resto, fold) por paciente; fold ~ 1/n_splits de las lesiones."""
    d = d.reset_index(drop=True)
    sgkf = StratifiedGroupKFold(n_splits=n_splits, shuffle=True, random_state=SEED)
    i_resto, i_fold = next(sgkf.split(d, d["label"], groups=d["patient_id"]))
    return d.iloc[i_resto].copy(), d.iloc[i_fold].copy()


def resumen(nombre, d):
    return (f"{nombre:<6} {len(d):>5} lesiones | {d.patient_id.nunique():>4} pacientes | "
            f"{int(d.label.sum()):>4} malignas / {int((1 - d.label).sum()):>4} benignas "
            f"({100 * d.label.mean():.1f} % malignas)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="data", help="carpeta con los CSV de CBIS-DDSM")
    ap.add_argument("--out", default="particiones", help="carpeta de salida")
    ap.add_argument("--disponibles", default=None, help="txt con lesion_id descargados")
    ap.add_argument("--modo", choices=["oficial", "propio"], default="oficial")
    ap.add_argument("--semilla", type=int, default=42)
    a = ap.parse_args()
    global SEED
    SEED = a.semilla

    tr_of = cargar(os.path.join(a.data, "mass_case_description_train_set.csv"), "train")
    te_of = cargar(os.path.join(a.data, "mass_case_description_test_set.csv"), "test")

    # ---- Comprobaciones de calidad de la tabla ----
    todo = pd.concat([tr_of, te_of], ignore_index=True)
    assert todo["lesion_id"].is_unique, "lesion_id no es único: revisar duplicados"
    assert set(tr_of.patient_id).isdisjoint(te_of.patient_id), \
        "Train y test oficiales comparten pacientes"

    # ---- Filtro por lo realmente descargado ----
    if a.disponibles:
        with open(a.disponibles) as f:
            disp = {l.strip() for l in f if l.strip()}
        tr_of = tr_of[tr_of.lesion_id.isin(disp)].reset_index(drop=True)
        te_of = te_of[te_of.lesion_id.isin(disp)].reset_index(drop=True)
        print(f"Filtro por disponibles: {len(todo)} -> {len(tr_of) + len(te_of)} lesiones")

    # ---- Partición por paciente ----
    if a.modo == "oficial":
        train, val = dividir(tr_of, 6)
        test = te_of.copy()
    else:
        pool = pd.concat([tr_of, te_of], ignore_index=True)
        resto, test = dividir(pool, 7)       # prueba ~ 1/7 del total
        train, val = dividir(resto, 6)       # validación ~ 1/6 del resto = 1/7 del total
    train["split"], val["split"], test["split"] = "train", "val", "test"

    # ---- Verificación de cero solapamiento (la que se muestra en vivo) ----
    p_tr, p_va, p_te = set(train.patient_id), set(val.patient_id), set(test.patient_id)
    solap = {"train&val": p_tr & p_va, "train&test": p_tr & p_te, "val&test": p_va & p_te}
    for k, v in solap.items():
        assert len(v) == 0, f"Fuga de pacientes entre {k}: {sorted(v)[:5]}"
    ids = pd.concat([train, val, test])["lesion_id"]
    assert ids.is_unique, "Una lesión aparece en más de una partición"
    total_entrada = len(tr_of) + len(te_of)
    assert len(ids) == total_entrada, "Se perdieron lesiones al particionar"

    # ---- Reporte ----
    lineas = [
        f"Modo: {a.modo} | semilla: {SEED} | StratifiedGroupKFold",
        resumen("train", train), resumen("val", val), resumen("test", test),
        "Pacientes solapados -> " + ", ".join(f"{k}: {len(v)}" for k, v in solap.items()),
    ]
    pool_all = pd.concat([tr_of, te_of])
    mixtos = pool_all.groupby("patient_id")["label"].nunique()
    lineas.append(f"Pacientes con lesiones de ambas clases: {(mixtos > 1).sum()}")
    for nombre, d in [("val", val), ("test", test)]:
        if d.label.sum() < MIN_MALIGNAS:
            lineas.append(f"ADVERTENCIA: {nombre} tiene solo {int(d.label.sum())} lesiones "
                          f"malignas; la sensibilidad será muy inestable (usar intervalos de confianza).")
    reporte = "\n".join(lineas)
    print(reporte)

    os.makedirs(a.out, exist_ok=True)
    for nombre, d in [("train", train), ("val", val), ("test", test)]:
        d.to_csv(os.path.join(a.out, f"{nombre}.csv"), index=False)
    with open(os.path.join(a.out, "reporte_particion.txt"), "w", encoding="utf-8") as f:
        f.write(reporte + "\n")
    print(f"\nGuardado en: {a.out}/ (train.csv, val.csv, test.csv, reporte_particion.txt)")


if __name__ == "__main__":
    main()
