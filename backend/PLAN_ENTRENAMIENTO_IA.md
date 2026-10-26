# Plan para mejorar el detector con casos reales

## Objetivo

Adaptar el análisis a estafas reales, jerga argentina, faltas de ortografía y nuevas modalidades sin permitir que reportes falsos cambien automáticamente el comportamiento del sistema.

La opción recomendada para este proyecto es un ciclo de **datos revisados + ejemplos dinámicos + evaluación automática**. Es gratuito con la infraestructura actual y permite mejorar antes de pagar un ajuste fino de un modelo.

## Etapa 1: construir un conjunto de casos revisados

Crear en Firestore la colección `casos_entrenamiento`. Solo un administrador puede aprobar elementos para esta colección.

Campos propuestos:

- `texto_anonimizado`: mensaje sin correos, teléfonos, enlaces, documentos, claves ni datos personales.
- `origen`: `reporte_comunidad`, `feedback_analisis` o `caso_sintetico`.
- `riesgo_correcto`: `bajo`, `medio` o `alto`.
- `tipo_estafa`: suplantación familiar, bancaria, premio, adelanto, empleo, inversión, compraventa, soporte falso, robo de cuenta, secuestro virtual u otra.
- `senales_confirmadas`: lista breve de señales presentes.
- `prediccion_original`: salida que produjo el sistema.
- `modelo` y `version_prompt`: versiones utilizadas para poder reproducir errores.
- `revisado_por` y `revisado_en`: auditoría administrativa.
- `aprobado_para_aprendizaje`: impide usar datos sin revisión.

Nunca se deben guardar contraseñas, códigos de verificación, datos de tarjetas ni el texto original sin anonimizar. Los reportes comunitarios solo se incorporan después de su moderación para evitar contaminación intencional del conjunto de datos.

## Etapa 2: feedback desde la aplicación

Después de cada análisis se puede mostrar:

- `La clasificación fue correcta`.
- `Era más peligroso de lo indicado`.
- `Fue un falso positivo`.
- `Indicar el tipo de estafa`.

El feedback crea un candidato pendiente. Un administrador revisa el caso antes de aprobarlo. La aplicación nunca cambia el modelo directamente a partir de un solo voto.

## Etapa 3: ejemplos dinámicos para Groq

Antes de consultar Groq, el backend selecciona entre tres y cinco casos aprobados que compartan señales o tipo de estafa con el mensaje nuevo. Envía versiones cortas y anonimizadas como ejemplos del criterio esperado.

Para la primera versión no hace falta una base vectorial paga. Firestore puede filtrar por `tipo_estafa` y `senales_confirmadas`, y el backend puede mantener una caché pequeña de ejemplos revisados. Esta técnica permite adaptar el modelo a modalidades locales sin modificar sus pesos.

Los ejemplos deben estar balanceados entre mensajes de riesgo alto, medio y bajo. Si solo se agregan estafas, el sistema terminará marcando mensajes normales como peligrosos.

## Etapa 4: evaluación antes de publicar cambios

Mantener un conjunto de evaluación separado que nunca se incluya entre los ejemplos enviados al modelo. Cada cambio de reglas, prompt o modelo debe medir como mínimo:

- porcentaje de estafas de riesgo alto detectadas;
- falsos negativos de riesgo alto;
- falsos positivos sobre mensajes normales;
- precisión por tipo de estafa;
- respuestas inválidas, tiempos de espera y fallos del proveedor.

La prioridad del proyecto debe ser reducir los falsos negativos de riesgo alto sin convertir todos los mensajes ambiguos en alertas máximas. Cada resultado debe guardar `version_motor`, `version_prompt` y `modelo`.

## Etapa 5: ajuste fino opcional

El ajuste fino solo conviene cuando existan varios cientos o miles de casos revisados y balanceados. La inferencia LoRA de Groq requiere actualmente acceso empresarial y el entrenamiento se realiza fuera de Groq, por lo que no encaja con el requisito gratuito de esta etapa.

Hasta entonces, reglas versionadas, ejemplos revisados y evaluación continua ofrecen más control, menor costo y una explicación clara de cada alerta.

## Orden de implementación recomendado

1. Guardar un identificador de análisis y su versión.
2. Crear el endpoint de feedback y la cola de revisión administrativa.
3. Anonimizar y aprobar casos para `casos_entrenamiento`.
4. Preparar un conjunto inicial balanceado de casos argentinos.
5. Añadir recuperación de ejemplos a la consulta de Groq.
6. Ejecutar la evaluación automática antes de cambiar el prompt o el modelo activo.
