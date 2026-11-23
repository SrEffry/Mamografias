# Clasificación de lesiones mamográficas benignas y malignas mediante aprendizaje profundo

> **Prototipo académico; no apto para diagnóstico ni decisiones clínicas.**
> Proyecto de clase de Aprendizaje Computacional (Ingeniería de Sistemas).
> Este prototipo NO diagnostica cáncer. La clasificación de una lesión con
> diagnóstico patológico no equivale a diagnosticar a una paciente.

**Autores:** Kevin Martínez Martínez, Iván González Ordosgoitia y Efren Suárez Negrete
**Repositorio:** https://github.com/SrEffry/Mamografias
**Bitácora:** [BITACORA.md](BITACORA.md)

## Estado del proyecto

| Etapa | Estado |
|---|---|
| Comprensión del problema, etiquetas e hipótesis | Hecho |
| Datos: descarga, indexación, EDA tabular y partición por paciente | Hecho |
| EDA de imágenes y preprocesamiento | Hecho |
| Línea base y transferencia de aprendizaje | Hecho |
| Experimento controlado, errores y umbral | Hecho |
| Evaluación final en prueba (una sola vez) | Hecho |
| Interfaz Gradio | Hecho |
| Informe | Pendiente |

---

## 1. Objetivo y alcance

Desarrollar un prototipo académico que clasifique lesiones mamográficas como
benignas o malignas a partir de imágenes con etiquetas de referencia, y que
permita visualizar el resultado en una interfaz Gradio.

- **Alcance mínimo:** clasificación binaria y evaluación rigurosa.
- **Opcionales:** Grad-CAM, localización de lesiones, comparación de dos arquitecturas.
- **Fuera de alcance:** segmentación, entrenamiento clínico, uso en decisiones médicas.

## 2. Comprensión del problema

- **Usuario:** estudiantes y docentes, en un contexto exclusivamente educativo.
- **Unidad de análisis:** la lesión (una fila por lesión, no por imagen, mama ni paciente).
- **Entrada del modelo:** el **recorte de la lesión (ROI)** que trae el dataset, no la
  mamografía completa. Motivo: en la mamografía completa, la lesión ocupa una fracción
  muy pequeña de la imagen (la máscara observada mide 4556x2585 px frente a un recorte
  de 434x387 px) y la imagen incluye texto grabado (por ejemplo "LCC" o "LMLO") que un
  modelo podría aprender en lugar de la lesión. Consecuencia: el prototipo clasifica
  recortes de lesiones, y la interfaz recibirá un recorte.
- **Significado de las etiquetas:** provienen del diagnóstico patológico de la lesión
  (biopsia), no de un diagnóstico a la paciente.

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

### Fuente y obtención

- **Dataset:** CBIS-DDSM, tarea sobre **masas** (se descartaron las calcificaciones:
  son lesiones muy pequeñas que se pierden al reducir a 224x224).
- **Metadatos (CSV):** `mass_case_description_train_set.csv` y
  `mass_case_description_test_set.csv` [de TCIA: confirmar]
  https://www.cancerimagingarchive.net/collection/cbis-ddsm/
- **Imágenes DICOM:** descargadas con manifiestos del NCI Imaging Data Commons (IDC),
  en varias tandas. [Confirmar el procedimiento exacto.]
- **Versión y licencia:** [completar según la página de TCIA/IDC]
- **Origen de las etiquetas:** diagnóstico patológico por lesión, incluido en los CSV.

Los CSV completos de masas tienen:

| Archivo | Lesiones | Pacientes | MALIGNANT | BENIGN | BENIGN_WITHOUT_CALLBACK |
|---|---|---|---|---|---|
| mass train | 1318 | 691 | 637 | 577 | 104 |
| mass test | 378 | 201 | 147 | 194 | 37 |

Entre ambos hay 784 lesiones en vista CC y 912 en MLO. Los pacientes del train
oficial y del test oficial no se solapan (comprobado en código).

