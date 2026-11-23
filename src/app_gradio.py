"""
app_gradio.py
Interfaz Gradio del prototipo: recibe el RECORTE de una lesión, aplica el mismo
preprocesamiento del entrenamiento y muestra la clase predicha y la puntuación del modelo.

Prototipo académico; no apto para diagnóstico ni decisiones clínicas.

Formatos admitidos: PNG, JPG/JPEG o DICOM (.dcm) de un recorte de lesión (ROI) en escala
de grises. No admite mamografías completas ni máscaras: el modelo se entrenó con recortes.
"""
import os

import numpy as np
import torch
from PIL import Image

import modelo_utils as mu

AVISO = "Prototipo académico; no apto para diagnóstico ni decisiones clínicas."
EXT_IMAGEN = {".png", ".jpg", ".jpeg"}
EXT_DICOM = {".dcm", ".dicom"}
LADO_MIN = 32      # por debajo no queda información útil de la lesión
LADO_MAX = 2000    # los recortes del EDA miden como máximo 839 px; las mamografías
                   # completas y las máscaras miden más de 3000 px por lado


class EntradaInvalida(Exception):
    """Error con un mensaje pensado para mostrarse al usuario."""


def leer_entrada(ruta):
    """Lee el archivo subido y devuelve un arreglo float32 2D en [0, 1].
    Lanza EntradaInvalida con un mensaje claro si el archivo no sirve."""
    ext = os.path.splitext(str(ruta))[1].lower()
    if ext in EXT_DICOM:
        try:
            x = mu.leer_recorte(ruta)               # sin force=True; normaliza min-max
        except ValueError as e:                     # imagen constante
            raise EntradaInvalida(f"La imagen es constante (sin contenido): {e}") from None
        except Exception as e:
            raise EntradaInvalida(f"No se pudo leer el archivo como DICOM ({type(e).__name__}).") from None
    elif ext in EXT_IMAGEN:
        try:
            img = Image.open(ruta)
            img.load()
        except Exception:
            raise EntradaInvalida("El archivo no es una imagen PNG o JPG válida.") from None
        x = np.asarray(img.convert("L"), dtype=np.float32)
        if x.max() <= x.min():
            raise EntradaInvalida("La imagen es constante (un solo color): no hay lesión que clasificar.")
        # Un PNG/JPG ya es una imagen de 8 bits: se usa tal cual (/255), sin volver a estirar el
        # contraste. Así un PNG del notebook 04 llega al modelo idéntico a como se entrenó.
        # Solo el DICOM (16 bits) se normaliza min-max, igual que en el notebook 04.
        x = x / 255.0
    else:
        raise EntradaInvalida(f"Formato no admitido ({ext or 'sin extensión'}). "
                              "Use PNG, JPG o DICOM (.dcm) de un recorte de lesión.")

    if x.ndim != 2:
        raise EntradaInvalida("Se esperaba una imagen en escala de grises de un solo cuadro.")
    h, w = x.shape
    if min(h, w) < LADO_MIN:
        raise EntradaInvalida(f"La imagen es demasiado pequeña ({h}x{w} px; mínimo {LADO_MIN} px por lado).")
    if max(h, w) > LADO_MAX:
        raise EntradaInvalida(f"La imagen mide {h}x{w} px: parece una mamografía completa o una máscara. "
                              "El prototipo solo clasifica recortes de lesión.")
    if len(np.unique(x)) <= 2:
        raise EntradaInvalida("La imagen solo tiene dos valores: parece una máscara binaria, no un recorte.")
    return x


def crear_predictor(ruta_ckpt, dispositivo="cpu"):
    """Carga ResNet18 desde el checkpoint y devuelve una función ruta -> (imagen 224, puntuación)."""
    modelo = mu.crear_modelo("resnet18")
    modelo.load_state_dict(torch.load(ruta_ckpt, map_location=dispositivo))
    modelo.to(dispositivo).eval()
    t = mu.transformaciones(entrenamiento=False)    # sin aumentos, como validación y prueba

    @torch.no_grad()
    def predecir(ruta):
        x224 = mu.a_entrada(leer_entrada(ruta))     # mismo preprocesamiento del notebook 04
        entrada = t(Image.fromarray(x224).convert("RGB")).unsqueeze(0).to(dispositivo)
        return x224, float(torch.sigmoid(modelo(entrada)).item())

    return predecir


def imagen_html(x224):
    """Incrusta la imagen 224x224 como PNG en base64. Así no depende de que Gradio sirva
    archivos aparte, que fallaba detrás del proxy de Colab (se veía una imagen rota)."""
    import base64
    import io
    buf = io.BytesIO()
    Image.fromarray(x224).save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode("ascii")
    return (f'<img src="data:image/png;base64,{b64}" width="224" height="224" '
            f'style="image-rendering:pixelated" alt="Imagen preprocesada 224x224">')


def texto_resultado(score, umbral):
    clase = "MALIGNA" if score >= umbral else "BENIGNA"
    return (f"### Clase predicha: lesión {clase}\n\n"
            f"- Puntuación del modelo: **{score:.3f}**\n"
            f"- Umbral de decisión: **{umbral:.2f}** (elegido con el conjunto de validación)\n"
            f"- Si la puntuación es mayor o igual al umbral, se predice maligna.\n\n"
            f"La puntuación **no es una probabilidad clínica calibrada**.\n\n**{AVISO}**")


def crear_app(ruta_ckpt, umbral, dispositivo="cpu", ejemplos=None):
    import gradio as gr
    predecir = crear_predictor(ruta_ckpt, dispositivo)

    def responder(archivo):
        if archivo is None:
            return None, "Sube un archivo para clasificar."
        ruta = archivo if isinstance(archivo, str) else getattr(archivo, "name", archivo)
        try:
            x224, score = predecir(ruta)
        except EntradaInvalida as e:
            return None, f"### Entrada no válida\n\n{e}"
        return imagen_html(x224), texto_resultado(score, umbral)

    with gr.Blocks(title="Clasificación de lesiones mamográficas") as app:
        gr.Markdown(f"# Clasificación de lesiones mamográficas (benigna / maligna)\n\n"
                    f"## ⚠️ {AVISO}")
        gr.Markdown("**Formatos admitidos:** PNG, JPG o DICOM (.dcm) del **recorte de una lesión** "
                    "(región de interés) en escala de grises. No se admiten mamografías completas, "
                    "máscaras ni imágenes vacías. Un DICOM se normaliza min-max; un PNG o JPG se usa con "
                    "sus valores de 8 bits. Después se rellena a cuadrado y se lleva a 224x224, igual "
                    "que en el entrenamiento.")
        with gr.Row():
            entrada = gr.File(label="Recorte de la lesión", file_types=sorted(EXT_IMAGEN | EXT_DICOM))
            with gr.Column():
                gr.Markdown("**Imagen que ve el modelo (224x224)**")
                vista = gr.HTML()
        boton = gr.Button("Clasificar", variant="primary")
        salida = gr.Markdown()
        boton.click(responder, inputs=entrada, outputs=[vista, salida])
        if ejemplos:
            gr.Examples(ejemplos, inputs=entrada)
        gr.Markdown(f"---\n**{AVISO}** Modelo: ResNet18 preentrenada en ImageNet y ajustada con "
                    "CBIS-DDSM (masas). Proyecto de clase de Aprendizaje Computacional.")
    app.responder = responder        # para probar la función sin abrir el navegador
    return app
