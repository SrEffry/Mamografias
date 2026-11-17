"""
modelo_utils.py
Funciones compartidas por los notebooks 04 (preprocesamiento), 05 (entrenamiento)
y demo_dia7: preprocesar el recorte DICOM, Dataset de PyTorch, modelos, entrenamiento
y métricas.

Prototipo académico; no apto para diagnóstico ni decisiones clínicas.
La salida del modelo es una PUNTUACIÓN entre 0 y 1, no una probabilidad clínica calibrada.

Decisiones (ver BITACORA.md):
  - Entrada: recorte ROI del DICOM, normalizado min-max por imagen, llevado a cuadrado
    con relleno (AJUSTE="pad") o estirado (AJUSTE="resize"), 224x224, PNG de 8 bits.
  - Aumentos SOLO en entrenamiento: volteo horizontal y rotación de +-10 grados.
    Validación y prueba sin aumentos.
  - Ambos modelos usan la misma entrada (3 canales repetidos y normalización de ImageNet),
    así la diferencia entre ellos es la arquitectura y el preentrenamiento.
"""
import os
import random
import time

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from PIL import Image
from sklearn.metrics import confusion_matrix, roc_auc_score
from torch.utils.data import DataLoader, Dataset
from torchvision import models, transforms

TAM = 224
MEDIA_IMAGENET = [0.485, 0.456, 0.406]
STD_IMAGENET = [0.229, 0.224, 0.225]


# --------------------------------------------------------------------------- #
# Reproducibilidad
# --------------------------------------------------------------------------- #
def fijar_semilla(semilla):
    random.seed(semilla)
    np.random.seed(semilla)
    torch.manual_seed(semilla)
    torch.cuda.manual_seed_all(semilla)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False


def _semilla_worker(worker_id):
    s = torch.initial_seed() % 2**32
    np.random.seed(s)
    random.seed(s)


# --------------------------------------------------------------------------- #
# Preprocesamiento del DICOM (se hace UNA vez y se guarda como PNG)
# --------------------------------------------------------------------------- #
def leer_recorte(ruta_dcm):
    """Lee el recorte DICOM y devuelve un arreglo float32 en [0, 1].
    Sin force=True: un archivo dañado debe fallar y no pasar sin avisar."""
    import pydicom
    ds = pydicom.dcmread(ruta_dcm)
    x = ds.pixel_array.astype(np.float32)
    if ds.get("PhotometricInterpretation", "MONOCHROME2") == "MONOCHROME1":
        x = x.max() - x                    # en MONOCHROME1 el blanco es 0: se invierte
    mn, mx = x.min(), x.max()
    if mx <= mn:
        raise ValueError(f"Imagen constante (min = max = {mn}): {ruta_dcm}")
    return (x - mn) / (mx - mn)


def a_cuadrado(x, ajuste="pad"):
    """'pad': rellena con ceros el lado corto para no deformar la forma de la lesión.
    'resize': estira directamente (deforma si el recorte no es cuadrado)."""
    if ajuste == "resize":
        return x
    h, w = x.shape
    lado = max(h, w)
    out = np.zeros((lado, lado), dtype=x.dtype)
    y0, x0 = (lado - h) // 2, (lado - w) // 2
    out[y0:y0 + h, x0:x0 + w] = x
    return out


def preprocesar(ruta_dcm, ajuste="pad", tam=TAM):
    """DICOM -> arreglo uint8 de tam x tam (escala de grises)."""
    import cv2
    x = a_cuadrado(leer_recorte(ruta_dcm), ajuste)
    x = cv2.resize(x, (tam, tam), interpolation=cv2.INTER_AREA)
    return np.clip(np.round(x * 255), 0, 255).astype(np.uint8)


# --------------------------------------------------------------------------- #
# Dataset y transformaciones
# --------------------------------------------------------------------------- #
def transformaciones(entrenamiento, flip=True, rotacion=10):
    """Aumentos moderados solo si entrenamiento=True."""
    t = []
    if entrenamiento:
        if flip:
            t.append(transforms.RandomHorizontalFlip(p=0.5))
        if rotacion:
            t.append(transforms.RandomRotation(rotacion))
    t += [transforms.ToTensor(), transforms.Normalize(MEDIA_IMAGENET, STD_IMAGENET)]
    return transforms.Compose(t)


