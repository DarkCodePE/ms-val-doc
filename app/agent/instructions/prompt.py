
DOCUMENT_PROCESSOR = """Valida la informacion del documento para la razon social {enterprise} y analisa la información clave del siguiente documento {document_data}, centrándote en las siguientes prioridades: vigencia, empresa, póliza, logo, y firma.
**Input Document Data:**
"document_data":  {document_data}

# Steps

1. **Comprender el Documento**: Lee completamente el documento para entender su contenido y estructura.
2. **Buscar la Vigencia**: Identifica todas las menciones de fechas o periodos temporales que indiquen la vigencia del documento.
3. **Fecha de emisión**: Busca la fecha de emisión del documento, si se encuentra, normalmente se encuentra en la parte superior del documento.
3. **Empresa**: Busca el nombre de la empresa que emite el documento, tienes que guardar el nombre de la empresa en el campo "company", difiere del nombre de la razón social {enterprise}, y el igual a logotipo.
4. **Identificar la Empresa**: Localiza cualquier mención del nombre de una empresa que pudiera ser responsable del documento.
5. **Encontrar Información de la Póliza**: Busca números o identificadores que se mencionen junto a las palabras 'póliza' o 'Póliza de Pensiones'.

# Output Format

Produce una respuesta estructurada en formato JSON con las siguientes claves:
- "validity": [rango_fechas_o_null],
- "company": nombre_empresa_o_null,
- "policy_number": numero_de_poliza_o_null,
- "date_of_issuance": fecha_de_emision_o_null,
# Notes

- Indica la ausencia de alguno de los elementos requeridos con el valor null si dicha información no está claramente especificada en el documento.
- La exactitud en la extracción de información y la claridad de los términos es prioritaria para asegurar la utilidad del resultado."""

LOGO_DETECTION_PROMPT = """Validar si el logotipo de la empresa dentro de un documento y corresponde a la razón social {enterprise} o la empresa {company}.

Revise el documento para asegurar que el logotipo del mismo es coherente con los datos {document_data} de la empresa.

# Pasos

1. **Extraer el Logo**: Identificar y extraer el logotipo presente en el documento.
2. **Comparar Logotipo y Datos**: Correlacione el logotipo extraído con los datos recopilados para garantizar su coherencia, verificando cualquier elemento distintivo de la marca.
3. **Conclusión**: Determine si el logotipo es concordante con los datos validados previamente.

# Notas

- Considere las variaciones de diseño que podrían existir en el logotipo oficial de la empresa.
- Solo responda si el logotipo coincide y se encuentra presente."""

VERDICT_PROMPT = """Elaborar un veredicto organizado y preciso basado en los veredictos de las páginas individuales, incluida la validación del logotipo, la validez del documento y la detección de firmas.

# Pasos

1. **Analizar el veredicto de las páginas**:
    - Veredicto de las páginas: Evalúa los veredictos de las páginas individuales, tomando en cuanta la pagina {approved_pages} aprobadas y {rejected_pages} rechazadas.

2. **Evaluar la razonamiento de la validez del documento de las páginas**:
    - Razonamiento de la validez: Evalua la razón por la cual se considera que el documento no es válido {page_verdicts}.

3. **Revisar la detección de firmas:
   - Detección de firmas: Evalúa la presencia y los datos de las firmas basándose en {total_found}, si el es mayor a cero, se considerará válida.

4. **Compilar el veredicto final**:
   - Considere los resultados globales de los tres primeros pasos de análisis para formar una conclusión unificada.
   - El veredicto final debe ser analizado en detalle para determinar si el documento es válido o no, y se de explicar los motivos de su decisión en el campo "reason".


# Notas
- Asegurarse de que todos los aspectos se analizan individualmente con el contexto de validaciones potencialmente fallidas que influyen en el veredicto final.
- Explica la razon por la cual se considera que el documento no es válido.
"""

VERDICT_PAGE_PROMPT = """Elaborar un veredicto organizado y preciso basado en diversos aspectos de la validación de documentos, incluida la validación del logotipo, la validez del documento y la detección de firmas, por numero de pagina {page_num}.

# Pasos

1. **Analizar la validación del logotipo**:
   - Validación del logotipo: Evalúa si el logotipo es válido basándose en {logo_diagnosis}.

2. **Evaluar la validez del documento**:
    - Validez del documento: la vigencia es valida si {date_of_issuance} es anterior o igual al inicio del rango {validity} y no puede ser postetior al rango {validity}.

3. **Evaluar la detección de firmas**:
    - Detección de firmas: Evalúa la presencia y los datos de las firmas basándose en {signature_info}.

3. **Compilar el veredicto final**:
   - Considere los resultados globales de los tres primeros pasos de análisis para formar una conclusión unificada.
   - El veredicto final debe ser analizado en detalle para determinar si el documento es válido o no, y se de explicar los motivos y observaciones de su decisión en el campo "reason".


# Notas
-  SI {logo_diagnosis} tiene un valor null, entonces el logotipo no se encontró en el documento. Importante: si logo_status es true, significa que el logotipo existe en el documento !!!.
- Asegurarse de que todos los aspectos se analizan individualmente con el contexto de validaciones potencialmente fallidas que influyen en el veredicto final.
- Explica la razon por la cual se considera que el documento no es válido.
- el campo "reason" debe detallar los motivos de la decisión final, incluyendo cualquier inconsistencia o discrepancia que haya encontrado en los datos.
"""

