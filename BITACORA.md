# Bitácora del proyecto

**Proyecto:** Clasificación de lesiones mamográficas benignas y malignas mediante aprendizaje profundo
**Asignatura:** Aprendizaje Computacional - Ingeniería de Sistemas
**Repositorio:** https://github.com/SrEffry/Mamografias

> Prototipo académico; no apto para diagnóstico ni decisiones clínicas.

---

## 15/11/2026 - Día 1

**Actividad:** Selección del dataset, análisis de los CSV de metadatos, definición de
etiquetas, hipótesis y repositorio; primeras imágenes.

**Qué hice:**
- Revisé las tres fuentes que recomienda la guía: CBIS-DDSM, VinDr-Mammo e INbreast.
- Descargué los cuatro CSV de CBIS-DDSM (masas y calcificaciones, train y test) y revisé
  columnas, clases, pacientes únicos, vistas, valores faltantes y duplicados:

  | Archivo | Lesiones | Pacientes | MALIGNANT | BENIGN | BENIGN_WITHOUT_CALLBACK |
  |---|---|---|---|---|---|
  | mass train | 1318 | 691 | 637 | 577 | 104 |
  | mass test | 378 | 201 | 147 | 194 | 37 |
  | calc train | 1546 | 602 | 544 | 528 | 474 |
  | calc test | 326 | 151 | 129 | 130 | 67 |

- Comprobé que train y test oficiales no comparten pacientes.
- Definí la unidad de análisis (lesión) y el mapeo de etiquetas.
- Escribí en el README las hipótesis H1 y H2, el costo de los errores y las
  limitaciones, antes de cualquier experimento.
- Creé el repositorio en GitHub y la estructura inicial.
- [Primera descarga de imágenes por IDC y lectura de las primeras con pydicom en Colab.
  Dimensiones observadas: mamografías completas 4808x3024 y 5341x3496; recorte 434x387;
  máscara 4556x2585.]

**Hallazgos sobre los datos:**
- Hay hasta 14 lesiones por paciente y 1592 mamografías distintas para 1696 lesiones de
  masas: varias lesiones comparten la misma mamografía. Hay que dividir por paciente.
- La columna `assessment` (BI-RADS) casi contiene la respuesta: en masas train, 293 de
  299 lesiones con assessment 5 son malignas, y ninguna con assessment 2 lo es.
- Valores faltantes en masas train: `mass margins` (43) y `mass shape` (4).
- Las rutas de `ROI mask file path` terminan con un salto de línea que hay que limpiar.
- En el CSV, recorte y máscara apuntan a `000000.dcm` o `000001.dcm` en un orden que no
  es consistente (en masas suele ser recorte 000000 y máscara 000001; en calcificaciones,
  al revés); en 92 filas de masas train y 11 de test ambas rutas terminan en
  `000000.dcm`.
- Con el mapeo binario, masas train queda 637 malignas / 681 benignas (48,3 %) y masas test
  147 / 231 (38,9 %).

**Dificultad:**
- Comandos de PowerShell usados en CMD (`New-Item`), configuración de la identidad de Git
  y un push rechazado porque GitHub ya tenía un commit inicial; resueltos con
  `type nul`, `git config` y un `git pull --allow-unrelated-histories`.
- No era posible distinguir recorte y máscara por el nombre del archivo.
- El dataset completo en DICOM es muy pesado.

**Alternativas consideradas:**
- **VinDr-Mammo:** BI-RADS indica sospecha radiológica, no malignidad confirmada, y exige
  acceso en PhysioNet.
- **INbreast:** solo 410 imágenes, pocas para evaluar con partición por paciente.
- **CBIS-DDSM, calcificaciones:** lesiones muy pequeñas que se pierden al reducir a 224x224.
- **CBIS-DDSM, masas:** lesiones más visibles y clases equilibradas con el mapeo binario.

**Decisiones:**
1. **Dataset:** CBIS-DDSM, solo masas, con la lesión como unidad de análisis.
2. **Mapeo:** BENIGN y BENIGN_WITHOUT_CALLBACK pasan a benigna (0); MALIGNANT a maligna (1).
3. **Entrada del modelo:** el recorte ROI y no la mamografía completa, porque la lesión
   ocupa una fracción mínima de la imagen completa y esta trae texto grabado que un modelo
   podría aprender.
