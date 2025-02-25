
DOCUMENT_PROCESSOR = """Valida la informacion del documento para la razon social {enterprise} y analisa la información clave del siguiente documento {document_data}, centrándote en las siguientes prioridades: vigencia, empresa, póliza, logo, y firma.
**Input Document Data:**
"document_data":  {document_data}

# Steps

1. **Comprender el Documento**: Lee completamente el documento para entender su contenido y estructura.
2. **Buscar la Vigencia**: Identifica todas las menciones de fechas o periodos temporales que indiquen la vigencia del documento.
3. **Fecha de emisión**: Busca la fecha de emisión del documento, si se encuentra, normalmente se encuentra en la parte superior del documento, pero puede estar en cualquier lugar.
3. **Empresa**: Busca el nombre de la empresa que emite el documento, tienes que guardar el nombre de la empresa en el campo "company", difiere del nombre de la razón social {enterprise}, y el igual a logotipo.
4. **Identificar la Empresa**: Localiza cualquier mención del nombre de una empresa que pudiera ser responsable del documento.
5. **Encontrar Información de la Póliza**: Busca números o identificadores que se mencionen junto a las palabras 'póliza' o 'Póliza de Pensiones'.
6. **Buscar Personas**: con el numero de poliza, busca el nombre de la persona asegurada {person} en la lista de asegurados, una ves encontrada, debes guardar el nombre de la persona asegurada en el campo "person_by_policy", su poliza en "policy_number" y la empresa en "company".

# Output Format

Produce una respuesta estructurada en formato JSON con las siguientes claves:
- "validity": [rango_fechas_o_null],
- "start_date_validity": [fecha_inicio_o_null],
- "end_date_validity": [fecha_fin_o_null],
- "company": [nombre_empresa_o_rason_social_o_null],
- "policy_number": [numeros_de_poliza_o_null],
- "date_of_issuance": fecha_de_emision_o_null,
- "person_by_policy": [person_by_policy_o_null],
# Notes

- Indica la ausencia de alguno de los elementos requeridos con el valor null si dicha información no está claramente especificada en el documento.
- La exactitud en la extracción de información y la claridad de los términos es prioritaria para asegurar la utilidad del resultado.
- Para la busqueda de personas aseguradas, se debe buscar el nombre de la persona asegurada con el numero de poliza en la lista de asegurados, si no se encuentra, se debe indicar null.
"""