### Subconjunto utilizado

Por limitaciones de espacio y tiempo no se descargó el dataset completo.
**Criterio de selección del subconjunto:** [describir cómo se eligieron los
pacientes o lesiones descargados; si no fue aleatorio, decirlo: es una posible
fuente de sesgo de selección].

Una lesión se considera **disponible** solo si se tiene su **serie ROI completa**
(recorte y máscara). Tener únicamente la mamografía completa no cuenta, porque el
modelo usa el recorte.

| | Lesiones | Pacientes | Malignas | Benignas |
|---|---|---|---|---|
| Del train oficial | 108 | 54 | 52 | 56 |
| Del test oficial | 103 | 51 | 33 | 70 |
| **Total** | **211** | **105** | **85** | **126** |

Vistas del subconjunto: 104 CC (61 benignas y 43 malignas) y 107 MLO (65 benignas y 42 malignas).

### Calidad de los datos y exclusiones

- Total de archivos .dcm descargados: 623. Seis eran archivos **vacíos** (0 bytes,
  sin cabecera DICM), probablemente por una descarga o copia interrumpida: se excluyeron.
  Quedaron 617 archivos DICOM válidos, en 417 series.
- Dos lesiones tenían un solo archivo ROI y se excluyeron:
  P_00408_RIGHT_MLO_1 y P_00413_LEFT_MLO_1.
- Los archivos válidos tienen todos cabecera DICOM estándar (0 de 617 sin ella), así
  que se lee con `pydicom` sin forzar.
- Recorte y máscara se distinguen **por su área** (la máscara tiene el tamaño de la
  mamografía completa), no por el nombre del archivo, porque en el CSV el orden
  `000000.dcm` / `000001.dcm` no es consistente.

### Hallazgos del análisis exploratorio

- **Hay varias lesiones por paciente** (hasta 14) y varias lesiones comparten la misma
  mamografía (1592 mamografías distintas para 1696 lesiones). Por eso la partición
  debe ser por paciente.
- **`assessment` (BI-RADS) casi contiene la respuesta:** en el CSV completo,
  363 de 374 lesiones con assessment 5 son malignas. No se usa como predictor.
- **Valores faltantes:** `mass shape` (4) y `mass margins` (60). No se usan
  en el modelo de imágenes, por lo que no se excluyeron lesiones por ello.
- **`subtlety`** tiene 2 filas con valor 0 (la escala esperada es de 1 a 5);
  no se usa esa columna.
- **Sin filas duplicadas** en los CSV.
- **Resolución de los recortes:** el alto mediano es 316,5 px en benignas y 341 px en malignas,
  y el ancho mediano 325 y 346 px. Van de 132 a 839 px de alto y de 156 a 758 px de ancho. 38
  recortes tienen algún lado menor de 224 px y se agrandan al redimensionar. La relación ancho/alto
  tiene mediana cercana a 1 (1,04 en benignas y 1,03 en malignas), pero 32 de 211 quedan fuera de
  0,8-1,25 (mínimo 0,51 y máximo 1,54). Ver `results/eda_imagenes_resolucion.png`.
- **Calidad:** los 211 recortes son MONOCHROME2 de 16 bits (`uint16`) y ninguno es constante.
- **Duplicados de imagen (hash MD5 de los píxeles):** ninguno.
- **Integridad del cruce:** el `PatientID` del encabezado DICOM coincide con el `lesion_id` en
  los 211 recortes, y la `SeriesDescription` de todos es `cropped images`. Con eso se comprueba
  que la regla del área eligió el recorte y no la máscara.
- **Análisis exploratorio con Weka** (capturas en `weka/capturas/`) y con Python
  (`notebooks/`).

### Partición de datos