class LesionesPNG(Dataset):
    """Una fila por lesión: lee {dir_png}/{lesion_id}.png y devuelve (imagen, etiqueta, índice)."""

    def __init__(self, df, dir_png, transform):
        self.df = df.reset_index(drop=True)
        self.dir_png = dir_png
        self.transform = transform

    def __len__(self):
        return len(self.df)

    def __getitem__(self, i):
        fila = self.df.iloc[i]
        img = Image.open(os.path.join(self.dir_png, f"{fila.lesion_id}.png")).convert("RGB")
        return self.transform(img), torch.tensor(float(fila.label)), i


def crear_loader(df, dir_png, entrenamiento, batch_size, semilla, flip=True, rotacion=10,
                 num_workers=None):
    if num_workers is None:                # en Windows los procesos auxiliares fallan fuera de __main__
        num_workers = 0 if os.name == "nt" else 2
    ds = LesionesPNG(df, dir_png, transformaciones(entrenamiento, flip, rotacion))
    g = torch.Generator()
    g.manual_seed(semilla)
    return DataLoader(ds, batch_size=batch_size, shuffle=entrenamiento,
                      num_workers=num_workers, worker_init_fn=_semilla_worker, generator=g)


# --------------------------------------------------------------------------- #
# Modelos
# --------------------------------------------------------------------------- #
class CNNBase(nn.Module):
    """Línea base: 4 bloques Conv-BN-ReLU-MaxPool, pooling global, dropout y 1 logit."""

    def __init__(self, p_dropout=0.5):
        super().__init__()
        capas, c_in = [], 3
        for c_out in [16, 32, 64, 128]:
            capas += [nn.Conv2d(c_in, c_out, 3, padding=1), nn.BatchNorm2d(c_out),
                      nn.ReLU(inplace=True), nn.MaxPool2d(2)]
            c_in = c_out
        self.features = nn.Sequential(*capas)
        self.cabeza = nn.Sequential(nn.AdaptiveAvgPool2d(1), nn.Flatten(),
                                    nn.Dropout(p_dropout), nn.Linear(128, 1))

    def forward(self, x):
        return self.cabeza(self.features(x)).squeeze(1)


class ResNet18Bin(nn.Module):
    """ResNet18 (preentrenada en ImageNet) con la capa final cambiada a 1 salida."""

    def __init__(self, preentrenada=True):
        super().__init__()
        pesos = models.ResNet18_Weights.IMAGENET1K_V1 if preentrenada else None
        self.red = models.resnet18(weights=pesos)
        self.red.fc = nn.Linear(self.red.fc.in_features, 1)

    def forward(self, x):
        return self.red(x).squeeze(1)


def crear_modelo(nombre):
    if nombre == "baseline":
        return CNNBase()
    if nombre == "resnet18":
        return ResNet18Bin(preentrenada=True)
    raise ValueError(nombre)


def contar_parametros(modelo):
    return sum(p.numel() for p in modelo.parameters() if p.requires_grad)


# --------------------------------------------------------------------------- #
# Entrenamiento y predicción
# --------------------------------------------------------------------------- #
@torch.no_grad()
def predecir(modelo, loader, dispositivo):
    """Devuelve DataFrame (copia del df del loader) con la columna 'score' y la pérdida media."""
    modelo.eval()
    crit = nn.BCEWithLogitsLoss(reduction="sum")
    scores, idxs, perdida = [], [], 0.0
    for x, y, i in loader:
        x, y = x.to(dispositivo), y.to(dispositivo)
        logit = modelo(x)
        perdida += crit(logit, y).item()
        scores.append(torch.sigmoid(logit).cpu().numpy())
        idxs.append(i.numpy())
    out = loader.dataset.df.iloc[np.concatenate(idxs)].copy()
    out["score"] = np.concatenate(scores)
    return out, perdida / len(out)


