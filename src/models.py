from pydantic import BaseModel
from datetime import datetime, date
from typing import Optional, List, Dict, Any
from decimal import Decimal
from enum import Enum

class ProcessingStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class DocumentType(str, Enum):
    CAPITAL_CALL = "capital_call"
    DISTRIBUTION = "distribution"
    VALUATION = "valuation"
    QUARTERLY_UPDATE = "quarterly_update"
    UNKNOWN = "unknown"

class DocumentResponse(BaseModel):
    id: str
    original_filename: str
    document_type: Optional[DocumentType] = None
    processing_status: ProcessingStatus
    classification_confidence: Optional[float] = None
    created_at: datetime

class DocumentSummary(BaseModel):
    id: str
    original_filename: str
    document_type: Optional[DocumentType] = None
    processing_status: ProcessingStatus
    classification_confidence: Optional[float] = None
    created_at: datetime

class CapitalCallResponse(BaseModel):
    id: str
    document_id: str
    fund_id: str
    call_date: date
    lp_id: str
    call_amount: Decimal
    currency: str
    call_number: Optional[int] = None
    extraction_confidence: Optional[float] = None
    created_at: datetime

class DistributionResponse(BaseModel):
    id: str
    document_id: str
    fund_id: str
    distribution_date: date
    lp_id: str
    distribution_amount: Decimal
    distribution_type: str  # ROC or CI
    currency: str
    extraction_confidence: Optional[float] = None
    created_at: datetime

class ValuationResponse(BaseModel):
    id: str
    document_id: str
    valuation_date: date
    methodology: Optional[str] = None
    discount_rate: Optional[Decimal] = None
    multiples: Optional[Dict[str, Any]] = None
    final_valuation: Optional[Decimal] = None
    currency: str
    extraction_confidence: Optional[float] = None
    created_at: datetime