Se juntaron las lesiones disponibles de los conjuntos oficiales de entrenamiento y
prueba (211 lesiones) y se repartieron **por paciente** con `StratifiedGroupKFold`
sobre `patient_id` (semilla 42), estratificando por etiqueta. Se aparta de la partición
oficial porque el subconjunto descargado del train oficial era demasiado pequeño para
validar con rigor. Se pierde la comparabilidad con la partición oficial.

| Partición | Lesiones | Pacientes | Malignas | Benignas | % malignas |
|---|---|---|---|---|---|
| Entrenamiento | 146 | 74 | 64 | 82 | 43,8 % |
| Validación | 37 | 16 | 10 | 27 | 27,0 % |
| Prueba | 28 | 15 | 11 | 17 | 39,3 % |

- **Cero pacientes solapados** entre las tres particiones (verificado en código con `assert`).
- **La validación tiene una prevalencia menor** (27 %) que entrenamiento y prueba. Se evaluaron
  200 semillas con un criterio fijado antes de entrenar y se encontraron particiones más
  equilibradas, pero se decidió mantener la semilla 42 por simplicidad (ver bitácora).
- El conjunto de prueba **no se usa** para elegir hiperparámetros ni umbral.
- Script: `src/01_particion.py` (modo `propio`). Resultados en `particiones/`.

### Preprocesamiento

Se hace una sola vez (`notebooks/04_preprocesamiento.ipynb`, función `preprocesar` de
`src/modelo_utils.py`) y se guarda como PNG en Drive:

1. Lectura del recorte DICOM con `pydicom`, sin `force=True`. Todos los recortes son MONOCHROME2;
   el código invertiría uno MONOCHROME1, pero no hay ninguno.
2. Normalización min-max por imagen a [0, 1], porque el rango de intensidades cambia entre
   imágenes.
3. Relleno a cuadrado con ceros y redimensionado a 224x224 con `INTER_AREA`. La mayoría de los
   recortes son casi cuadrados, pero 32 de 211 tienen una relación de aspecto fuera de 0,8-1,25
   y, si se estiraran, la forma de esas masas se deformaría. En el caso extremo, con relación
   0,51, un eje se estiraría casi al doble.
4. Guardado en PNG de 8 bits. Se pierde precisión frente a los bits originales del DICOM.

Al cargar cada imagen se repite en 3 canales y se normaliza con la media y la desviación de
ImageNet, igual para los dos modelos. Los aumentos son moderados y **solo en entrenamiento**:
volteo horizontal (p = 0,5) y rotación aleatoria de ±10°. Validación y prueba no se alteran.

### Herramientas

- **Weka [versión: ___]** (Help → About): análisis exploratorio de los CSV de metadatos.
- **Python en Google Colab [versión: ___]**, con los archivos en Google Drive:
  lectura de DICOM, partición, preprocesamiento, modelado, evaluación y Gradio.
- **Librerías:** ver `requirements.txt`. **GPU de Colab:** Tesla T4 (torch 2.14.1+cu130)

## 4. Modelado

| Modelo | Descripción | Semilla | Épocas | Batch | Optimizador | LR | Tiempo |
|---|---|---|---|---|---|---|---|
| Línea base | CNN de 4 bloques Conv-BN-ReLU-MaxPool, dropout 0,5, 1 salida | 42 | 30 (mejor: 3) | 16 | Adam | 1e-3 | 73,9 s |
| Transferencia | ResNet18 preentrenada en ImageNet, capa final de 1 salida | 42 | 20 (mejor: 9) | 16 | Adam | 1e-4 | 36,0 s |

Pérdida `BCEWithLogitsLoss` sin `pos_weight`. En ambos se guarda la época con mayor ROC-AUC de
validación. Registro completo en `results/registro_experimentos.csv`.

### Experimento controlado: con y sin aumentos de datos