4. **Herramientas:** Weka para el EDA de los CSV; Python para DICOM, partición, modelado y Gradio.
5. **Variables:** no usar `assessment`, `patient_id` ni las rutas como predictores.

**Evidencia:** README con mapeo e hipótesis, commits fechados, [capturas en weka/capturas/].

**Contribución individual:** [Describir con precisión qué hice yo.]

---

## 16/11/2026 - Día 2

**Actividad:** Descarga e indexación de los DICOM, EDA con Weka, partición por paciente.

**Qué hice:**
- **EDA en Weka** sobre el CSV de masas train (relación `mass_train_limpio`, 1318 instancias):
  conteo de `pathology` (637 / 577 / 104), `patient_id` con 691 valores distintos
  (196 aparecen una sola vez, un 15 %), `mass_margins` con 43 faltantes (3 %) e histogramas
  de todos los atributos. [Falta la captura del test.]
- **Cruce de las imágenes con el CSV.** El primer cruce por nombre de carpeta dio 0
  coincidencias porque los archivos de IDC vienen planos (nombrados por instancia), sin
  carpetas por lesión. Lo resolví con los manifiestos de IDC (`File Instance Name` y
  `Series ID`). Primer resultado: 167 archivos, 113 series, 59 lesiones con el criterio
  laxo (cualquiera de las tres imágenes) y 57 con el criterio estricto (serie ROI), de 29
  pacientes, todas del train oficial.
- **Segunda y tercera descarga**, incluyendo lesiones del test. Para no depender de los
  manifiestos ni de la carpeta, indexé los DICOM leyendo el encabezado con pydicom
  (SeriesInstanceUID, SOPInstanceUID, Rows y Columns) y cruzando por UID de serie con el CSV.
  Tras la segunda descarga (470 archivos): 160 lesiones completas, 57 de train y 103 de test.
- **Tras la tercera descarga:** 623 archivos, 6 de ellos ilegibles, 617 válidos en 417 series.
  Lesiones completas (recorte + máscara): **211**, de ellas 108 de train (54 pacientes, 52
  malignas) y 103 de test (51 pacientes, 33 malignas).
- **Partición por paciente** de esas 211 lesiones (ver decisiones).

**Hallazgos:**
- Cada lesión tiene una mamografía completa (1 archivo) y una serie ROI con recorte y
  máscara juntos (2 archivos). Por eso 167 archivos no eran 59 lesiones: 167 = 54 series de
  2 archivos + 59 series de 1 archivo.
- 6 archivos pesan 0 bytes y no tienen cabecera DICM (probablemente una descarga o copia
  interrumpida). Con `force=True` se leían sin error como "desconocido" y, al deduplicar por
  (series_uid, sop_uid), se fusionaban en una sola fila y parecían 5 duplicados. No lo eran.
- Los 617 archivos válidos tienen todos cabecera DICM: `force=True` no era necesario, y
  conviene evitarlo para que un archivo malo no pase sin avisar.
- Dos lesiones (P_00408_RIGHT_MLO_1 y P_00413_LEFT_MLO_1) tienen un solo archivo ROI.
- Con la partición se comprobó que hay 1 paciente con lesiones de ambas clases.

**Dificultad:**
- El cruce por carpeta fallaba (0 coincidencias) por la estructura plana de IDC.
- El criterio de cruce laxo marcaba como disponibles lesiones sin recorte, y varias lesiones
  comparten mamografía, así que contaba de más. Pasé a un criterio estricto.
- El conjunto de entrenamiento descargado era pequeño (108 lesiones, 54 pacientes) y la
  prevalencia de malignas difería entre train (48 %) y test (32 %).
- Los scripts no se encontraban en Colab (otro entorno distinto de mi PC) y un archivo se
  guardaba en la carpeta temporal en vez de en Drive.

**Alternativas consideradas:**
- **A:** descargar más lesiones de train y conservar la partición oficial.
- **B:** juntar lo descargado y repartirlo por paciente.
- **Semilla:** conservar la 42 o buscar otra con las particiones más equilibradas.

**Decisiones:**
1. **Criterio de lesión disponible:** solo si tiene su serie ROI completa (2 archivos) y el
   menor de los dos, por área, es el recorte (la máscara es la de mayor área).
2. **Archivos vacíos:** excluidos del índice y registrados, sin volver a descargarlos.
   Cifras finales: 617 archivos válidos, 417 series, 211 lesiones completas.
