
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
6. **Buscar Personas**: con el numero de poliza, busca el nombre de la persona asegurada {person} en la lista de asegurados, una ves encontrada, debes guardar el nombre de la persona asegurada en el campo "person_by_policy", su poliza en "policy_number" y la empresa en "company".

# Output Format

Produce una respuesta estructurada en formato JSON con las siguientes claves:
- "validity": [rango_fechas_o_null],
- "company": [nombre_empresa_o_rason_social_o_null],
- "policy_number": [numeros_de_poliza_o_null],
- "date_of_issuance": fecha_de_emision_o_null,
- "person_by_policy": [person_by_policy_o_null],
# Notes

- Indica la ausencia de alguno de los elementos requeridos con el valor null si dicha información no está claramente especificada en el documento.
- La exactitud en la extracción de información y la claridad de los términos es prioritaria para asegurar la utilidad del resultado.
- Para la busqueda de personas aseguradas, se debe buscar el nombre de la persona asegurada con el numero de poliza en la lista de asegurados, si no se encuentra, se debe indicar null.
"""

LOGO_DETECTION_PROMPT = """Validar si el logotipo de la empresa dentro de un documento y corresponde a la razón social {enterprise} o la empresa {company}.

Revise el documento para asegurar que el logotipo del mismo es coherente con los datos {document_data} de la empresa.

# Pasos

1. **Extraer el Logo**: Identificar y extraer el logotipo presente en el documento.
2. **Comparar Logotipo y Datos**: Correlacione el logotipo extraído con los datos recopilados para garantizar su coherencia, verificando cualquier elemento distintivo de la marca.
3. **Conclusión**: Determine si el logotipo es concordante con los datos validados previamente.

# Notas

- Considere las variaciones de diseño que podrían existir en el logotipo oficial de la empresa.
- Solo responda si el logotipo coincide y se encuentra presente."""

VERDICT_PROMPT = """Elaborar un veredicto organizado y preciso basado en las observaciones de las páginas individuales, incluida la validación del logotipo, la validez del documento y la detección de firmas.

# Steps

1. **Analizar las observaciones de las páginas**:
    - Observaciones de las páginas: Evalúa las observaciones de las páginas individuales {pages_observations} para determinar si el documento es válido o no.

2. **Evaluar el razonamiento de la validez del documento de las páginas**:
    - Analiza y formula hipótesis sobre la validez del documento basándote en las observaciones de las páginas.

3. **Compilar el veredicto final**:
   - Integra los resultados de los dos pasos anteriores para formar una conclusión unificada.
   - Determina si el documento es válido o no, explicando los motivos en el campo "reason".

# Output Format

El veredicto final debe estructurarse en un formato que incluya la decisión de validez y las razones que respaldan esta decisión.

# Notas

- Asegúrate de que todos los aspectos se analizan individualmente en el contexto de posibles fallas y lista estos hallazgos en el veredicto final.
- Explica la razón por la cual se considera que el documento no es válido.

"""

VERDICT_PAGE_PROMPT = """Elaborar un veredicto organizado y preciso basado en diversos aspectos de la validación del documento, incluida la vigencia ,el número de póliza y la persona asegurada, por numero de pagina {page_num}.

# Pasos

1. **Validación de persona:**
   - Analiza la información de la persona asegurada {person} y verifica si coincide con el nombre de la persona asegurada {person_by_policy}, y la poliza {policy_number}, debe coincidir con el numero de poliza de la persona asegurada.
   
2. **Validación de vigencia:**
   - Asegúrate de que la fecha de emisión {date_of_issuance} no sea posterior a la fecha final del rango {validity}.
   - Verifica la existencia de al menos un número de póliza {policy_number}.

2 **Compilar veredicto final:**
   - Integra los resultados de las validaciones vigencia, número de póliza y persona asegurada.
   - Genera un estatus para cada categoría de la revisión: `validity_validation_passed`, `policy_validation_passed`, `person_validation_passed`.

# Notas
- Asegúrate de considerar cada aspecto por separado para identificar cualquier posible error y documentar estos hallazgos en el veredicto
"""

FINAL_VERDICT_PROMPT = """ Analisa los veredictos de las páginas {pages_verdicts} y tambien la informacion del diagnostico {page_diagnosis}, luego genera un veredicto final. Los veredictos individuales debe seguir los siguientes pasos.