`notebooks/06_experimento.ipynb`. Se cambió **una sola decisión**, los aumentos de
entrenamiento (volteo horizontal y rotación de ±10° frente a ninguno), y se dejó fijo todo lo
demás: ResNet18, lr 1e-4, 20 épocas, batch 16, la partición de la semilla 42 y el
preprocesamiento. Cada condición se entrenó con 3 semillas de entrenamiento (42, 7 y 123) para
ver cuánto varía el AUC solo por el azar del entrenamiento. La regla de decisión se fijó antes de
ejecutar: quitar los aumentos solo si subía el AUC medio de validación en al menos 0,02.

| Condición | AUC val. semilla 42 | Semilla 7 | Semilla 123 | Media | AUC train medio (mejor época) |
|---|---|---|---|---|---|
| Con aumentos | 0,819 | 0,848 | 0,796 | 0,821 | 0,998 |
| Sin aumentos | 0,881 | 0,844 | 0,852 | 0,859 | 1,000 |

- Sin aumentos la media fue 0,038 mayor, así que por la regla se eligió **sin aumentos**. El
  modelo final es el de la semilla 42 sin aumentos (mejor época 4, AUC de validación 0,881).
- Los rangos se solapan (con aumentos llega a 0,848 y sin aumentos baja a 0,844), y la
  variación entre semillas de una misma condición, de hasta 0,05, es parecida a la diferencia
  entre condiciones. Con 37 lesiones de validación no se puede afirmar que quitar los aumentos
  mejore el modelo; solo que no lo empeoró en esta validación.
- En las dos condiciones el AUC de entrenamiento llega a casi 1, así que los aumentos
  moderados no evitaron el sobreajuste. Sin aumentos llega a 1 algunas épocas antes.
- La corrida con aumentos y semilla 42 reprodujo exactamente las puntuaciones del notebook 05
  (diferencia máxima 0,0).
- Elegir el mejor de 6 modelos por su AUC de validación hace que 0,881 sea una estimación
  optimista; por eso la prueba se evalúa aparte.

## 5. Evaluación

### Entrenamiento preliminar (validación: 37 lesiones, 10 malignas; umbral 0,5)

| Métrica | Línea base | ResNet18 |
|---|---|---|
| ROC-AUC (IC 95 %, bootstrap por paciente) | 0,648 (0,47-0,82) | 0,819 (0,63-0,99) |
| Sensibilidad (IC 95 % Wilson) | 0,10 (0,02-0,40), 1 de 10 | 0,60 (0,31-0,83), 6 de 10 |
| Especificidad (IC 95 % Wilson) | 0,963 (0,82-0,99), 26 de 27 | 0,704 (0,52-0,84), 19 de 27 |
| Precisión | 0,500 | 0,429 |
| F1 | 0,167 | 0,500 |

- **Línea base:** su mejor AUC de validación fue 0,648 en la época 3, y después osciló entre 0,46
  y 0,65 sin mejorar. El AUC de entrenamiento tampoco pasó de 0,77, así que con esta
  configuración la CNN pequeña aprende poco. Con umbral 0,5 detecta 1 de 10 malignas.
- **ResNet18:** su mejor AUC de validación fue 0,819 en la época 9. Desde la época 8 el AUC de
  entrenamiento está por encima de 0,99, mientras la pérdida de validación sube de 0,54 en las
  épocas 9-10 a cerca de 1,0 al final. Es una señal de sobreajuste, y por eso se guarda la
  época 9 y no la última.
- **H1:** la diferencia de AUC es 0,171, mayor que el 0,05 de la hipótesis. Pero los intervalos se
  solapan (0,47-0,82 y 0,63-0,99), así que con 37 lesiones esta corrida no basta para afirmar
  que la diferencia es real.
- **H2:** con umbral 0,5, la sensibilidad es menor que la especificidad en los dos modelos. En
  ResNet18, al bajar el umbral a 0,2 la sensibilidad sube de 0,6 a 0,8 y la especificidad baja de
  0,704 a 0,630. Entre 0,5 y 0,4 no cambia nada.