3. **Opción B:** juntar las 211 lesiones y repartirlas por paciente con `StratifiedGroupKFold`
   (semilla 42) en ~71 % / 14 % / 14 %, por [limitación de espacio y tiempo: confirmar].
   Consecuencia: la partición ya no es la oficial.
4. **Semilla:** antes de entrenar, fijé un criterio (validación y prueba con 12-17 % de las
   lesiones y la menor diferencia de prevalencia respecto al total, 40,3 %) y escaneé 200
   semillas, de las cuales 113 cumplían el tamaño. La mejor era la 11 (desbalance 2,0 puntos);
   la 42 tiene 13,3. Ejecuté por error la semilla 12 (no salió del escaneo, desbalance 20,6 y
   tamaños bajo el criterio) y la descarté sin entrenar. Decidí **mantener la semilla 42 por
   simplicidad**. La elección no usa ningún resultado de modelo.

**Resultado de la partición (semilla 42):**

| Partición | Lesiones | Pacientes | Malignas | Benignas | % malignas |
|---|---|---|---|---|---|
| train | 146 | 74 | 64 | 82 | 43,8 % |
| val | 37 | 16 | 10 | 27 | 27,0 % |
| test | 28 | 15 | 11 | 17 | 39,3 % |

Pacientes solapados: 0 entre train y val, 0 entre train y test y 0 entre val y test.

**Limitaciones de esta decisión:**
- La validación tiene 27 % de malignas frente a 43,8 % en train: el umbral que elija con
  ella puede no transferirse a la prueba. Lo discutiré en el informe y revisaré la
  estabilidad del umbral.
- Con 10 y 11 malignas en validación y prueba, la sensibilidad es muy inestable. Por ejemplo,
  detectar 8 de 11 da un intervalo de confianza del 95 % de aproximadamente 43 % a 90 %.
  Reportaré intervalos de confianza.

**Evidencia:** commits [hashes], `particiones/reporte_particion.txt`, `src/01_particion.py`,
`weka/capturas/`, notebook de indexación, [escaneo_semillas.csv si lo guardaste].

**Contribución individual:** [Describir con precisión qué hice yo.]

**Pendiente:**
- EDA de imágenes: resolución de los recortes, ejemplos por clase y duplicados.
- Weka: captura del test y `.arff` sin rutas.
- `requirements.txt`, notebook depurado y guardado en GitHub.
- Preprocesamiento (224x224, normalización, aumentos solo en train) y línea base.

---

## 17/11/2026 - Día 3

> Borrador: lo que queda entre corchetes lo completa cada integrante. Borrar esta nota al terminar.

**Actividad:** EDA de las imágenes, verificación de la partición, limpieza del repositorio y
dependencias.

**Qué hice:**
- Verifiqué que los CSV de `particiones/` son los de la semilla 42 (146 / 37 / 28 lesiones, 0
  pacientes solapados) y no los de la semilla 12 que se ejecutó por error el día 2. Coinciden.
- Weka: subí al repositorio los `.arff` de `mass_train_limpio` y `mass_test_limpio`, que se
  generaron el 16/11 quitando `patient_id` y las tres columnas de rutas (filtro
  `Remove -R 1,12-14`), porque no son variables del problema. Conservan `assessment` solo para
  el EDA; no se usa como predictor. [Captura del test: hecha / pendiente.]
- EDA de los 211 recortes (`notebooks/03_eda_imagenes.ipynb`):
  - Vistas del subconjunto: 104 CC y 107 MLO, con proporciones de clase parecidas en ambas.
  - El `PatientID` del encabezado DICOM coincide con el `lesion_id` en los 211 recortes, y la
    `SeriesDescription` de todos es `cropped images`. Con eso se comprueba que el cruce por UID de
    serie y la regla del área eligieron el recorte y no la máscara.
  - Los 211 son MONOCHROME2 de 16 bits y ninguno es constante.
  - No hay duplicados por hash MD5 de los píxeles. Leer los 211 recortes sin errores sirve además
    como prueba de integridad de los píxeles.
  - Resolución: el alto mediano es 316,5 px en benignas y 341 px en malignas, y el ancho mediano
    325 y 346 px. 38 recortes tienen algún lado menor de 224 px y 32 tienen una relación de
    aspecto fuera de 0,8-1,25. La mediana de la relación es casi 1 en las dos clases.
  - Los recortes malignos son algo más grandes en promedio (unos 375 px de alto frente a 340 en
    benignas). Al llevar todos a 224x224 esa diferencia de tamaño absoluto deja de verse en la
    entrada del modelo.
  - Ejemplos por clase en `results/ejemplos_clases.png` (solo de entrenamiento).
