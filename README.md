# Clasificación de lesiones mamográficas benignas y malignas mediante aprendizaje profundo

> **Prototipo académico; no apto para diagnóstico ni decisiones clínicas.**
> Proyecto de clase de Aprendizaje Computacional (Ingeniería de Sistemas).
> Este prototipo NO diagnostica cáncer. La clasificación de una lesión con
> diagnóstico patológico no equivale a diagnosticar a una paciente.

**Autor:** Kevin Martinez Martinez - Iván Gonzalez Ordosgoitia - Efren Suárez Negrete
**Repositorio:** https://github.com/SrEffry/Mamografias
**Bitácora:** ver [BITACORA.md](BITACORA.md)

---

## 1. Objetivo y alcance

Desarrollar un prototipo académico que clasifique lesiones mamográficas como
benignas o malignas a partir de imágenes con etiquetas de referencia, y que
permita visualizar el resultado en una interfaz Gradio.

- **Alcance mínimo:** clasificación binaria y evaluación rigurosa.
- **Opcionales:** Grad-CAM, localización de lesiones, comparación de dos
  arquitecturas.
- **Fuera de alcance:** segmentación, entrenamiento clínico, uso en decisiones médicas.

## 2. Comprensión del problema

- **Usuario:** estudiantes y docentes, en un contexto exclusivamente educativo.
- **Unidad de análisis:** la lesión (una fila por lesión, no por imagen,
  por mama ni por paciente).
- **Significado de las etiquetas:** provienen del diagnóstico patológico de
  la lesión (biopsia), no de un diagnóstico a la paciente.

### Mapeo de etiquetas

| Etiqueta original (CBIS-DDSM) | Etiqueta del proyecto |
|---|---|
| BENIGN | Benigna (0) |
| BENIGN_WITHOUT_CALLBACK | Benigna (0) |
| MALIGNANT | Maligna (1) |

### Hipótesis (escritas antes de experimentar)

**H1 (modelo).** Un modelo con transferencia de aprendizaje (ResNet18
preentrenada en ImageNet) obtendrá un ROC-AUC en validación al menos 0.05
mayor que la línea base (CNN pequeña entrenada desde cero). Razón: el
conjunto de lesiones es pequeño (cientos a pocos miles) y una red entrenada
desde cero tiende a sobreajustarse, mientras que las características visuales
generales de una red preentrenada se pueden reutilizar.

**H2 (sensibilidad y umbral).** Con el umbral por defecto de 0.5, la
sensibilidad para malignidad será menor que la especificidad, porque la clase
benigna suele ser mayoritaria y el modelo tiende a favorecerla. Al bajar el
umbral (por ejemplo a 0.3, elegido solo con el conjunto de validación), la
sensibilidad subirá y la especificidad bajará. Considero preferible ese
intercambio, porque un falso negativo (lesión maligna clasificada como
benigna) es más costoso que un falso positivo.

### Costo de los errores

- **Falso negativo:** una lesión maligna clasificada como benigna. En un
  contexto real retrasaría el diagnóstico y el tratamiento, por eso es el
  error más grave y el que se busca reducir.
- **Falso positivo:** una lesión benigna clasificada como maligna. Genera
  ansiedad, pruebas adicionales y posibles biopsias innecesarias, pero suele
  ser reversible.

## 3. Datos

- **Fuente:** CBIS-DDSM (The Cancer Imaging Archive, TCIA)
  https://www.cancerimagingarchive.net/collection/cbis-ddsm/
- **Versión y licencia:** [completar según la página de TCIA]
- **Origen de las etiquetas:** diagnóstico patológico por lesión, incluido
  en los CSV de metadatos del dataset.
- **Subconjunto elegido:** [masas / calcificaciones], porque [razón].
- **Pacientes / imágenes / lesiones:** [completar tras el EDA]
- **Distribución por clase:** [benigna: N, maligna: N]
- **Vistas:** [CC: N, MLO: N]
- **Exclusiones:** [casos descartados y motivo]

### Herramientas

- **Weka 3.8.x** (versión: [___], se ve en Help → About): análisis exploratorio
  y limpieza de los CSV de metadatos.
- **Python [3.x]:** lectura de DICOM, partición por paciente, preprocesamiento,
  modelado, evaluación e interfaz Gradio.
- **Librerías:** ver `requirements.txt`.
- **Entorno de ejecución:** [Colab / Kaggle / equipo local, GPU: ___].

### Partición de datos

