# \# Clasificación de lesiones mamográficas benignas y malignas

# 

# > \*\*Prototipo académico; no apto para diagnóstico ni decisiones clínicas.\*\*

# > Proyecto de clase de Aprendizaje Computacional. No diagnostica cáncer.

# 

# \## 1. Problema

# \- \*\*Usuario:\*\* (estudiantes y docentes, contexto educativo)

# \- \*\*Unidad de análisis:\*\* lesión (una fila por lesión, no por imagen ni por paciente)

# \- \*\*Significado de las etiquetas:\*\* la etiqueta viene del diagnóstico patológico

# &#x20; de la lesión, no de un diagnóstico a la paciente.

# 

# \## 2. Dataset

# \- \*\*Fuente:\*\* CBIS-DDSM (TCIA)

# \- \*\*Versión y licencia:\*\* (completar)

# \- \*\*Subconjunto elegido:\*\* (por ejemplo, solo masas) y por qué

# \- \*\*Pacientes / imágenes / vistas CC-MLO:\*\* (completar tras el EDA)

# 

# \## 3. Mapeo de etiquetas

# 

# | Etiqueta original | Etiqueta del proyecto |

# |---|---|

# | BENIGN | Benigna (0) |

# | BENIGN\_WITHOUT\_CALLBACK | Benigna (0) |

# | MALIGNANT | Maligna (1) |

## 4. Hipótesis (escritas antes de experimentar)

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

## 5. Costo de los errores
- **Falso negativo:** una lesión maligna clasificada como benigna. En un
  contexto real retrasaría el diagnóstico y el tratamiento, por eso es el
  error más grave y el que se busca reducir.
- **Falso positivo:** una lesión benigna clasificada como maligna. Genera
  ansiedad, pruebas adicionales y posibles biopsias innecesarias, pero suele
  ser reversible.

## 6. Limitaciones
- Prototipo académico: no diagnostica cáncer ni sirve para decisiones médicas.
- La etiqueta es el diagnóstico patológico de una lesión, no el de una paciente.
- Dataset pequeño y de una sola fuente: riesgo de sobreajuste y de sesgo de selección.
- La salida del modelo es una puntuación, no una probabilidad clínica calibrada.

# \## 7. Cómo reproducir

# (completar al final)