- Ordené el repositorio: los notebooks pasaron a `notebooks/` y el de lectura de imágenes se
  renombró `01_lectura_imagenes`. Limpié `02_eda_particion` quitando las celdas obsoletas (cruce por
  carpeta y por manifiestos, la lectura con `force=True` y las celdas `%%writefile`); la versión
  anterior queda en el historial de Git. Subí los scripts de `src/`, las particiones de la semilla 42
  y las capturas de Weka, que estaban solo en Drive.
- Creé `requirements.txt` con las versiones de Colab y añadí `venv/` al `.gitignore`.

**Dificultad:** Leer los 211 recortes desde Drive tardó unos 3 minutos, así que leer DICOM en
cada época de entrenamiento no es viable. [Añadir cualquier otra dificultad real.]

**Alternativas consideradas:**
- Llevar el recorte a 224x224 estirándolo o rellenándolo primero a cuadrado.
- Guardar los recortes preprocesados o leer el DICOM de Drive en cada época.

**Decisión:** La mayoría de los recortes son casi cuadrados, pero 32 de 211 tienen una relación
de aspecto fuera de 0,8-1,25, así que se rellenan a cuadrado con ceros antes de redimensionar, para
no deformar la forma de la masa. Los recortes se preprocesan una sola vez y se guardan como PNG en
Drive, porque leer los DICOM tarda unos 3 minutos por pasada.

**Evidencia:** `notebooks/03_eda_imagenes.ipynb`, `results/eda_imagenes_resolucion.png`,
`results/ejemplos_clases.png`, `results/resumen_eda_imagenes.csv`, `weka/arff/`, commits [hash].

**Contribución individual:**
- Efren Suárez: [ ]
- Kevin Martínez: [ ]
- Iván González: [ ]

**Pendiente:** preprocesamiento y primer entrenamiento.

---

## 17/11/2026 - Días 4-5: preprocesamiento y línea base

> Los días 3 a 7 se trabajaron el mismo 17/11.

**Actividad:** Preprocesamiento de los recortes y entrenamiento de la línea base.

**Qué hice:**
- Preprocesé los 211 recortes con `notebooks/04_preprocesamiento.ipynb` y las funciones de
  `src/modelo_utils.py`: lectura del DICOM sin `force=True`, normalización min-max por imagen,
  relleno a cuadrado, redimensionado a 224x224 con `INTER_AREA` y guardado como PNG de 8 bits en
  Drive. Se generaron los 211 PNG sin errores.
- Entrené la línea base en `notebooks/05_entrenamiento.ipynb`: CNN de 4 bloques
  Conv-BN-ReLU-MaxPool con dropout 0,5 y 98.049 parámetros, semilla 42, batch 16, Adam, lr 1e-3,
  30 épocas, con aumentos solo en entrenamiento (volteo horizontal y rotación de ±10°) y guardando la
  época con mayor ROC-AUC de validación. Tardó 73,9 s en una GPU Tesla T4.
- Resultado en validación: AUC 0,648 (IC 95 % 0,47-0,82), mejor época 3. Con umbral 0,5,
  sensibilidad 0,10 (1 de 10 malignas) y especificidad 0,963 (26 de 27 benignas).

**Interpretación:** la línea base casi no aprende con esta configuración. El AUC de validación
osciló entre 0,46 y 0,65 y el de entrenamiento no pasó de 0,77. Al pasar el umbral de 0,4 a 0,3 la
especificidad cae de 0,778 a 0,037, o sea que casi todas sus puntuaciones quedan en un rango muy
estrecho.

**Dificultad:** [Añadir una dificultad real si la hubo.]

**Alternativas consideradas:** usar `pos_weight` en la pérdida o no usarlo.

**Decisión:** no usar `pos_weight`, porque en entrenamiento hay 64 malignas y 82 benignas (43,8 %
de malignas), que es un desbalance leve. No se cambiaron épocas ni learning rate después de ver los
resultados; cualquier cambio se hará como experimento controlado en los días 8 a 11.

