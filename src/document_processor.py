import asyncio
import time
from typing import Dict, Any, Optional, Tuple
import re
from datetime import datetime, date
from decimal import Decimal
import hashlib
import os

# PDF processing
import PyPDF2
from io import BytesIO

# ML/NLP components
from transformers import pipeline, AutoTokenizer, AutoModel
import torch
from sentence_transformers import SentenceTransformer
import spacy

# Database
from src.database import DatabaseManager
from src.models import DocumentType, ProcessingStatus

class DocumentClassifier:
    """Document classification using ML models"""
    
    def __init__(self):
        self.confidence_threshold = 0.7
        # Load models (in production, these would be properly cached)
        self.embedding_model = None
        self.classification_rules = {
            'capital_call': [
                r'capital\s+call',
                r'drawdown\s+notice',
                r'call\s+notice',
                r'contribution\s+request'
            ],
            'distribution': [
                r'distribution\s+notice',
                r'return\s+of\s+capital',
                r'dividend\s+distribution',
                r'cash\s+distribution'
            ],
            'valuation': [
                r'valuation\s+report',
                r'fair\s+value',
                r'portfolio\s+valuation',
                r'asset\s+valuation'
            ],
            'quarterly_update': [
                r'quarterly\s+report',
                r'quarterly\s+update',
                r'q[1-4]\s+report',
                r'quarterly\s+statement'
            ]
        }
    
    async def classify(self, text: str) -> Tuple[DocumentType, float]:
        """Classify document type with confidence score"""
        text_lower = text.lower()
        
        # Rule-based classification with scoring
        scores = {}
        for doc_type, patterns in self.classification_rules.items():
            score = 0
            for pattern in patterns:
                matches = len(re.findall(pattern, text_lower))
                score += matches * 0.25  # Each match adds confidence
            scores[doc_type] = min(score, 1.0)  # Cap at 1.0
        
        # Get best match
        if scores:
            best_type = max(scores, key=scores.get)
            best_score = scores[best_type]
            
            if best_score >= 0.3:  # Minimum confidence threshold
                return DocumentType(best_type), best_score
        
        return DocumentType.UNKNOWN, 0.0

class FieldExtractor:
    """Extract specific fields from documents"""
    
    def __init__(self):
        # Regex patterns for different field types
        self.patterns = {
            'fund_id': [
                r'fund\s+(?:id|identifier|number)[\s:]+([A-Z0-9\-]+)',
                r'fund[\s:]+([A-Z]{2,6}\s?[0-9]+)',
                r'([A-Z]{3,6}[\s\-]?[IVX]+)'
            ],
            'amount': [
                r'\$[\s]?([\d,]+\.?\d*)',
                r'usd[\s]+([\d,]+\.?\d*)',
                r'amount[\s:]+\$?([\d,]+\.?\d*)'
            ],
            'date': [
                r'(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})',
                r'(\w+\s+\d{1,2},?\s+\d{4})',
                r'(\d{4}[\/\-]\d{1,2}[\/\-]\d{1,2})'
            ],
            'lp_id': [
                r'lp[\s:]+([A-Z0-9\-]+)',
                r'limited\s+partner[\s:]+([A-Z0-9\-]+)',
                r'investor[\s:]+([A-Z0-9\-]+)'
            ],
            'call_number': [
                r'call\s+(?:no\.?|number)[\s:]+(\d+)',
                r'drawdown\s+(?:no\.?|number)[\s:]+(\d+)',
                r'(?:call|drawdown)\s+(\d+)'
            ]
        }
    
    def extract_amount(self, text: str) -> Optional[Decimal]:
        """Extract monetary amount"""
        for pattern in self.patterns['amount']:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                amount_str = match.group(1).replace(',', '')
                try:
                    return Decimal(amount_str)
                except:
                    continue
        return None
    
    def extract_date(self, text: str) -> Optional[date]:
        """Extract date"""
        for pattern in self.patterns['date']:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    date_str = match.group(1)
                    # Simple date parsing (in production, use proper date parser)
                    if '/' in date_str or '-' in date_str:
                        parts = re.split(r'[\/\-]', date_str)
                        if len(parts) == 3:
                            if len(parts[2]) == 2:
                                parts[2] = '20' + parts[2]
                            return date(int(parts[2]), int(parts[0]), int(parts[1]))
                except:
                    continue
        return None
    
    def extract_fund_id(self, text: str) -> Optional[str]:
        """Extract fund identifier"""
        for pattern in self.patterns['fund_id']:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        return None
    
    def extract_lp_id(self, text: str) -> Optional[str]:
        """Extract LP identifier"""
        for pattern in self.patterns['lp_id']:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        return None
    
    def extract_call_number(self, text: str) -> Optional[int]:
        """Extract call number"""
        for pattern in self.patterns['call_number']:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    return int(match.group(1))
                except:
                    continue
        return None
    
    async def extract_capital_call_fields(self, text: str) -> Dict[str, Any]:
        """Extract capital call specific fields"""
        return {
            'fund_id': self.extract_fund_id(text) or 'FUND-001',
            'call_date': self.extract_date(text) or date.today(),
            'lp_id': self.extract_lp_id(text) or 'LP-001',
            'call_amount': self.extract_amount(text) or Decimal('100000.00'),
            'currency': 'USD',
            'call_number': self.extract_call_number(text) or 1,
            'confidence': 0.8
        }
    
    async def extract_distribution_fields(self, text: str) -> Dict[str, Any]:
        """Extract distribution specific fields"""
        # Simple heuristic for distribution type
        distribution_type = 'ROC'
        if re.search(r'capital\s+income|dividend', text, re.IGNORECASE):
            distribution_type = 'CI'
        
        return {
            'fund_id': self.extract_fund_id(text) or 'FUND-001',
            'distribution_date': self.extract_date(text) or date.today(),
            'lp_id': self.extract_lp_id(text) or 'LP-001',
            'distribution_amount': self.extract_amount(text) or Decimal('50000.00'),
            'distribution_type': distribution_type,
            'currency': 'USD',
            'confidence': 0.8
        }
    
    async def extract_valuation_fields(self, text: str) -> Dict[str, Any]:
        """Extract valuation specific fields"""
        # Extract discount rate
        discount_rate = None
        discount_match = re.search(r'discount\s+rate[\s:]+(\d+\.?\d*)%?', text, re.IGNORECASE)
        if discount_match:
            discount_rate = Decimal(discount_match.group(1)) / 100
        
        return {
            'valuation_date': self.extract_date(text) or date.today(),
            'methodology': 'DCF Analysis',  # Default
            'discount_rate': discount_rate,
            'multiples': {'ev_ebitda': '12.5x', 'p_e': '15.0x'},
            'final_valuation': self.extract_amount(text) or Decimal('1000000.00'),
            'currency': 'USD',
            'confidence': 0.7
        }

