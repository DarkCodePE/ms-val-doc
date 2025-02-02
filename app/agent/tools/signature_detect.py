import cv2
import os
import numpy as np
import time
import math
import logging
from typing import List, Tuple

# Configuración del logger
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Definición del tipo para un rectángulo: (left, top, width, height)
Rectangle = Tuple[int, int, int, int]

# Constantes para los umbrales (ajustables según necesidad)
MIN_AREA_MULTIPLIER = 4
MAX_AREA_MULTIPLIER = 50
HORIZONTAL_LINE_HEIGHT_MULTIPLIER = 5
HORIZONTAL_LINE_WIDTH_MULTIPLIER = 30
VERTICAL_LINE_WIDTH_MULTIPLIER = 5
VERTICAL_LINE_HEIGHT_MULTIPLIER = 30
FOREGROUND_RATIO_THRESHOLD = 0.30


def binarize_image(image: np.ndarray) -> np.ndarray:
    """
    Convierte la imagen de entrada a una imagen binarizada usando el método de umbralización de Otsu.

    :param image: Imagen en formato BGR.
    :return: Imagen binarizada.
    """
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    # Se utiliza THRESH_BINARY_INV para que el primer plano (firma) sea blanco.
    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    return binary


def filter_candidate_components(stats: np.ndarray, binary_image: np.ndarray, median_area: float,
                                median_character_width: int) -> List[Rectangle]:
    """
    Filtra los componentes conectados basándose en el área, la relación de aspecto y el ratio de píxeles
    de primer plano para detectar candidatos a firma.

    :param stats: Estadísticas de los componentes conectados.
    :param binary_image: Imagen binarizada.
    :param median_area: Área mediana de los componentes (excluyendo el fondo).
    :param median_character_width: Ancho mediano estimado de los caracteres.
    :return: Lista de rectángulos (left, top, width, height) de candidatos a firma.
    """
    possible_signatures: List[Rectangle] = []
    min_area_threshold = median_area * MIN_AREA_MULTIPLIER
    max_area_threshold = median_area * MAX_AREA_MULTIPLIER

    num_labels = stats.shape[0]
    # Se itera sobre cada componente (excluyendo el fondo, índice 0)
    for i in range(1, num_labels):
        area = stats[i, cv2.CC_STAT_AREA]
        if not (min_area_threshold < area < max_area_threshold):
            continue

        left = stats[i, cv2.CC_STAT_LEFT]
        top = stats[i, cv2.CC_STAT_TOP]
        width = stats[i, cv2.CC_STAT_WIDTH]
        height = stats[i, cv2.CC_STAT_HEIGHT]

        # Filtrar líneas horizontales (probablemente no sean firmas)
        if height < median_character_width * HORIZONTAL_LINE_HEIGHT_MULTIPLIER and \
                width > median_character_width * HORIZONTAL_LINE_WIDTH_MULTIPLIER:
            logger.debug(f"Descartando línea horizontal en componente {i} (w={width}, h={height})")
            continue

        # Filtrar líneas verticales
        if width < median_character_width * VERTICAL_LINE_WIDTH_MULTIPLIER and \
                height > median_character_width * VERTICAL_LINE_HEIGHT_MULTIPLIER:
            logger.debug(f"Descartando línea vertical en componente {i} (w={width}, h={height})")
            continue

        # Calcular el ratio de píxeles de primer plano en el ROI (la firma es blanca)
        roi = binary_image[top:top + height, left:left + width]
        foreground_pixels = cv2.countNonZero(roi)
        total_pixels = width * height
        ratio = foreground_pixels / total_pixels

        logger.debug(f"Candidato {i}: área={area}, ratio de píxeles={ratio:.2f}")

        # Descartar el candidato si el ratio es demasiado alto (posible logo u otra región densa)
        if ratio > FOREGROUND_RATIO_THRESHOLD:
            logger.debug(f"Descartando candidato {i} por ratio de píxeles alto ({ratio:.2f})")
            continue

        possible_signatures.append((left, top, width, height))

    return possible_signatures