**Evidencia:** `src/modelo_utils.py`, `notebooks/04_preprocesamiento.ipynb`,
`notebooks/05_entrenamiento.ipynb`, `results/preprocesamiento_ejemplos.png`,
`results/historial_baseline.csv`, `results/registro_experimentos.csv`, commits [hash].

**Contribución individual:**
- Efren Suárez: [ ]
- Kevin Martínez: [ ]
- Iván González: [ ]

---

## 17/11/2026 - Días 6-7: transferencia de aprendizaje, errores y preparación del control

**Actividad:** Entrenamiento preliminar con ResNet18, análisis de errores en validación.

**Qué hice:**
- Entrené ResNet18 preentrenada en ImageNet, con la capa final de 1 salida (11.177.025
  parámetros), con la misma semilla, batch, aumentos y partición que la línea base, Adam, lr 1e-4 y
  20 épocas. Tardó 36,0 s. Mejor época: 9.
- Resultados en validación con umbral 0,5 (`results/metricas_val.csv`):

  | Modelo | AUC (IC 95 %) | Sensibilidad (IC 95 %) | Especificidad (IC 95 %) | Precisión | F1 |
  |---|---|---|---|---|---|
  | Línea base | 0,648 (0,47-0,82) | 0,10 (0,02-0,40) | 0,963 (0,82-0,99) | 0,500 | 0,167 |
  | ResNet18 | 0,819 (0,63-0,99) | 0,60 (0,31-0,83) | 0,704 (0,52-0,84) | 0,429 | 0,500 |

- Efecto del umbral en validación con ResNet18 (`results/umbrales_val_resnet18.csv`):

  | Umbral | TP | FN | TN | FP | Sensibilidad | Especificidad |
  |---|---|---|---|---|---|---|
  | 0,5 | 6 | 4 | 19 | 8 | 0,60 | 0,704 |
  | 0,4 | 6 | 4 | 19 | 8 | 0,60 | 0,704 |
  | 0,3 | 7 | 3 | 18 | 9 | 0,70 | 0,667 |
  | 0,2 | 8 | 2 | 17 | 10 | 0,80 | 0,630 |

- Falsos negativos de ResNet18 con umbral 0,5: P_00198_LEFT_CC_1 (0,129), P_00396_LEFT_MLO_1
  (0,150), P_00198_LEFT_MLO_1 (0,246) y P_00324_RIGHT_CC_1 (0,357). Hay 8 falsos positivos, con
  puntuaciones entre 0,529 y 0,902.

**Interpretación preliminar:**
- ResNet18 aprende el conjunto de entrenamiento casi por completo (AUC de entrenamiento por encima
  de 0,99 desde la época 8), mientras la pérdida de validación sube después de la época 10. Eso
  indica sobreajuste, y por eso se usa el checkpoint de la época 9.
- **H1:** la diferencia de AUC es 0,171, mayor que 0,05, pero los intervalos se solapan. Con 37
  lesiones no se puede afirmar todavía que la diferencia sea real.
- **H2:** con umbral 0,5, la sensibilidad es menor que la especificidad en los dos modelos, y al
  bajar el umbral la sensibilidad de ResNet18 sube y la especificidad baja, como se esperaba.
  Todavía no se elige umbral; eso es de los días 8 a 11.
- Dos de los cuatro falsos negativos son las vistas CC y MLO de la misma paciente (P_00198), y los
  falsos positivos también se repiten por paciente. Los errores no son independientes, lo que hace
  la muestra efectiva aún más pequeña.

**Dificultad:**
- [Añadir otra dificultad real si la hubo.]

**Decisión:** usar el checkpoint de la mejor época por AUC de validación y no el de la última, por
el sobreajuste que muestran las curvas.

**Evidencia:** `notebooks/05_entrenamiento.ipynb`, `results/curvas_entrenamiento.png`,
`results/matriz_confusion_resnet18_val.png`, `results/errores_resnet18_val.png`,
`results/pred_val_resnet18.csv`, commits [hash].

**Contribución individual:**
- Efren Suárez: [ ]
- Kevin Martínez: [ ]
- Iván González: [ ]

**Pendiente:** preparar y ensayar la demostración del control del día 7. Días 8-11:
experimento controlado cambiando una sola decisión, análisis de los falsos negativos y selección
del umbral con validación.
