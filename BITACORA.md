# Bitácora del proyecto

**Proyecto:** Clasificación de lesiones mamográficas benignas y malignas mediante aprendizaje profundo
**Asignatura:** Aprendizaje Computacional - Ingeniería de Sistemas
**Repositorio:** https://github.com/SrEffry/Mamografias

> Prototipo académico; no apto para diagnóstico ni decisiones clínicas.

---

## 15/11/2026 - Día 1

**Actividad:** Selección del dataset, análisis inicial de los CSV de metadatos,
definición de etiquetas y herramientas, y creación del repositorio.

**Qué hice:**
- Revisé las tres fuentes que recomienda la guía: CBIS-DDSM, VinDr-Mammo e INbreast.
- Entré a la página de CBIS-DDSM en TCIA y revisé la documentación, la licencia
  y los archivos disponibles.
- Descargué los cuatro CSV de metadatos: masas (train y test) y calcificaciones
  (train y test).
- Revisé columnas, clases, pacientes únicos, vistas, valores faltantes y duplicados:

  | Archivo | Lesiones | Pacientes | MALIGNANT | BENIGN | BENIGN_WITHOUT_CALLBACK |
  |---|---|---|---|---|---|
  | mass train | 1318 | 691 | 637 | 577 | 104 |
  | mass test | 378 | 201 | 147 | 194 | 37 |
  | calc train | 1546 | 602 | 544 | 528 | 474 |
  | calc test | 326 | 151 | 129 | 130 | 67 |

- Comprobé que las particiones oficiales de train y test no comparten ninguna
  paciente (ni en masas ni en calcificaciones).
- Definí la unidad de análisis (la lesión) y el mapeo de etiquetas.
- Escribí en el README las dos hipótesis, el costo de los errores y las
  limitaciones, antes de realizar cualquier experimento.
- Creé el repositorio en GitHub con la estructura inicial del proyecto.

**Hallazgos sobre los datos:**
- En masas train hay 1318 lesiones pero solo 1231 imágenes completas distintas,
  y una paciente llega a tener 14 lesiones. Dividir por lesión produciría fuga
  de datos, así que la partición debe ser por paciente.
- Hay 13 pacientes en train y 5 en test con lesiones de clases distintas, por
  lo que la estratificación por paciente no será perfecta (limitación).
- La columna `assessment` (BI-RADS) contiene casi la respuesta: en masas train,
  293 de 299 lesiones con assessment 5 son malignas, y ninguna con assessment 2
  lo es. No se usará como predictor.
- 129 lesiones de masas train tienen assessment 0 (evaluación incompleta).
- Valores faltantes en masas train: `mass margins` (43) y `mass shape` (4).
- Las rutas de `ROI mask file path` terminan con un salto de línea que hay que
  limpiar. La columna de densidad se llama `breast_density` en masas y
  `breast density` en calcificaciones.
- 79 pacientes aparecen tanto en masas como en calcificaciones.
- Distribución con el mapeo binario: masas train 637 malignas / 681 benignas
  (48,3 % malignas); masas test 147 / 231 (38,9 % malignas). La prueba tiene
  menos proporción de malignas que el entrenamiento.

**Dificultad:**
- El dataset completo en DICOM es pesado, por lo que debo trabajar con un
  subconjunto.
- Las rutas de recorte y máscara no son consistentes: en masas el recorte
  suele terminar en 000000.dcm y la máscara en 000001.dcm, en calcificaciones
  es al revés, y en 92 filas de masas train y 11 de test ambas rutas terminan
  en 000000.dcm. No se pueden distinguir por el nombre.
- Menor: errores iniciales con Git (identidad de usuario y un push rechazado
  porque GitHub ya tenía un commit inicial), que resolví integrando los
  historiales con un merge.

**Alternativas consideradas:**
- **VinDr-Mammo:** más grande y con BI-RADS, pero BI-RADS indica sospecha
  radiológica, no malignidad confirmada por patología, y requiere acceso en PhysioNet.
- **INbreast:** solo 410 imágenes, pocas para entrenar y evaluar con
  partición por paciente.
- **CBIS-DDSM, calcificaciones:** son lesiones muy pequeñas que se pierden al
  reducir a 224x224.
- **CBIS-DDSM, masas:** lesiones más visibles, clases equilibradas con el
  mapeo binario y patología confirmada por lesión.
- **Herramientas:** hacer todo en Python o dividir el trabajo con Weka.