- **Errores de ResNet18 (umbral 0,5):** hay 4 falsos negativos, de los cuales 2 son las vistas CC
  y MLO de la paciente P_00198, y 8 falsos positivos, que se concentran en las pacientes P_00429,
  P_00044 y P_00173 con 2 cada una. Los errores no son independientes entre sí.

### Selección del umbral (solo validación)

`notebooks/07_umbral_errores.ipynb`. Criterio fijado antes de ver la tabla: el umbral **más
alto** de la rejilla 0,05-0,95 con **sensibilidad de validación de al menos 0,80**, porque un
falso negativo es el error más costoso (H2) y, entre los umbrales que cumplen, el más alto deja
menos falsos positivos.

| Umbral | TP | FN | TN | FP | Sensibilidad | Especificidad |
|---|---|---|---|---|---|---|
| 0,25 | 9 | 1 | 20 | 7 | 0,90 | 0,741 |
| **0,30 (elegido)** | **8** | **2** | **23** | **4** | **0,80 (0,49-0,94)** | **0,852 (0,68-0,94)** |
| 0,35 | 6 | 4 | 25 | 2 | 0,60 | 0,926 |
| 0,50 | 3 | 7 | 26 | 1 | 0,30 | 0,963 |

- **Estabilidad:** al remuestrear pacientes de validación 1000 veces y aplicar la misma regla,
  el umbral elegido va de 0,15 a 0,40 (percentiles 2,5 y 97,5). El 0,3 depende de muy pocos casos.
- **Errores en validación con umbral 0,3:** 2 falsos negativos, que son las vistas CC y MLO de la
  misma paciente (P_00324), y 4 falsos positivos de 4 pacientes distintas. Por las variables
  del CSV no se puede sacar una conclusión: los grupos tienen de 0 a 3 errores.

### Evaluación final en prueba (28 lesiones, 15 pacientes, 11 malignas)

`notebooks/08_prueba_final.ipynb`, ejecutado **una sola vez** el 21/11/2026 con el modelo y el
umbral fijados antes (candado en `results/prueba_final/EVALUADA.txt`).

| Modelo y umbral | AUC (IC 95 %) | TP | FN | TN | FP | Sensibilidad (IC 95 %) | Especificidad (IC 95 %) | Precisión | F1 |
|---|---|---|---|---|---|---|---|---|---|
| **ResNet18 final, umbral 0,3** | **0,706 (0,44-0,97)** | 5 | 6 | 14 | 3 | **0,455 (0,21-0,72)** | **0,824 (0,59-0,94)** | 0,625 | 0,526 |
| ResNet18 final, umbral 0,5 | 0,706 (0,44-0,97) | 3 | 8 | 16 | 1 | 0,273 (0,10-0,57) | 0,941 (0,73-0,99) | 0,750 | 0,400 |
| Línea base, umbral 0,5 | 0,754 (0,53-0,92) | 0 | 11 | 17 | 0 | 0,000 (0,00-0,26) | 1,000 (0,82-1,00) | - | 0,000 |

- **Validación frente a prueba (mismo modelo y umbral):** el AUC baja de 0,881 a 0,706 y la
  sensibilidad de 0,80 a 0,455. La especificidad se mantiene parecida (0,852 y 0,824). La caída
  era esperable porque la época, la condición del experimento y el umbral se eligieron con
  validación.
- **H1 no se confirma.** En validación ResNet18 superó a la línea base por 0,17 de AUC, pero en
  prueba la línea base tuvo 0,754 y ResNet18 0,706. Los intervalos se solapan casi por completo,
  así que con 28 lesiones no se puede decir cuál es mejor.
- **H2 se cumple en la dirección esperada.** Con umbral 0,5 la sensibilidad (0,273) es menor que
  la especificidad (0,941), y al bajar a 0,3 la sensibilidad sube a 0,455 y la especificidad baja
  a 0,824. Pero la sensibilidad objetivo de 0,80 que se logró en validación no se alcanzó en prueba.