def merge_nearby_rectangles(rectangles: List[Rectangle], nearness: int) -> List[Rectangle]:
    """
    Fusiona rectángulos que estén cerca entre sí dentro de un umbral especificado.

    :param rectangles: Lista de rectángulos (left, top, width, height).
    :param nearness: Distancia máxima para considerar dos rectángulos como cercanos.
    :return: Lista de rectángulos fusionados.
    """

    def is_near(rect1: Rectangle, rect2: Rectangle) -> bool:
        left1, top1, width1, height1 = rect1
        left2, top2, width2, height2 = rect2
        right1, bottom1 = left1 + width1, top1 + height1
        right2, bottom2 = left2 + width2, top2 + height2
        return not (right1 < left2 - nearness or left1 > right2 + nearness or
                    bottom1 < top2 - nearness or top1 > bottom2 + nearness)

    def merge(rect1: Rectangle, rect2: Rectangle) -> Rectangle:
        left1, top1, width1, height1 = rect1
        left2, top2, width2, height2 = rect2
        right1, bottom1 = left1 + width1, top1 + height1
        right2, bottom2 = left2 + width2, top2 + height2
        min_left = min(left1, left2)
        min_top = min(top1, top2)
        max_right = max(right1, right2)
        max_bottom = max(bottom1, bottom2)
        return (min_left, min_top, max_right - min_left, max_bottom - min_top)

    merged = []
    # Se realiza una fusión iterativa: se intenta fusionar rectángulos cercanos hasta que no se puedan fusionar más.
    while rectangles:
        current = rectangles.pop(0)
        merged_with_current = False

        # Intentar fusionar con cualquier rectángulo ya fusionado
        for i, other in enumerate(merged):
            if is_near(current, other):
                merged[i] = merge(current, other)
                merged_with_current = True
                break

        if merged_with_current:
            continue

        # Intentar fusionar con los rectángulos restantes
        j = 0
        while j < len(rectangles):
            if is_near(current, rectangles[j]):
                current = merge(current, rectangles.pop(j))
                # Reiniciar el escaneo ya que 'current' ha cambiado
                j = 0
            else:
                j += 1

        merged.append(current)

    return merged


def find_signature_bounding_boxes(image: np.ndarray) -> List[Rectangle]:
    """
    Detecta las cajas delimitadoras de la firma en la imagen dada.

    :param image: Imagen en formato BGR.
    :return: Lista de rectángulos (left, top, width, height) de cada firma detectada.
    """
    start_time = time.time()

    if image is None:
        raise ValueError("No se ha proporcionado una imagen válida.")

    binary_image = binarize_image(image)

    # Encontrar componentes conectados
    num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(
        binary_image, connectivity=8, ltype=cv2.CV_32S
    )

    # Calcular el área mediana de los componentes (excluyendo el fondo)
    if num_labels <= 1:
        return []
    areas = stats[1:, cv2.CC_STAT_AREA]
    median_area = float(np.median(areas))
    median_character_width = int(math.sqrt(median_area))
    logger.debug(f"Área mediana: {median_area}, ancho mediano estimado: {median_character_width}")

    # Filtrar componentes candidatas basándose en los umbrales definidos
    possible_signatures = filter_candidate_components(stats, binary_image, median_area, median_character_width)
    logger.info(f"Número de candidatos antes de fusionar: {len(possible_signatures)}")

    # Fusionar rectángulos cercanos
    nearness_threshold = median_character_width * 4
    merged_signatures = merge_nearby_rectangles(possible_signatures, nearness_threshold)
    logger.info(f"Número de candidatos después de fusionar: {len(merged_signatures)}")

    end_time = time.time()
    logger.info(f"Detección completada en {end_time - start_time:.2f} segundos.")

    return merged_signatures