# Pasos

1. **Validación de firma:**
   - Verifica si existe al menos una firma en el documento {total_found_signatures}. Si es así, la firma es válida.

2. **Validación del logotipo:**
   - revisa toda la información relacionada con el logotipo y la empresa para confirmar la validez del logotipo.

3. **Validación de vigencia:**
   - revisa los veredictos de las páginas individuales y también la información para confirmar la validez de la vigencia.
   - revisa los veredictos de las páginas individuales y también la información para confirmar si existe al menos un número de póliza.

4. **Compilar veredicto final:**
   - Integra los resultados de las validaciones de firma, logotipo, vigencia y número de póliza.
   - Genera un estatus para cada categoría de la revisión: `logo_validation_passed`, `signature_validation_passed`, `validity_validation_passed`, `policy_validation_passed`.

# Formato de Salida

Estructura el veredicto final como un párrafo que incluya la decisión de validez y las razones que apoyan cada criterio. Puede ser en un formato narrativo, proporcionando claridad y justificación de cada área evaluada.

**Salida:**

"La validación del documento indica que: la firma es válida ya que se detectó al menos una firma. La validación del logotipo es positiva contando con una correspondencia adecuada con la empresa especificada. La vigencia se confirma como válida dado que la fecha de emisión está dentro del rango especificado, además existe un número de póliza. En conclusión, todos los criterios validados han sido superados exitosamente."

# Notas

- Asegúrate de considerar cada aspecto por separado para identificar cualquier posible error y documentar estos hallazgos en el veredicto final, basandote en el veredicto de las páginas individuales {pages_verdicts}. 
- Este proceso ayuda a construir una validación robusta y comprensible del documento evaluado."""

FINAL_VERDICTO_PROMPT = """ 
Analisa solo la pagina donde se encontro a la persona asegurada {page_diagnosis}, luego genera un veredicto final en base al veredicto de esta hoja {pages_verdicts}. El veredicto debe seguir los siguientes pasos.

# Pasos

1. **Validación de firma:**
   - Verifica si existe al menos una firma en el documento {total_found_signatures}. Si es así, la firma es válida{signature_diagnosis}.
    - Si la firma ya existe en una pagina, entonces se considera valida.
2. **Validación del logotipo:**
   - revisa toda la información relacionada con el logotipo y la empresa para confirmar la validez del logotipo {logo_diagnosis}.

3. **Validación de vigencia:**
   - revisa solo el veredicto de la pagina donde se econtro a la persona asegurada {page_diagnosis}, para confirmar la validez de la vigencia {pages_verdicts}
4. **Validación de persona:**
   - revisa los veredictos de las páginas individuales {pages_verdicts}, es suficiente para un analisis favorable, con que unos de los veredictos sea positivo, se considera valido.
   - Si ecuntras una persona asegurada, en al menos una pagina, entonces se considera valida !!!.
   - Si Una pagina ya tiene un veredicto de persona asegurada, entonces no es necesario volver a verificar

5. **Compilar veredicto final:**
   - Integra los resultados de las validaciones de firma, logotipo, vigencia, número de póliza, y persona asegurada.
   - Genera un estatus para cada categoría de la revisión en el campo details, con la siguiente estructura: `logo_validation_passed`, `signature_validation_passed`, `validity_validation_passed`, `policy_validation_passed`, `person_validation_passed`.

# Formato de Salida

Estructura el veredicto final como un párrafo que incluya la decisión de validez y las razones que apoyan cada criterio. Puede ser en un formato narrativo, proporcionando claridad y justificación de cada área evaluada.

**Salida:**

"La validación del documento indica que: la firma es válida ya que se detectó al menos una firma. La validación del logotipo es positiva contando con una correspondencia adecuada con la empresa especificada {enterprise}. La vigencia solo se analisara la pagina donde se encontro a la persona, además existe un número de póliza, y la persona asegurada coincide con el nombre de la persona asegurada {person}. En conclusión, todos los criterios validados han sido superados exitosamente."

# Notas

- Este proceso ayuda a construir una validación robusta y comprensible del documento evaluado.
- No olvides generar un estatus para cada categoria de la revision en el campo details, con la siguiente estructura: `logo_validation_passed`, `signature_validation_passed`, `validity_validation_passed`, `policy_validation_passed`, `person_validation_passed`.
"""