- **La línea base con umbral 0,5 clasifica las 28 lesiones como benignas.** Su AUC de 0,754
  indica que ordena razonablemente las lesiones, pero todas sus puntuaciones quedan por debajo de
  0,5. Por eso el AUC y la matriz de confusión cuentan cosas distintas.
- **Errores en prueba:** los 6 falsos negativos vienen de solo 3 pacientes (3 lesiones de P_00074,
  2 de P_00406 y 1 de P_00347), con puntuaciones de 0,04 a 0,22. Los 3 falsos positivos son de 3
  pacientes distintas. Los errores no son independientes entre sí.

Figuras: `results/prueba_final/matriz_y_roc_prueba.png` y `results/prueba_final/errores_prueba.png`.

La salida del modelo es una **puntuación**, no una probabilidad clínica calibrada: un 0,6 no
significa 60 % de probabilidad de malignidad.

## 6. Interfaz (Gradio)

- **Cómo ejecutarla:** `notebooks/09_gradio.ipynb` en Colab. Carga el modelo final
  (`results/modelo_final.json`) y el umbral 0,3 (`results/umbral_final.json`) y muestra la
  interfaz dentro del notebook. Código en `src/app_gradio.py`.
- **Formatos admitidos:** PNG, JPG o DICOM (.dcm) del **recorte de una lesión** en escala de grises.
  Un DICOM se normaliza min-max como en el notebook 04; un PNG o JPG se usa con sus valores de 8
  bits. Después se rellena a cuadrado y se lleva a 224x224, igual que en el entrenamiento.
- **Salida:** la imagen que ve el modelo, la clase (maligna si la puntuación es mayor o igual a
  0,3), la puntuación y el aviso de que no es una probabilidad calibrada.
- **Imágenes inválidas, en dos capas:** Gradio rechaza cualquier extensión distinta de PNG, JPG o
  DICOM (`results/gradio_rechazo.png`), y `leer_entrada` rechaza con un mensaje los archivos
  dañados, las imágenes constantes, las de menos de 32 px por lado, las de más de 2000 px
  (mamografías completas o máscaras; los recortes miden como máximo 839 px) y las máscaras
  binarias. Los 6 casos están probados en el notebook 09.
- **Coherencia con el notebook:** para la misma lesión la interfaz debe dar la misma puntuación
  que `pred_val_final.csv`; el notebook 09 lo comprueba con 5 lesiones de validación.

La interfaz muestra de forma visible: *«Prototipo académico; no apto para
diagnóstico ni decisiones clínicas»* (`results/gradio_prediccion.png`).

## 7. Limitaciones

- Prototipo académico: no diagnostica cáncer ni sirve para decisiones médicas.
- La etiqueta es el diagnóstico patológico de una lesión, no el de una paciente.
- Conjunto pequeño (211 lesiones de 105 pacientes) y de una sola fuente: riesgo de
  sobreajuste y de sesgo de selección. [Añadir cómo se eligió el subconjunto.]
- Validación y prueba con solo 10 y 11 lesiones malignas: la sensibilidad es muy
  inestable y las comparaciones entre modelos tienen poca potencia estadística.
- La validación tiene 27 % de malignas frente a 43,8 % en entrenamiento: el umbral
  elegido en validación puede no transferirse a la prueba.
- Se usó una partición propia, no la oficial; los resultados no son comparables con
  otros trabajos sobre CBIS-DDSM.
- El modelo clasifica recortes de lesión, no mamografías completas.
- Un paciente tiene lesiones de ambas clases, por lo que la estratificación por
  paciente no es perfecta.
- Las imágenes de CBIS-DDSM son mamografías de película escaneadas (DDSM, de finales de los años
  90), lo que puede limitar la generalización a mamografías digitales actuales.
