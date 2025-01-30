
DOCUMENT_PROCESSOR = """Valida la informacion de la empresa {enterprise} y extrae la información clave de un documento, centrándote en las siguientes prioridades: vigencia, empresa, póliza, logo, y firma.
#validity
-Identifica todos los períodos de vigencia mencionados (ej.: “01/01/2025 al 31/01/2025”). En caso de múltiples vigencias, listar cada rango de fechas encontrado. Si no aparece ninguna fecha, registra este campo como null.

# Steps

1. **Comprender el Documento**: Lee completamente el documento para entender su contenido y estructura.
2. **Buscar la Vigencia**: Identifica todas las menciones de fechas o periodos temporales que indiquen la vigencia del documento.
3. **Identificar la Empresa**: Localiza cualquier mención del nombre de una empresa que pudiera ser responsable del documento.
4. **Encontrar Información de la Póliza**: Busca números o identificadores que se mencionen junto a las palabras 'póliza' o 'Póliza de Pensiones', como en los ejemplos: 'Póliza de Pensiones No. 7011610151843' o 'Salud Póliza # 9194284'.
5. **Detectar el Logo**: Trata de ubicar descripciones o referencias hacia un elemento gráfico que podría ser el logo.
6. **Localizar Firmas**: Busca menciones o imágenes que indiquen la presencia de una firma.

# Notes

- Si alguna información no está claramente especificada en el documento, indica su ausencia con un valor null.
- La exactitud en la extracción y claridad de los términos es prioritaria para asegurar la utilidad del resultado.
- La poliza de la empresa es la póliza que se encuentra en el documento, no es necesario buscar en otro lugar.
- En caso de múltiples vigencias, listar cada rango de fechas encontrado.
- Te voy a proporcionar el nombre de la empresa, entonces tienes que detectar si dentro del documento existe el nombre de otra empresa o logo, si es así guarda estas anomalías en el campo "anomalias"."""

LOGO_DETECTION_PROMPT = """Validar si el logotipo de la empresa dentro de un documento coincide con el nombre de la empresa {enterprise} y si está presente en el documento.

Revise el documento para asegurar que el logotipo del mismo es coherente con los datos de la empresa.

# Pasos

1. **Extraer el Logo**: Identificar y extraer el logotipo presente en el documento.
2. **Comparar Logotipo y Datos**: Correlacione el logotipo extraído con los datos recopilados para garantizar su coherencia, verificando cualquier elemento distintivo de la marca.
3. **Conclusión**: Determine si el logotipo es concordante con los datos validados previamente, señalando cualquier inconsistencia encontrada.

# Formato de salida

Escriba una conclusión detallada en un breve párrafo. Indique si el logotipo coincide con los datos previamente evaluados y mencione cualquier discrepancia identificada. Responda con un "sí" o "no" en caso de coincidencia y especifique si existe el logotipo para ajustar el estado del documento.

# Notas

- Considere las variaciones de diseño que podrían existir en el logotipo oficial de la empresa.
- Frente a cualquier diferencia, evalúe si estas son menores y no comprometen la autenticidad del logotipo.
- Solo responda si el logotipo coincide y se encuentra presente para cambiar el estado."""

VERDICT_PROMPT = """Elaborar un veredicto organizado y preciso basado en diversos aspectos de la validación de documentos, incluida la validación del logotipo, la validez del documento y la detección de firmas.

Asegúrese de que el veredicto final tenga en cuenta los siguientes elementos:
- Validación del logotipo: Evalúa si el logotipo es válido basándose en {logo_diagnosis}.
- Validez del documento: Tenga en cuenta parámetros como {valid_data}.
- Detección de firmas: Evalúa la presencia y los datos de las firmas basándose en {signature_diagnosis}.

# Pasos

1. **Analizar la validación del logotipo**:
   - Comprobar cada entrada en {logo_diagnosis}.

2. **Evaluar la validez del documento**:
   - Validar los campos {valid_data}.

3. **Revisar la detección de firmas:
   - Examinar minuciosamente las entradas de {signature_diagnosis} incluye el análisis de `metadata`, como «número_de_página», «firmas_encontradas» y «detalles_de_firma».

4. **Compilar el veredicto final**:
   - Considere los resultados globales de los tres pasos de análisis para formar una conclusión unificada.
   - El veredicto final debe ser `Verdadero` si todas las validaciones son satisfactorias, en caso contrario `Falso`.


# Notas
-  SI logo_diagnosis tiene un valor null, entonces el logotipo no se encontró en el documento. Importante: si logo_status es true, significa que el logotipo existe en el documento !!!.
- Asegurarse de que todos los aspectos se analizan individualmente con el contexto de validaciones potencialmente fallidas que influyen en el veredicto final.
- Abordar los casos en los que no se esperan firmas en determinados documentos, lo que puede influir de forma diferente en el veredicto final."""
