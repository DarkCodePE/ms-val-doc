from sqlalchemy import Column, String, Integer, DateTime, Date, JSON, Boolean
from datetime import datetime
from uuid import uuid4
from pydantic import BaseModel, EmailStr, HttpUrl
from typing import List, Optional
from app.config.base import Base


# Modelo para persistencia de datos validados en la base de datos
class DocumentValidation(Base):
    __tablename__ = "document_validations"
    __table_args__ = {"schema": "public"}

    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    document_number = Column(String, nullable=False)  # Número de la constancia
    insurance_provider = Column(String, nullable=False)  # Aseguradora (e.g., MAPFRE)
    issue_date = Column(DateTime, default=datetime.utcnow)  # Fecha de emisión
    validity_start = Column(Date, nullable=False)  # Fecha de inicio de vigencia
    validity_end = Column(Date, nullable=False)  # Fecha de fin de vigencia
    insured_list = Column(JSON, nullable=True)  # Lista de asegurados (JSON)
    has_signature = Column(Boolean, nullable=False)  # Indicador de firma
    is_valid = Column(Boolean, nullable=False)  # Indicador de validez del documento
    validity_reason = Column(String, nullable=True)  # Razonamiento de la validez/invalidez
    created_at = Column(DateTime, default=datetime.utcnow)


class DocumentValidationResponse:
    pass