- La salida del modelo es una puntuación, no una probabilidad clínica calibrada.
- El modelo, la condición del experimento y el umbral se eligieron con la misma validación de 37
  lesiones; en prueba el rendimiento bajó (AUC de 0,881 a 0,706 y sensibilidad de 0,80 a 0,455).
- Los aumentos moderados no evitaron el sobreajuste: el AUC de entrenamiento llega a casi 1 en
  todas las corridas.
- Con una sola partición de 28 lesiones de prueba no se puede afirmar que ResNet18 sea mejor que
  la línea base.

## 8. Estructura del repositorio

```
Mamografias/
├── README.md
├── BITACORA.md
├── requirements.txt
├── .gitignore
├── data/            (ignorada por Git: CSV originales y DICOM)
├── particiones/     train.csv, val.csv, test.csv, reporte_particion.txt,
│                    lesiones_descargadas.txt
├── src/             01_particion.py, 00_seleccion_subconjunto.py, modelo_utils.py,
│                    app_gradio.py
├── notebooks/       01_lectura_imagenes, 02_eda_particion, 03_eda_imagenes,
│                    04_preprocesamiento, 05_entrenamiento, demo_dia7,
│                    06_experimento, 07_umbral_errores, 08_prueba_final, 09_gradio
├── weka/
│   ├── arff/
│   └── capturas/
├── results/         gráficos, métricas, modelo_final.json, umbral_final.json
│   └── prueba_final/  métricas y errores de la prueba, EVALUADA.txt
└── informe/
```

No se versionan los DICOM, los PNG preprocesados, los checkpoints `.pt` ni los archivos con
rutas de Google Drive (`indice_dicom.csv`, `lesiones_disponibles.csv`, `archivos_ilegibles.csv`).

## 9. Cómo reproducir

1. Clonar el repositorio:
   `git clone https://github.com/SrEffry/Mamografias.git`
2. Crear el entorno e instalar dependencias:
   `python -m venv venv`, activarlo y `pip install -r requirements.txt`
3. Descargar los CSV de masas de CBIS-DDSM y colocarlos en `data/`.
4. Obtener las imágenes: `particiones/lesiones_descargadas.txt` lista las 211 lesiones.
   Con los CSV se obtienen los `SeriesInstanceUID` de sus series ROI
   (tercer componente de las rutas `cropped image file path` y `ROI mask file path`),
   que se descargan de IDC.
5. Indexar los DICOM leyendo el encabezado (notebook `02_eda_particion`) y generar
   `lesiones_descargadas.txt`.
6. Partición por paciente (semilla 42):
   ```
   python src/01_particion.py --data data --out particiones --modo propio \
       --disponibles particiones/lesiones_descargadas.txt
   ```
7. Copiar `src/modelo_utils.py` y `src/app_gradio.py` a la carpeta `src` de Drive y ejecutar en
   Colab con GPU, en orden: `03_eda_imagenes`, `04_preprocesamiento`, `05_entrenamiento`,
   `06_experimento`, `07_umbral_errores`, `08_prueba_final` y `09_gradio`.
8. `08_prueba_final` evalúa la prueba **una sola vez**: deja un candado
   (`resultados/prueba_final/EVALUADA.txt`) y se detiene si se vuelve a ejecutar.
9. En `09_gradio`, la interfaz se muestra dentro del notebook. El enlace público `gradio.live`
   no se usa porque en Colab daba error 404 o 504.

Tiempos aproximados en una Tesla T4: 05 unos 2 minutos, 06 unos 5 minutos, 07 a 09 menos de
1 minuto cada uno.

## 10. Referencias

- Lee, R. S. et al. *A curated mammography data set for use in computer-aided
  detection and diagnosis research* (CBIS-DDSM). Scientific Data, 4, 170177, 2017.
- The Cancer Imaging Archive (TCIA): https://www.cancerimagingarchive.net/
- NCI Imaging Data Commons (IDC): https://portal.imaging.datacommons.cancer.gov/