**Decisiones:**
1. **Dataset:** CBIS-DDSM, solo masas, con la lesión como unidad de análisis.
2. **Mapeo de etiquetas:** BENIGN y BENIGN_WITHOUT_CALLBACK pasan a benigna (0);
   MALIGNANT pasa a maligna (1). La etiqueta proviene del diagnóstico
   patológico de la lesión, no de un diagnóstico a la paciente.
3. **Partición:** usar la partición oficial de test como prueba y obtener la
   validación del train oficial, agrupando por `patient_id` en Python
   (`GroupShuffleSplit` o `StratifiedGroupKFold`), con una comprobación de cero
   solapamiento entre particiones.
4. **Herramientas:** Weka para el análisis exploratorio y la limpieza de los
   CSV de metadatos; Python para DICOM, partición, modelado y Gradio. Weka no
   lee DICOM ni permite construir la interfaz.
5. **Variables:** no usar `assessment`, `patient_id` ni las rutas como
   predictores en ningún clasificador tabular.

**Evidencia:**
- README con mapeo de etiquetas, hipótesis, costo de errores y limitaciones.
- Commits fechados en el repositorio.
- CSV originales en data/ (ignorada por Git por su tamaño).
- [Captura del conteo de pathology en Weka, en weka/capturas/, cuando esté hecha.]

**Contribución individual:** [Describir con precisión qué hice yo.]

---

## [DD/MM/2026] - Día 2

**Actividad:** Acceso a las imágenes DICOM en Google Colab y lectura de las
primeras imágenes.

**Qué hice:**
- Monté el dataset en Colab [desde Google Drive / otra fuente] y leí archivos
  DICOM con pydicom.
- Escogí pacientes al azar para validar la lectura y la correspondencia con el CSV:
  [P_00001, P_02092, ...].
- Mostré mamografías completas, un recorte de lesión (ROI) y una máscara.
- Dimensiones observadas:
  - P_00001_LEFT_CC, mamografía completa: 4808 x 3024
  - P_02092_LEFT_MLO, mamografía completa: 5341 x 3496
  - P_02092_LEFT_CC_1, recorte ROI: 434 x 387
  - P_02092_LEFT_CC_1, máscara: 4556 x 2585
- [Descargué un subconjunto de N lesiones / N pacientes, elegido por ___.]

**Hallazgos:**
- El recorte y la máscara están en la misma carpeta de la lesión, pero tienen
  tamaños muy distintos: la máscara tiene el tamaño de la mamografía completa
  y el recorte es pequeño. Por eso se distinguen por dimensiones y no por el
  nombre del archivo (000000.dcm / 000001.dcm).
- En la mamografía completa la lesión ocupa una fracción muy pequeña de la
  imagen: al reducir a 224x224 quedaría de unos 20 píxeles de ancho (estimación
  aproximada a partir de la máscara observada).
- Las mamografías completas traen texto grabado en la imagen (por ejemplo
  "LCC", "LMLO" y números), que un modelo podría aprender en lugar de la lesión.

**Dificultad:** No se puede saber cuál archivo es recorte y cuál es máscara
por el nombre, y el orden cambia entre masas y calcificaciones. [Añadir
cualquier otro problema real: memoria, rutas largas, tiempos de lectura, etc.]

**Alternativas consideradas:**
- Usar la mamografía completa redimensionada (la lesión se vuelve diminuta y
  hay texto grabado en la imagen).
- Recortar la mamografía alrededor de la máscara con un margen.
- Usar directamente el recorte ROI que ya trae el dataset.

**Decisión:** Usar el recorte ROI como entrada del modelo e identificar recorte
y máscara por sus dimensiones (la máscara es la de mayor área). Consecuencia:
el prototipo clasifica recortes de lesiones, no mamografías completas, y la
interfaz Gradio recibirá un recorte. Se documentará como limitación.

**Evidencia:** notebooks/01_lectura_imagenes.ipynb, commit [hash], capturas de
las imágenes leídas.

**Contribución individual:** [Describir con precisión qué hice yo.]

**Pendiente:**
- Verificar que la máscara de una lesión coincide en dimensiones con su
  mamografía completa.
- Abrir los CSV en Weka y guardar las capturas del balance de clases.
- Script de partición por paciente con verificación de solapamiento.
- Completar requirements.txt y los datos del README (versión de Weka, entorno,
  subconjunto).

---

## [DD/MM/2026] - Día 3

**Actividad:**

**Qué hice:**
-

**Dificultad:**

**Alternativas consideradas:**

**Decisión:**

**Evidencia:**

**Contribución individual:**

**Pendiente:**
-