Entrenamiento, validación y prueba se separan **por paciente** (con
`GroupShuffleSplit` sobre `patient_id`), para evitar fuga entre imágenes de
una misma paciente. Los CSV resultantes se guardan para reproducibilidad.
El conjunto de prueba no se usa para elegir hiperparámetros ni umbral.

| Partición | Pacientes | Lesiones | Benignas | Malignas |
|---|---|---|---|---|
| Entrenamiento | [ ] | [ ] | [ ] | [ ] |
| Validación | [ ] | [ ] | [ ] | [ ] |
| Prueba | [ ] | [ ] | [ ] | [ ] |

### Preprocesamiento

[Completar: lectura DICOM, imagen completa o recorte (ROI), normalización,
redimensionamiento a 224x224, conversión a 3 canales. Aumentos moderados
(flip, rotación leve) solo en entrenamiento.]

## 4. Modelado

| Modelo | Descripción | Semilla | Épocas | Batch | Optimizador | LR | Tiempo |
|---|---|---|---|---|---|---|---|
| Línea base | [CNN pequeña] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] |
| Transferencia | ResNet18 preentrenada | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] |

**Experimento controlado:** [una sola decisión modificada, por ejemplo con
vs. sin aumentos de datos]

**Referencia tabular (opcional):** [si se entrena un clasificador en Weka
sobre metadatos, indicarlo aquí como referencia adicional. No se usa la
columna `assessment` (BI-RADS) como predictor, porque contiene la sospecha
radiológica y filtraría la respuesta.]

## 5. Evaluación

[Completar con resultados en validación y, al final, en prueba.]

| Métrica | Validación | Prueba |
|---|---|---|
| Sensibilidad (malignidad) | [ ] | [ ] |
| Especificidad | [ ] | [ ] |
| Precisión | [ ] | [ ] |
| F1 | [ ] | [ ] |
| ROC-AUC | [ ] | [ ] |

- **Umbral elegido (con validación):** [ ]
- **Matriz de confusión:** [ver results/]
- **Análisis de falsos negativos y positivos:** [ver results/ y el informe]

La salida del modelo es una **puntuación**, no una probabilidad clínica
calibrada.

## 6. Interfaz (Gradio)

[Completar al terminar: cómo ejecutarla, formatos admitidos (PNG, JPG),
manejo de imágenes inválidas.]
La interfaz muestra de forma visible: *«Prototipo académico; no apto para
diagnóstico ni decisiones clínicas»*.

## 7. Limitaciones

- Prototipo académico: no diagnostica cáncer ni sirve para decisiones médicas.
- La etiqueta es el diagnóstico patológico de una lesión, no el de una paciente.
- Dataset pequeño y de una sola fuente: riesgo de sobreajuste y de sesgo de selección.
- La salida del modelo es una puntuación, no una probabilidad clínica calibrada.
- [Agregar más al avanzar: generalización, calidad de las imágenes, sesgos del dataset.]

## 8. Estructura del repositorio

```
Mamografias/
├── README.md
├── BITACORA.md
├── requirements.txt
├── .gitignore
├── data/          (ignorada por Git: DICOM y datos pesados)
├── weka/
│   ├── arff/      (archivos preparados para Weka)
│   └── capturas/  (pantallazos del EDA)
├── notebooks/     (EDA, experimentos, demo)
├── src/           (dataset, entrenamiento, evaluación)
├── app/           (interfaz Gradio)
├── results/       (métricas, matrices, figuras)
└── informe/
```

## 9. Cómo reproducir

1. Clonar el repositorio:
   `git clone https://github.com/SrEffry/Mamografias.git`
2. Crear el entorno e instalar dependencias:
   `python -m venv venv`, activarlo, y `pip install -r requirements.txt`
3. Descargar el subconjunto de CBIS-DDSM desde TCIA con NBIA Data Retriever
   y colocarlo en `data/`. [Indicar el manifiesto o los IDs del subconjunto.]
4. [Ejecutar la partición por paciente: `python src/...`]
5. [Entrenar: `python src/...`]
6. [Evaluar: `python src/...`]
7. [Lanzar la interfaz: `python app/app.py`]
8. Semilla utilizada: [42]

## 10. Referencias

- Lee, R. S. et al. *A curated mammography data set for use in computer-aided
  detection and diagnosis research* (CBIS-DDSM). Scientific Data, 2017.
- The Cancer Imaging Archive (TCIA): https://www.cancerimagingarchive.net/