DOCUMENT_PROCESSOR_DNI = """Valida la informacion del documento para la razon social {enterprise} y analisa la información clave del siguiente documento {document_data}, centrándote en las siguientes prioridades: vigencia, empresa, póliza, logo, y firma.
**Input Document Data:**
"document_data":  {document_data}

# Steps

1. **Comprender el Documento**: Lee completamente el documento para entender su contenido y estructura.
2. **Buscar la Vigencia**: Identifica todas las menciones de fechas o periodos temporales que indiquen la vigencia del documento.
3. **Fecha de emisión**: Busca la fecha de emisión del documento, si se encuentra, normalmente se encuentra en la parte superior del documento, pero puede estar en cualquier lugar.
3. **Empresa**: Busca el nombre de la empresa que emite el documento, tienes que guardar el nombre de la empresa en el campo "company", difiere del nombre de la razón social {enterprise}, y el igual a logotipo.
4. **Identificar la Empresa**: Localiza cualquier mención del nombre de una empresa que pudiera ser responsable del documento.
5. **Encontrar Información de la Póliza**: Busca números o identificadores que se mencionen junto a las palabras 'póliza' o 'Póliza de Pensiones'.
6. **Buscar Persona por DNI**: 
   - Estás recibiendo un DNI: "{person_identifier}".
   - Busca este DNI en la lista de asegurados dentro del documento.
   - Una vez encontrada la persona asociada a este DNI, guarda sus datos en el campo "person_by_policy".

# Output Format

Produce una respuesta estructurada en formato JSON con las siguientes claves:
- "validity": [rango_fechas_o_null],
- "start_date_validity": [fecha_inicio_o_null],
- "end_date_validity": [fecha_fin_o_null],
- "company": [nombre_empresa_o_rason_social_o_null],
- "policy_number": [numeros_de_poliza_o_null],
- "date_of_issuance": fecha_de_emision_o_null,
- "person_by_policy": [person_by_policy_o_null],

# Notes

- Indica la ausencia de alguno de los elementos requeridos con el valor null si dicha información no está claramente especificada en el documento.
- La exactitud en la extracción de información y la claridad de los términos es prioritaria para asegurar la utilidad del resultado.
- Para la búsqueda de personas aseguradas, independientemente de si buscas por nombre o DNI, debes proporcionar toda la información asociada a la persona encontrada.
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
    - Analiza el nombre de la persona asegurada extraído de esta página: {person}.
   - Compara este nombre con el nombre de la persona asegurada registrado en la póliza: {page_content}.
   - **Criterios de Coincidencia Flexible:**
     - **Nombre y Apellido Principal:** Verifica si al menos un nombre y un apellido presentes en {person} coinciden con al menos un nombre y un apellido en {page_content}.  Considera el nombre y apellido principal como los elementos clave para la coincidencia.
     - **Flexibilidad en Variaciones:** Sé flexible con:
       - Mayúsculas y minúsculas (ignora la diferencia).
       - Comas, puntos, guiones y otros signos de puntuación en el nombre (ignóralos).
       - Iniciales y nombres abreviados (considera "J." como posible coincidencia con "Juan").
       - Pequeños errores de ortografía o tipeo (tolera errores leves).
       - Orden de los nombres (si el nombre y apellido principal son consistentes, el orden secundario no es crucial).
     - **Ejemplo de Coincidencia:** "JUAN PEREZ" se considera una coincidencia con "Perez, Juan Carlos", "Juan R. Perez", "Juan Pérez".
   - **Número de Póliza como Confirmación (Opcional):**  Verifica que el número de póliza extraído de la página ({policy_number}) coincida con el número de póliza asociado a la persona asegurada (implícito en {page_content}).  Si hay coincidencia en el número de póliza, úsalo como una confirmación adicional de la validación de persona, pero la validación principal debe basarse en la coincidencia del nombre.
   - **Resultado:** Determina si la validación de la persona asegurada es exitosa basándote en la coincidencia flexible del nombre.  En el veredicto, explica brevemente cómo se realizó la comparación del nombre y si se encontró una coincidencia flexible.
   
2. **Validación de Poliza:**
   - Verifica la existencia de al menos un número de póliza {policy_number}.
   
3. **Validación de Vigencia:**
   - Considera los resultados de las validaciones de vigencia pre-calculadas:
     - `validation_passed`: Indica si la fecha de emisión es válida respecto a la fecha de fin de vigencia. Valor: {validation_passed}.
     - `validity_passed`: Indica si la fecha de fin de vigencia es válida respecto a una fecha de referencia. Valor: {validity_passed}.
   - **Resultado:** Determina si la validación de vigencia es exitosa basándote en que **ambos** `validation_passed` y `validity_passed` sean verdaderos.
   
4. **Compilar veredicto final:**
   - Integra los resultados de las número de póliza y persona asegurada.
   - Genera un estatus para cada categoría de la revisión: `validity_validation_passed`, `policy_validation_passed`, `person_validation_passed`.
   - validity_validation_passed: Será **verdadero** si **ambos** `validation_passed` es {validation_passed} y `validity_passed` es {validity_passed} son verdaderos. Si es **falso**, explica **cuál de los dos criterios no se cumple** (o ambos) y por qué.
   - policy_validation_passed: si existe al menos un número de póliza {policy_number}. Debes explicar el criterio que no se cumple, en caso de que no se cumpla.
   - person_validation_passed:* Verifica si al menos un nombre y un apellido presentes en {person} coinciden con al menos un nombre y un apellido en {page_content}.  Considera el nombre y apellido principal como los elementos clave para la coincidencia.
     - **Flexibilidad en Variaciones:** Sé flexible con:
       - Mayúsculas y minúsculas (ignora la diferencia).
       - Comas, puntos, guiones y otros signos de puntuación en el nombre (ignóralos).
       - Iniciales y nombres abreviados (considera "J." como posible coincidencia con "Juan").
       - Pequeños errores de ortografía o tipeo (tolera errores leves).
       - Orden de los nombres (si el nombre y apellido principal son consistentes, el orden secundario no es crucial).


# Notas
- Asegúrate de considerar cada aspecto por separado  validity_validation_passed, policy_validation_passed, person_validation_passed, si alguno de estos aspectos no es valido, centra el veredicto en ese aspecto.
"""