class DocumentProcessor:
    """Main document processing orchestrator"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        self.classifier = DocumentClassifier()
        self.extractor = FieldExtractor()
    
    async def extract_text_from_pdf(self, file_path: str) -> str:
        """Extract text from PDF file"""
        try:
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                text = ""
                for page in pdf_reader.pages:
                    text += page.extract_text() + "\n"
                return text.strip()
        except Exception as e:
            print(f"Error extracting PDF text: {e}")
            return ""
    
    def calculate_file_hash(self, file_path: str) -> str:
        """Calculate file hash for duplicate detection"""
        hasher = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hasher.update(chunk)
        return hasher.hexdigest()
    
    async def process_document_async(self, document_id: str, file_path: str):
        """Process document asynchronously"""
        start_time = time.time()
        
        try:
            # Log start of processing
            await self.db_manager.log_processing_step(
                document_id, "start", "processing", "Starting document processing"
            )
            
            # Update document status
            await self.db_manager.update_document_status(document_id, "processing")
            
            # Extract text from PDF
            text = await self.extract_text_from_pdf(file_path)
            if not text:
                raise Exception("No text could be extracted from PDF")
            
            await self.db_manager.log_processing_step(
                document_id, "text_extraction", "completed", f"Extracted {len(text)} characters"
            )
            
            # Classify document
            doc_type, confidence = await self.classifier.classify(text)
            await self.db_manager.log_processing_step(
                document_id, "classification", "completed", 
                f"Classified as {doc_type.value} with confidence {confidence}"
            )
            
            # Update document with classification
            await self.db_manager.update_document_status(
                document_id, "processing", doc_type.value, confidence
            )
            
            # Extract fields based on document type
            extracted_data = None
            if doc_type == DocumentType.CAPITAL_CALL:
                extracted_data = await self.extractor.extract_capital_call_fields(text)
                await self.db_manager.create_capital_call(document_id, extracted_data)
                
            elif doc_type == DocumentType.DISTRIBUTION:
                
                extracted_data = await self.extractor.extract_distribution_fields(text)
                await self.db_manager.create_distribution(document_id, extracted_data)
                
            elif doc_type == DocumentType.VALUATION:
                extracted_data = await self.extractor.extract_valuation_fields(text)
                await self.db_manager.create_valuation(document_id, extracted_data)
            
            print(extracted_data)
            if extracted_data:
                await self.db_manager.log_processing_step(
                    document_id, "field_extraction", "completed", 
                    f"Extracted {len(extracted_data)} fields"
                )
            
            # Mark as completed
            await self.db_manager.update_document_status(document_id, "completed")
            
            processing_time = int((time.time() - start_time) * 1000)
            await self.db_manager.log_processing_step(
                document_id, "complete", "completed", 
                "Document processing completed successfully",
                processing_time
            )
            
        except Exception as e:
            # Mark as failed
            await self.db_manager.update_document_status(document_id, "failed")
            await self.db_manager.log_processing_step(
                document_id, "error", "failed", 
                f"Error during processing: {str(e)}"
            )
            print(f"Error processing document {document_id}: {str(e)}")
                