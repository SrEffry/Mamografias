# Bitácora del proyecto

**Proyecto:** Clasificación de lesiones mamográficas benignas y malignas mediante aprendizaje profundo
**Asignatura:** Aprendizaje Computacional - Ingeniería de Sistemas
**Repositorio:** https://github.com/SrEffry/Mamografias

> Prototipo académico; no apto para diagnóstico ni decisiones clínicas.

---

## 15/11/2026 - Día 1

**Actividad:** Búsqueda y selección del dataset, definición inicial de etiquetas
y herramientas, y creación del repositorio.

**Qué hice:**
- Revisé las tres fuentes que recomienda la guía: CBIS-DDSM, VinDr-Mammo e INbreast.
- Entré a la página de CBIS-DDSM en TCIA y revisé la documentación, la licencia
  y los archivos disponibles.
- Descargué los CSV de metadatos de [masas / calcificaciones]:
  [mass_case_description_train_set.csv y mass_case_description_test_set.csv].
- Abrí los CSV y revisé las columnas (patient_id, pathology, rutas de imagen
  completa y de ROI) y los valores de la columna pathology.
- Definí la unidad de análisis (la lesión) y el mapeo de etiquetas.
- Escribí en el README las dos hipótesis, el costo de los errores y las
  limitaciones, antes de realizar cualquier experimento.
- Creé el repositorio en GitHub con la estructura inicial del proyecto
  y configuré el entorno de trabajo.
- [Descargué un subconjunto de N lesiones / aún no descargo imágenes porque ...].

**Dificultad:**
- [Ejemplo: el dataset completo en DICOM pesa cientos de GB y mi disco o mi
  conexión no lo permiten, así que necesito trabajar con un subconjunto.]
- [Ejemplo: no tenía claro cuál ruta del CSV corresponde a la imagen completa,
  cuál al recorte y cuál a la máscara.]
- [Ejemplo: no tenía claro qué significa BENIGN_WITHOUT_CALLBACK.]
- Menor: tuve errores iniciales con la configuración de Git (identidad de
  usuario y un push rechazado porque GitHub ya tenía un commit inicial), que
  resolví integrando los historiales con un merge.

**Alternativas consideradas:**
- **VinDr-Mammo:** más grande y con BI-RADS, pero BI-RADS indica sospecha
  radiológica, no malignidad confirmada por patología, y requiere acceso en PhysioNet.
- **INbreast:** solo 410 imágenes, pocas para entrenar y evaluar con
  partición por paciente.
- **CBIS-DDSM:** trae patología por lesión y ROI, y encaja con la tarea binaria
  que propone la guía.
- **Herramientas:** hacer todo en Python o dividir el trabajo con Weka.

**Decisiones:**
1. **Dataset:** usar CBIS-DDSM, solo [masas], con la lesión como unidad de
   análisis. Elegí [masas] por [ser un tipo de lesión más homogéneo / requerir
   una descarga menor / ...].
2. **Mapeo de etiquetas:** BENIGN y BENIGN_WITHOUT_CALLBACK pasan a benigna (0);
   MALIGNANT pasa a maligna (1). La etiqueta proviene del diagnóstico patológico
   de la lesión, no de un diagnóstico a la paciente.
3. **Herramientas:** usar Weka para el análisis exploratorio y la limpieza de los
   CSV de metadatos, y Python para la lectura de DICOM, la partición, el
   modelado y la interfaz en Gradio. Weka no lee DICOM ni permite construir
   la interfaz.
4. **Partición:** se hará por paciente en Python (`GroupShuffleSplit` con
   patient_id), para evitar que imágenes de una misma paciente queden en
   entrenamiento y prueba a la vez.

**Evidencia:**
- Repositorio con README (mapeo de etiquetas, hipótesis, costo de errores
  y limitaciones) y commits fechados.
- CSV originales en data/ (ignorada por Git por su tamaño).
- [Captura del conteo de la columna pathology en weka/capturas/ cuando esté hecha.]

**Contribución individual:** [Todo el trabajo descrito fue realizado por mí.]

**Pendiente para el día 2:**
- Abrir los CSV en Weka y obtener el balance de clases y el número de pacientes únicos.
- Descargar un subconjunto trazable de imágenes DICOM.
- Leer y mostrar las primeras imágenes en un notebook.