FINAL_VERDICTO_PROMPT = """ 
Analisa solo la pagina donde se encontro a la persona asegurada {page_diagnosis}, luego genera un veredicto final en base al veredicto de esta hoja {pages_verdicts}. El veredicto debe seguir los siguientes pasos.

# Pasos

1. **Validación de firma:**
    - Verifica si existe al menos una firma en el documento {logo_diagnosis}. Si es asi el veredicto es positivo.
    
2. **Validación del logotipo:**
   - revisa toda la información relacionada con el logotipo y la empresa para confirmar la validez del logotipo {logo_diagnosis}.

3. **Validación de vigencia:**
   - revisa solo el veredicto de la pagina donde se encontro a la persona asegurada {page_diagnosis}, para confirmar la validez de la vigencia {pages_verdicts}
   
4. **Validación de persona:**
   - Revisa los veredictos de persona asegurada de todas las páginas {pages_verdicts}.
   - **Para cada página, considera la validación de persona como positiva si se encuentra el nombre de la persona asegurada {page_diagnosis} o una variación razonable del mismo.**
   - **Sé flexible con:**
     - Comas y otros signos de puntuación en el nombre.
     - Iniciales y nombres abreviados.
     - Pequeños errores de ortografía o tipeo.
     - Orden de los nombres (si es consistente el nombre principal).
   - **Criterio General:**  Si al menos **una** página tiene un veredicto positivo de persona asegurada, considera la validación de persona como **válida en general**.
   - **Resultado:** Si la persona asegurada se valida en al menos una página, `person_validation_passed` es verdadero. De lo contrario, es falso.


5. **Compilar veredicto final:**
   - Integra los resultados de las validaciones de firma, logotipo, vigencia, número de póliza, y persona asegurada.
   - Genera un estatus para cada categoría de la revisión en el campo details, con la siguiente estructura: `logo_validation_passed`, `signature_validation_passed`, `validity_validation_passed`, `policy_validation_passed`, `person_validation_passed`.

# Formato de Salida

Estructura el veredicto final como un párrafo que incluya la decisión de validez y las razones que apoyan cada criterio. Puede ser en un formato narrativo, proporcionando claridad y justificación de cada área evaluada.

**verdict:**

Debe clasificar el documento como válido, observado o no válido. Siguiendo los siguientes criterios:

- La primera parte valida el `{logo_diagnosis}` resaltando datos del logotipo y la firma. Si esta primera parte de validación es negativa, el documento estará observado.
- La segunda parte evalúa `{pages_verdicts}` para validar vigencia, número de póliza y persona asegurada.Si esta segunda parte de validación es negativa, el documento sera catalogado como no válido.
- Si ambas partes son positivas, el documento es válido.

# Notas
- El veredicto final debe estar en español, debe ser claro y conciso !!!.
- Es suficiente con encontrar un firma para que signature_validation_passed sea verdadero !!!.
- Este proceso ayuda a construir una validación robusta y comprensible del documento evaluado.
- No olvides generar un estatus para cada categoria de la revision en el campo details, con la siguiente estructura: `logo_validation_passed`, `signature_validation_passed`, `validity_validation_passed`, `policy_validation_passed`, `person_validation_passed`.
"""