def entrenar(modelo, dl_train, dl_train_eval, dl_val, epocas, lr, dispositivo, ruta_ckpt,
             weight_decay=0.0):
    """Entrena con Adam y BCEWithLogitsLoss. Guarda el checkpoint de la época con mayor
    ROC-AUC en VALIDACIÓN (la prueba no se usa). Devuelve (historial, mejor_epoca, segundos)."""
    modelo.to(dispositivo)
    opt = torch.optim.Adam(modelo.parameters(), lr=lr, weight_decay=weight_decay)
    crit = nn.BCEWithLogitsLoss()
    hist, mejor_auc, mejor_ep = [], -1.0, 0
    t0 = time.time()
    for ep in range(1, epocas + 1):
        modelo.train()
        for x, y, _ in dl_train:
            x, y = x.to(dispositivo), y.to(dispositivo)
            opt.zero_grad()
            perdida = crit(modelo(x), y)
            perdida.backward()
            opt.step()
        p_tr, loss_tr = predecir(modelo, dl_train_eval, dispositivo)   # train sin aumentos
        p_va, loss_va = predecir(modelo, dl_val, dispositivo)
        auc_tr = roc_auc_score(p_tr.label, p_tr.score)
        auc_va = roc_auc_score(p_va.label, p_va.score)
        hist.append(dict(epoca=ep, loss_train=loss_tr, loss_val=loss_va,
                         auc_train=auc_tr, auc_val=auc_va))
        marca = ""
        if auc_va > mejor_auc:
            mejor_auc, mejor_ep = auc_va, ep
            torch.save(modelo.state_dict(), ruta_ckpt)
            marca = "  <- mejor"
        print(f"época {ep:>3} | loss train {loss_tr:.3f} val {loss_va:.3f} | "
              f"AUC train {auc_tr:.3f} val {auc_va:.3f}{marca}")
    return pd.DataFrame(hist), mejor_ep, time.time() - t0


# --------------------------------------------------------------------------- #
# Métricas
# --------------------------------------------------------------------------- #
def wilson(k, n, z=1.96):
    """Intervalo de confianza de Wilson (95 %) para una proporción k/n."""
    if n == 0:
        return (np.nan, np.nan)
    p = k / n
    den = 1 + z**2 / n
    centro = (p + z**2 / (2 * n)) / den
    margen = z * np.sqrt(p * (1 - p) / n + z**2 / (4 * n**2)) / den
    return (centro - margen, centro + margen)


def metricas(y, score, umbral=0.5):
    y = np.asarray(y).astype(int)
    pred = (np.asarray(score) >= umbral).astype(int)
    tn, fp, fn, tp = confusion_matrix(y, pred, labels=[0, 1]).ravel()
    sens = tp / (tp + fn) if tp + fn else np.nan
    esp = tn / (tn + fp) if tn + fp else np.nan
    prec = tp / (tp + fp) if tp + fp else np.nan
    f1 = 2 * tp / (2 * tp + fp + fn) if tp + fp + fn else np.nan
    s_lo, s_hi = wilson(tp, tp + fn)
    e_lo, e_hi = wilson(tn, tn + fp)
    return dict(umbral=umbral, TP=tp, FN=fn, TN=tn, FP=fp,
                sensibilidad=sens, sens_ic95=f"{s_lo:.2f}-{s_hi:.2f}",
                especificidad=esp, esp_ic95=f"{e_lo:.2f}-{e_hi:.2f}",
                precision=prec, f1=f1)


def auc_ic_bootstrap(pred, n_boot=1000, semilla=0):
    """ROC-AUC con IC 95 % por bootstrap remuestreando PACIENTES (no lesiones),
    porque las lesiones de una misma paciente no son independientes."""
    rng = np.random.default_rng(semilla)
    pacientes = pred.patient_id.unique()
    grupos = {p: g for p, g in pred.groupby("patient_id")}
    aucs = []
    for _ in range(n_boot):
        m = pd.concat([grupos[p] for p in rng.choice(pacientes, len(pacientes), replace=True)])
        if m.label.nunique() == 2:
            aucs.append(roc_auc_score(m.label, m.score))
    auc = roc_auc_score(pred.label, pred.score)
    return auc, np.percentile(aucs, 2.5), np.percentile(aucs, 97.5)


def tabla_umbrales(pred, umbrales=(0.5, 0.4, 0.3, 0.2)):
    return pd.DataFrame([metricas(pred.label, pred.score, u) for u in umbrales])
