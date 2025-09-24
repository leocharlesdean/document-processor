import asyncio
import asyncpg
from typing import List, Dict, Optional, Any
from datetime import datetime, date
import json
import uuid
from src.config import settings

class DatabaseManager:
    def __init__(self):
        self.pool = None
    
    async def initialize(self):
        """Initialize database connection pool and create tables"""
        self.pool = await asyncpg.create_pool(settings.DATABASE_URL)
        await self.create_tables()
    
    async def close(self):
        """Close database connections"""
        if self.pool:
            await self.pool.close()
    
    async def create_tables(self):
        """Create database tables if they don't exist"""
        async with self.pool.acquire() as conn:
            await conn.execute("""
                CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
                
                CREATE TABLE IF NOT EXISTS documents (
                    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                    original_filename VARCHAR(255) NOT NULL,
                    file_path TEXT NOT NULL,
                    file_size BIGINT NOT NULL,
                    content_hash VARCHAR(64),
                    document_type VARCHAR(50),
                    classification_confidence DECIMAL(3,2),
                    processing_status VARCHAR(20) DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                
                CREATE TABLE IF NOT EXISTS capital_calls (
                    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                    document_id UUID REFERENCES documents(id),
                    fund_id VARCHAR(50) NOT NULL,
                    call_date DATE NOT NULL,
                    lp_id VARCHAR(50) NOT NULL,
                    call_amount DECIMAL(15,2) NOT NULL,
                    currency VARCHAR(3) NOT NULL DEFAULT 'USD',
                    call_number INTEGER,
                    extraction_confidence DECIMAL(3,2),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                
                CREATE TABLE IF NOT EXISTS distributions (
                    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                    document_id UUID REFERENCES documents(id),
                    fund_id VARCHAR(50) NOT NULL,
                    distribution_date DATE NOT NULL,
                    lp_id VARCHAR(50) NOT NULL,
                    distribution_amount DECIMAL(15,2) NOT NULL,
                    distribution_type VARCHAR(10) CHECK (distribution_type IN ('ROC', 'CI')),
                    currency VARCHAR(3) NOT NULL DEFAULT 'USD',
                    extraction_confidence DECIMAL(3,2),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                
                CREATE TABLE IF NOT EXISTS valuations (
                    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                    document_id UUID REFERENCES documents(id),
                    valuation_date DATE NOT NULL,
                    methodology TEXT,
                    discount_rate DECIMAL(5,4),
                    multiples JSONB,
                    final_valuation DECIMAL(15,2),
                    currency VARCHAR(3) NOT NULL DEFAULT 'USD',
                    extraction_confidence DECIMAL(3,2),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                
                CREATE TABLE IF NOT EXISTS processing_logs (
                    id SERIAL PRIMARY KEY,
                    document_id UUID REFERENCES documents(id),
                    stage VARCHAR(50) NOT NULL,
                    status VARCHAR(20) NOT NULL,
                    message TEXT,
                    execution_time_ms INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                
                CREATE INDEX IF NOT EXISTS idx_documents_type ON documents(document_type);
                CREATE INDEX IF NOT EXISTS idx_documents_status ON documents(processing_status);
                CREATE INDEX IF NOT EXISTS idx_capital_calls_fund_date ON capital_calls(fund_id, call_date);
                CREATE INDEX IF NOT EXISTS idx_distributions_fund_date ON distributions(fund_id, distribution_date);
            """)
    
    async def create_document(self, document_id: str, original_filename: str, 
                            file_path: str, file_size: int) -> Dict[str, Any]:
        """Create a new document record"""
        async with self.pool.acquire() as conn:
            result = await conn.fetchrow("""
                INSERT INTO documents (id, original_filename, file_path, file_size)
                VALUES ($1, $2, $3, $4)
                RETURNING *
            """, uuid.UUID(document_id), original_filename, file_path, file_size)
            return dict(result)
    
    async def update_document_status(self, document_id: str, status: str, 
                                   document_type: Optional[str] = None,
                                   confidence: Optional[float] = None):
        """Update document processing status"""
        async with self.pool.acquire() as conn:
            if document_type and confidence is not None:
                await conn.execute("""
                    UPDATE documents 
                    SET processing_status = $2, document_type = $3, 
                        classification_confidence = $4, updated_at = CURRENT_TIMESTAMP
                    WHERE id = $1
                """, uuid.UUID(document_id), status, document_type, confidence)
            else:
                await conn.execute("""
                    UPDATE documents 
                    SET processing_status = $2, updated_at = CURRENT_TIMESTAMP
                    WHERE id = $1
                """, uuid.UUID(document_id), status)
    
    async def get_document(self, document_id: str) -> Optional[Dict[str, Any]]:
        """Get document by ID"""
        async with self.pool.acquire() as conn:
            result = await conn.fetchrow(
                "SELECT * FROM documents WHERE id = $1", 
                uuid.UUID(document_id)
            )
            return dict(result) if result else None
    
    async def get_documents(self, document_type: Optional[str] = None,
                          status: Optional[str] = None,
                          limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        """Get documents with optional filtering"""
        query = "SELECT * FROM documents WHERE 1=1"
        params = []
        
        if document_type:
            query += " AND document_type = $" + str(len(params) + 1)
            params.append(document_type)
        
        if status:
            query += " AND processing_status = $" + str(len(params) + 1)
            params.append(status)
        
        query += " ORDER BY created_at DESC LIMIT $" + str(len(params) + 1)
        params.append(limit)
        
        query += " OFFSET $" + str(len(params) + 1)
        params.append(offset)
        
        async with self.pool.acquire() as conn:
            results = await conn.fetch(query, *params)
            return [dict(r) for r in results]
    
    async def create_capital_call(self, document_id: str, data: Dict[str, Any]):
        """Create capital call record"""
        async with self.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO capital_calls 
                (document_id, fund_id, call_date, lp_id, call_amount, currency, 
                 call_number, extraction_confidence)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            """, uuid.UUID(document_id), data['fund_id'], data['call_date'], 
                data['lp_id'], data['call_amount'], data.get('currency', 'USD'),
                data.get('call_number'), data.get('confidence'))
    
    async def create_distribution(self, document_id: str, data: Dict[str, Any]):
        """Create distribution record"""
        async with self.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO distributions 
                (document_id, fund_id, distribution_date, lp_id, distribution_amount, 
                 distribution_type, currency, extraction_confidence)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            """, uuid.UUID(document_id), data['fund_id'], data['distribution_date'],
                data['lp_id'], data['distribution_amount'], data['distribution_type'],
                data.get('currency', 'USD'), data.get('confidence'))
    
    async def create_valuation(self, document_id: str, data: Dict[str, Any]):
        """Create valuation record"""
        async with self.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO valuations 
                (document_id, valuation_date, methodology, discount_rate, 
                 multiples, final_valuation, currency, extraction_confidence)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            """, uuid.UUID(document_id), data['valuation_date'], data.get('methodology'),
                data.get('discount_rate'), json.dumps(data.get('multiples', {})),
                data.get('final_valuation'), data.get('currency', 'USD'), data.get('confidence'))
    
    async def get_capital_calls(self, fund_id: Optional[str] = None,
                              start_date: Optional[str] = None,
                              end_date: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get capital calls with optional filtering"""
        query = "SELECT * FROM capital_calls WHERE 1=1"
        params = []
        
        if fund_id:
            query += " AND fund_id = $" + str(len(params) + 1)
            params.append(fund_id)
        
        if start_date:
            query += " AND call_date >= $" + str(len(params) + 1)
            params.append(start_date)
            
        if end_date:
            query += " AND call_date <= $" + str(len(params) + 1)
            params.append(end_date)
        
        query += " ORDER BY call_date DESC"
        
        async with self.pool.acquire() as conn:
            results = await conn.fetch(query, *params)
            return [dict(r) for r in results]
    
    async def get_distributions(self, fund_id: Optional[str] = None,
                              start_date: Optional[str] = None,
                              end_date: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get distributions with optional filtering"""
        query = "SELECT * FROM distributions WHERE 1=1"
        params = []
        
        if fund_id:
            query += " AND fund_id = $" + str(len(params) + 1)
            params.append(fund_id)
        
        if start_date:
            query += " AND distribution_date >= $" + str(len(params) + 1)
            params.append(start_date)
            
        if end_date:
            query += " AND distribution_date <= $" + str(len(params) + 1)
            params.append(end_date)
        
        query += " ORDER BY distribution_date DESC"
        
        async with self.pool.acquire() as conn:
            results = await conn.fetch(query, *params)
            return [dict(r) for r in results]
    
    async def get_capital_call_by_document(self, document_id: str) -> Optional[Dict[str, Any]]:
        """Get capital call by document ID"""
        async with self.pool.acquire() as conn:
            result = await conn.fetchrow(
                "SELECT * FROM capital_calls WHERE document_id = $1",
                uuid.UUID(document_id)
            )
            return dict(result) if result else None
    
    async def get_distribution_by_document(self, document_id: str) -> Optional[Dict[str, Any]]:
        """Get distribution by document ID"""
        async with self.pool.acquire() as conn:
            result = await conn.fetchrow(
                "SELECT * FROM distributions WHERE document_id = $1",
                uuid.UUID(document_id)
            )
            return dict(result) if result else None
    
    async def get_valuation_by_document(self, document_id: str) -> Optional[Dict[str, Any]]:
        """Get valuation by document ID"""
        async with self.pool.acquire() as conn:
            result = await conn.fetchrow(
                "SELECT * FROM valuations WHERE document_id = $1",
                uuid.UUID(document_id)
            )
            return dict(result) if result else None
    
    async def log_processing_step(self, document_id: str, stage: str, 
                                status: str, message: Optional[str] = None,
                                execution_time_ms: Optional[int] = None):
        """Log processing step"""
        async with self.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO processing_logs 
                (document_id, stage, status, message, execution_time_ms)
                VALUES ($1, $2, $3, $4, $5)
            """, uuid.UUID(document_id), stage, status, message, execution_time_ms)
    
    async def get_dashboard_analytics(self) -> Dict[str, Any]:
        """Get dashboard analytics data"""
        async with self.pool.acquire() as conn:
            # Total documents by type
            doc_types = await conn.fetch("""
                SELECT document_type, COUNT(*) as count 
                FROM documents 
                WHERE document_type IS NOT NULL
                GROUP BY document_type
            """)
            
            # Processing status distribution
            status_dist = await conn.fetch("""
                SELECT processing_status, COUNT(*) as count 
                FROM documents 
                GROUP BY processing_status
            """)
            
            # Recent activity
            recent_docs = await conn.fetch("""
                SELECT COUNT(*) as count 
                FROM documents 
                WHERE created_at >= NOW() - INTERVAL '24 hours'
            """)
            
            # Total amounts by fund
            fund_amounts = await conn.fetch("""
                SELECT 
                    cc.fund_id,
                    SUM(cc.call_amount) as total_calls,
                    COUNT(cc.id) as call_count
                FROM capital_calls cc
                GROUP BY cc.fund_id
                ORDER BY total_calls DESC
                LIMIT 10
            """)
            
            return {
                "document_types": [dict(r) for r in doc_types],
                "processing_status": [dict(r) for r in status_dist],
                "recent_documents": dict(recent_docs[0])["count"] if recent_docs else 0,
                "fund_summary": [dict(r) for r in fund_amounts]
            }