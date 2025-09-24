import os
from fastapi import FastAPI, File, UploadFile, HTTPException, BackgroundTasks, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
import uvicorn
from typing import List, Optional, Dict
import asyncio
from datetime import datetime
import uuid
import json

from src.database import DatabaseManager
from src.document_processor import DocumentProcessor
from src.models import (
    DocumentResponse, DocumentSummary, CapitalCallResponse, 
    DistributionResponse, ProcessingStatus
)
from src.config import settings

# Initialize FastAPI app
app = FastAPI(
    title="Alternative Investments Document Intelligence",
    description="AI-native platform for processing investment documents",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize components
db_manager = DatabaseManager()
document_processor = DocumentProcessor(db_manager)

@app.on_event("startup")
async def startup_event():
    """Initialize database and create tables"""
    await db_manager.initialize()

@app.on_event("shutdown")
async def shutdown_event():
    """Clean up database connections"""
    await db_manager.close()

# API Routes

@app.post("/api/v1/documents", response_model=DocumentResponse)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...)
):
    """Upload and process a document"""
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
    
    # Save file
    document_id = str(uuid.uuid4())
    file_path = f"uploads/{document_id}_{file.filename}"
    os.makedirs("uploads", exist_ok=True)
    
    with open(file_path, "wb") as buffer:
        content = await file.read()
        buffer.write(content)
    
    # Create database record
    document_record = await db_manager.create_document(
        document_id=document_id,
        original_filename=file.filename,
        file_path=file_path,
        file_size=len(content)
    )
    
    # Start background processing
    background_tasks.add_task(
        document_processor.process_document_async,
        document_id,
        file_path
    )
    
    return DocumentResponse(
        id=document_id,
        original_filename=file.filename,
        processing_status=ProcessingStatus.PROCESSING,
        created_at=document_record["created_at"]
    )

@app.get("/api/v1/documents", response_model=List[DocumentSummary])
async def list_documents(
    document_type: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0
):
    """List documents with optional filtering"""
    documents = await db_manager.get_documents(
        document_type=document_type,
        status=status,
        limit=limit,
        offset=offset
    )
    
    return [
        DocumentSummary(
            id=str(doc["id"]),
            original_filename=doc["original_filename"],
            document_type=doc["document_type"],
            processing_status=ProcessingStatus(doc["processing_status"]),
            classification_confidence=doc["classification_confidence"],
            created_at=doc["created_at"]
        )
        for doc in documents
    ]

@app.get("/api/v1/documents/{document_id}")
async def get_document(document_id: str):
    """Get document details with extracted data"""
    document = await db_manager.get_document(document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Get extracted data based on document type
    extracted_data = None
    if document["document_type"] == "capital_call":
        extracted_data = await db_manager.get_capital_call_by_document(document_id)
    elif document["document_type"] == "distribution":
        extracted_data = await db_manager.get_distribution_by_document(document_id)
    elif document["document_type"] == "valuation":
        extracted_data = await db_manager.get_valuation_by_document(document_id)
    
    return {
        "document": document,
        "extracted_data": extracted_data
    }

@app.post("/api/v1/documents/{document_id}/reprocess")
async def reprocess_document(document_id: str, background_tasks: BackgroundTasks):
    """Reprocess a document"""
    document = await db_manager.get_document(document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Update status to processing
    await db_manager.update_document_status(document_id, "processing")
    
    # Start background processing
    background_tasks.add_task(
        document_processor.process_document_async,
        document_id,
        document["file_path"]
    )
    
    return {"message": "Document reprocessing started"}

@app.get("/api/v1/capital-calls", response_model=List[CapitalCallResponse])
async def get_capital_calls(
    fund_id: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
):
    """Get capital calls with optional filtering"""
    capital_calls = await db_manager.get_capital_calls(
        fund_id=fund_id,
        start_date=start_date,
        end_date=end_date
    )
    
    return [
        CapitalCallResponse(**call) for call in capital_calls
    ]

@app.get("/api/v1/distributions", response_model=List[DistributionResponse])
async def get_distributions(
    fund_id: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
):
    """Get distributions with optional filtering"""
    distributions = await db_manager.get_distributions(
        fund_id=fund_id,
        start_date=start_date,
        end_date=end_date
    )
    
    return [
        DistributionResponse(**dist) for dist in distributions
    ]

@app.get("/api/v1/analytics/dashboard")
async def get_dashboard_analytics():
    """Get dashboard analytics"""
    return await db_manager.get_dashboard_analytics()

@app.get("/", response_class=HTMLResponse)
async def get_ui():
    """Enhanced UI with extracted data display"""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Document Intelligence Platform</title>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            * { box-sizing: border-box; margin: 0; padding: 0; }
            
            body { 
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
                background: #f5f7fa;
                color: #333;
            }
            
            .container { max-width: 1400px; margin: 0 auto; padding: 20px; }
            
            .header {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 30px;
                margin: -20px -20px 30px -20px;
                text-align: center;
                box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            }
            
            .header h1 { font-size: 2.5em; margin-bottom: 10px; }
            .header p { font-size: 1.1em; opacity: 0.9; }
            
            .dashboard {
                display: grid;
                grid-template-columns: 1fr 2fr;
                gap: 30px;
                margin-bottom: 30px;
            }
            
            .card {
                background: white;
                border-radius: 12px;
                padding: 25px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                border: 1px solid #e1e8ed;
            }
            
            .upload-area {
                border: 2px dashed #4299e1;
                border-radius: 12px;
                padding: 40px;
                text-align: center;
                background: #f7fafc;
                transition: all 0.3s ease;
            }
            
            .upload-area:hover {
                border-color: #3182ce;
                background: #edf2f7;
            }
            
            .upload-area h3 { color: #2d3748; margin-bottom: 15px; }
            
            .file-input {
                margin: 15px 0;
                padding: 10px;
                border: 1px solid #cbd5e0;
                border-radius: 6px;
                width: 100%;
            }
            
            .btn-primary {
                background: linear-gradient(135deg, #4299e1 0%, #3182ce 100%);
                color: white;
                border: none;
                padding: 12px 30px;
                border-radius: 6px;
                cursor: pointer;
                font-size: 16px;
                transition: all 0.3s ease;
            }
            
            .btn-primary:hover {
                transform: translateY(-1px);
                box-shadow: 0 4px 12px rgba(66, 153, 225, 0.4);
            }
            
            .stats-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
                gap: 15px;
                margin-bottom: 20px;
            }
            
            .stat-card {
                background: #f8fafc;
                padding: 20px;
                border-radius: 8px;
                text-align: center;
                border-left: 4px solid #4299e1;
            }
            
            .stat-number { font-size: 2em; font-weight: bold; color: #2d3748; }
            .stat-label { color: #718096; font-size: 0.9em; margin-top: 5px; }
            
            .document-grid {
                display: grid;
                gap: 20px;
            }
            
            .document-card {
                background: white;
                border-radius: 12px;
                padding: 20px;
                box-shadow: 0 2px 8px rgba(0,0,0,0.08);
                border: 1px solid #e2e8f0;
                transition: all 0.3s ease;
                cursor: pointer;
            }
            
            .document-card:hover {
                box-shadow: 0 4px 20px rgba(0,0,0,0.15);
                transform: translateY(-2px);
            }
            
            .doc-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 15px;
                padding-bottom: 15px;
                border-bottom: 1px solid #e2e8f0;
            }
            
            .doc-title {
                font-weight: bold;
                color: #2d3748;
                font-size: 1.1em;
            }
            
            .doc-type {
                padding: 4px 12px;
                border-radius: 20px;
                font-size: 0.85em;
                font-weight: 500;
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }
            
            .type-capital_call { background: #fed7d7; color: #c53030; }
            .type-distribution { background: #c6f6d5; color: #38a169; }
            .type-valuation { background: #bee3f8; color: #3182ce; }
            .type-quarterly_update { background: #faf0e6; color: #d69e2e; }
            .type-unknown { background: #e2e8f0; color: #718096; }
            
            .status {
                padding: 6px 12px;
                border-radius: 20px;
                font-size: 0.8em;
                font-weight: 500;
                text-transform: uppercase;
            }
            
            .status-processing { background: #fed7d7; color: #c53030; }
            .status-completed { background: #c6f6d5; color: #38a169; }
            .status-failed { background: #feb2b2; color: #e53e3e; }
            .status-pending { background: #faf0e6; color: #d69e2e; }
            
            .extracted-data {
                margin-top: 15px;
                padding: 15px;
                background: #f7fafc;
                border-radius: 8px;
                border-left: 4px solid #4299e1;
            }
            
            .data-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 15px;
            }
            
            .data-field {
                background: white;
                padding: 12px;
                border-radius: 6px;
                border: 1px solid #e2e8f0;
            }
            
            .field-label {
                font-size: 0.8em;
                color: #718096;
                text-transform: uppercase;
                letter-spacing: 0.5px;
                margin-bottom: 5px;
            }
            
            .field-value {
                font-weight: 600;
                color: #2d3748;
                font-size: 1.1em;
            }
            
            .confidence-bar {
                margin-top: 10px;
                height: 4px;
                background: #e2e8f0;
                border-radius: 2px;
                overflow: hidden;
            }
            
            .confidence-fill {
                height: 100%;
                background: linear-gradient(90deg, #48bb78, #38a169);
                transition: width 0.3s ease;
            }
            
            .confidence-text {
                font-size: 0.8em;
                color: #718096;
                margin-top: 5px;
            }
            
            .no-data {
                text-align: center;
                color: #718096;
                font-style: italic;
                padding: 40px;
            }
            
            .loading {
                display: inline-block;
                width: 20px;
                height: 20px;
                border: 2px solid #f3f3f3;
                border-top: 2px solid #4299e1;
                border-radius: 50%;
                animation: spin 1s linear infinite;
            }
            
            @keyframes spin {
                0% { transform: rotate(0deg); }
                100% { transform: rotate(360deg); }
            }
            
            .refresh-btn {
                background: #e2e8f0;
                border: none;
                padding: 8px 16px;
                border-radius: 6px;
                cursor: pointer;
                font-size: 14px;
                color: #4a5568;
                transition: all 0.3s ease;
            }
            
            .refresh-btn:hover {
                background: #cbd5e0;
            }
            
            .section-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 20px;
            }
            
            .section-title {
                font-size: 1.5em;
                font-weight: 600;
                color: #2d3748;
            }
            
            @media (max-width: 768px) {
                .dashboard { grid-template-columns: 1fr; }
                .data-grid { grid-template-columns: 1fr; }
                .stats-grid { grid-template-columns: repeat(2, 1fr); }
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>Alternative Investments Document Intelligence</h1>
                <p>AI-powered platform for processing investment documents</p>
            </div>
            
            <div class="dashboard">
                <div class="card">
                    <div class="upload-area">
                        <h3>📄 Upload Document</h3>
                        <p>Upload PDF documents for automated processing</p>
                        <form id="uploadForm" enctype="multipart/form-data">
                            <input type="file" id="fileInput" class="file-input" accept=".pdf" required>
                            <button type="submit" class="btn-primary">
                                <span id="uploadText">Upload PDF</span>
                                <span id="uploadLoader" class="loading" style="display: none; margin-left: 10px;"></span>
                            </button>
                        </form>
                    </div>
                </div>
                
                <div class="card">
                    <h3>📊 Dashboard</h3>
                    <div class="stats-grid" id="statsGrid">
                        <div class="stat-card">
                            <div class="stat-number" id="totalDocs">-</div>
                            <div class="stat-label">Total Documents</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-number" id="completedDocs">-</div>
                            <div class="stat-label">Completed</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-number" id="processingDocs">-</div>
                            <div class="stat-label">Processing</div>
                        </div>
                    </div>
                    <div id="dashboardData"></div>
                </div>
            </div>
            
            <div class="card">
                <div class="section-header">
                    <h3 class="section-title">📋 Recent Documents</h3>
                    <button class="refresh-btn" onclick="loadDocuments()">🔄 Refresh</button>
                </div>
                <div class="document-grid" id="documentsList">
                    <div class="no-data">Loading documents...</div>
                </div>
            </div>
        </div>
        
        <script>
            let documentsData = [];
            
            // Upload functionality
            document.getElementById('uploadForm').onsubmit = async function(e) {
                e.preventDefault();
                
                const uploadBtn = document.getElementById('uploadText');
                const uploadLoader = document.getElementById('uploadLoader');
                const fileInput = document.getElementById('fileInput');
                
                // Show loading state
                uploadBtn.textContent = 'Uploading...';
                uploadLoader.style.display = 'inline-block';
                
                const formData = new FormData();
                formData.append('file', fileInput.files[0]);
                
                try {
                    const response = await fetch('/api/v1/documents', {
                        method: 'POST',
                        body: formData
                    });
                    
                    if (!response.ok) {
                        throw new Error('Upload failed');
                    }
                    
                    const result = await response.json();
                    showNotification('Document uploaded successfully! Processing started...', 'success');
                    fileInput.value = ''; // Clear file input
                    setTimeout(() => loadDocuments(), 1000); // Refresh after 1 second
                    
                } catch (error) {
                    showNotification('Error uploading document: ' + error.message, 'error');
                } finally {
                    // Reset button state
                    uploadBtn.textContent = 'Upload PDF';
                    uploadLoader.style.display = 'none';
                }
            };
            
            // Load documents with detailed data
            async function loadDocuments() {
                try {
                    const response = await fetch('/api/v1/documents');
                    const documents = await response.json();
                    documentsData = documents;
                    
                    if (documents.length === 0) {
                        document.getElementById('documentsList').innerHTML = 
                            '<div class="no-data">No documents uploaded yet. Upload a PDF to get started!</div>';
                        updateStats([]);
                        return;
                    }
                    
                    // Load detailed data for completed documents
                    const detailedDocs = await Promise.all(
                        documents.map(async (doc) => {
                            if (doc.processing_status === 'completed') {
                                try {
                                    const detailResponse = await fetch(`/api/v1/documents/${doc.id}`);
                                    const detail = await detailResponse.json();
                                    return { ...doc, extractedData: detail.extracted_data };
                                } catch (e) {
                                    return doc;
                                }
                            }
                            return doc;
                        })
                    );
                    
                    renderDocuments(detailedDocs);
                    updateStats(documents);
                    
                } catch (error) {
                    console.error('Error loading documents:', error);
                    document.getElementById('documentsList').innerHTML = 
                        '<div class="no-data">Error loading documents. Please try again.</div>';
                }
            }
            
            function renderDocuments(documents) {
                const listDiv = document.getElementById('documentsList');
                
                listDiv.innerHTML = documents.map(doc => {
                    const typeClass = doc.document_type ? `type-${doc.document_type}` : 'type-unknown';
                    const statusClass = `status-${doc.processing_status}`;
                    
                    let extractedDataHtml = '';
                    if (doc.extractedData && doc.processing_status === 'completed') {
                        extractedDataHtml = renderExtractedData(doc.document_type, doc.extractedData);
                    } else if (doc.processing_status === 'processing') {
                        extractedDataHtml = '<div class="extracted-data"><div style="text-align: center; color: #718096;"><span class="loading"></span> Processing document...</div></div>';
                    } else if (doc.processing_status === 'failed') {
                        extractedDataHtml = '<div class="extracted-data"><div style="text-align: center; color: #e53e3e;">❌ Processing failed</div></div>';
                    }
                    
                    return `
                        <div class="document-card">
                            <div class="doc-header">
                                <div>
                                    <div class="doc-title">📄 ${doc.original_filename}</div>
                                    <div style="font-size: 0.85em; color: #718096; margin-top: 5px;">
                                        Uploaded: ${new Date(doc.created_at).toLocaleString()}
                                    </div>
                                </div>
                                <div style="text-align: right;">
                                    <div class="doc-type ${typeClass}">
                                        ${doc.document_type ? doc.document_type.replace('_', ' ') : 'detecting...'}
                                    </div>
                                    <div class="status ${statusClass}" style="margin-top: 8px;">
                                        ${doc.processing_status}
                                    </div>
                                </div>
                            </div>
                            
                            ${doc.classification_confidence ? `
                                <div class="confidence-bar">
                                    <div class="confidence-fill" style="width: ${doc.classification_confidence * 100}%"></div>
                                </div>
                                <div class="confidence-text">
                                    Classification Confidence: ${(doc.classification_confidence * 100).toFixed(1)}%
                                </div>
                            ` : ''}
                            
                            ${extractedDataHtml}
                        </div>
                    `;
                }).join('');
            }
            
            function renderExtractedData(docType, data) {
                if (!data) return '';
                
                let fieldsHtml = '';
                
                switch (docType) {
                    case 'capital_call':
                        fieldsHtml = `
                            <div class="data-field">
                                <div class="field-label">Fund ID</div>
                                <div class="field-value">${data.fund_id || 'N/A'}</div>
                            </div>
                            <div class="data-field">
                                <div class="field-label">LP ID</div>
                                <div class="field-value">${data.lp_id || 'N/A'}</div>
                            </div>
                            <div class="data-field">
                                <div class="field-label">Call Date</div>
                                <div class="field-value">${data.call_date ? new Date(data.call_date).toLocaleDateString() : 'N/A'}</div>
                            </div>
                            <div class="data-field">
                                <div class="field-label">Call Amount</div>
                                <div class="field-value">${data.call_amount ? formatCurrency(data.call_amount, data.currency) : 'N/A'}</div>
                            </div>
                            <div class="data-field">
                                <div class="field-label">Call Number</div>
                                <div class="field-value">#${data.call_number || 'N/A'}</div>
                            </div>
                            <div class="data-field">
                                <div class="field-label">Currency</div>
                                <div class="field-value">${data.currency || 'USD'}</div>
                            </div>
                        `;
                        break;
                        
                    case 'distribution':
                        fieldsHtml = `
                            <div class="data-field">
                                <div class="field-label">Fund ID</div>
                                <div class="field-value">${data.fund_id || 'N/A'}</div>
                            </div>
                            <div class="data-field">
                                <div class="field-label">LP ID</div>
                                <div class="field-value">${data.lp_id || 'N/A'}</div>
                            </div>
                            <div class="data-field">
                                <div class="field-label">Distribution Date</div>
                                <div class="field-value">${data.distribution_date ? new Date(data.distribution_date).toLocaleDateString() : 'N/A'}</div>
                            </div>
                            <div class="data-field">
                                <div class="field-label">Distribution Amount</div>
                                <div class="field-value">${data.distribution_amount ? formatCurrency(data.distribution_amount, data.currency) : 'N/A'}</div>
                            </div>
                            <div class="data-field">
                                <div class="field-label">Distribution Type</div>
                                <div class="field-value">
                                    <span style="padding: 4px 8px; border-radius: 4px; background: ${data.distribution_type === 'ROC' ? '#c6f6d5' : '#bee3f8'}; color: ${data.distribution_type === 'ROC' ? '#38a169' : '#3182ce'}; font-size: 0.85em; font-weight: 600;">
                                        ${data.distribution_type === 'ROC' ? 'Return of Capital' : 'Capital Income'}
                                    </span>
                                </div>
                            </div>
                            <div class="data-field">
                                <div class="field-label">Currency</div>
                                <div class="field-value">${data.currency || 'USD'}</div>
                            </div>
                        `;
                        break;
                        
                    case 'valuation':
                        fieldsHtml = `
                            <div class="data-field">
                                <div class="field-label">Valuation Date</div>
                                <div class="field-value">${data.valuation_date ? new Date(data.valuation_date).toLocaleDateString() : 'N/A'}</div>
                            </div>
                            <div class="data-field">
                                <div class="field-label">Methodology</div>
                                <div class="field-value">${data.methodology || 'N/A'}</div>
                            </div>
                            <div class="data-field">
                                <div class="field-label">Discount Rate</div>
                                <div class="field-value">${data.discount_rate ? (parseFloat(data.discount_rate) * 100).toFixed(2) + '%' : 'N/A'}</div>
                            </div>
                            <div class="data-field">
                                <div class="field-label">Final Valuation</div>
                                <div class="field-value">${data.final_valuation ? formatCurrency(data.final_valuation, data.currency) : 'N/A'}</div>
                            </div>
                            <div class="data-field">
                                <div class="field-label">Multiples</div>
                                <div class="field-value">
                                    ${data.multiples ? Object.entries(data.multiples).map(([k, v]) => `${k.toUpperCase()}: ${v}`).join('<br>') : 'N/A'}
                                </div>
                            </div>
                            <div class="data-field">
                                <div class="field-label">Currency</div>
                                <div class="field-value">${data.currency || 'USD'}</div>
                            </div>
                        `;
                        break;
                        
                    default:
                        fieldsHtml = '<div class="data-field"><div class="field-value">No specific fields extracted</div></div>';
                }
                
                const confidenceHtml = data.extraction_confidence ? `
                    <div style="margin-top: 15px; padding-top: 15px; border-top: 1px solid #e2e8f0;">
                        <div class="confidence-bar">
                            <div class="confidence-fill" style="width: ${data.extraction_confidence * 100}%"></div>
                        </div>
                        <div class="confidence-text">
                            Extraction Confidence: ${(data.extraction_confidence * 100).toFixed(1)}%
                        </div>
                    </div>
                ` : '';
                
                return `
                    <div class="extracted-data">
                        <h4 style="margin-bottom: 15px; color: #2d3748;">🎯 Extracted Data</h4>
                        <div class="data-grid">
                            ${fieldsHtml}
                        </div>
                        ${confidenceHtml}
                    </div>
                `;
            }
            
            function updateStats(documents) {
                const totalDocs = documents.length;
                const completedDocs = documents.filter(d => d.processing_status === 'completed').length;
                const processingDocs = documents.filter(d => d.processing_status === 'processing').length;
                
                document.getElementById('totalDocs').textContent = totalDocs;
                document.getElementById('completedDocs').textContent = completedDocs;
                document.getElementById('processingDocs').textContent = processingDocs;
            }
            
            function formatCurrency(amount, currency = 'USD') {
                return new Intl.NumberFormat('en-US', {
                    style: 'currency',
                    currency: currency
                }).format(parseFloat(amount));
            }
            
            function showNotification(message, type = 'info') {
                // Simple notification (could be enhanced with a toast library)
                const notification = document.createElement('div');
                notification.style.cssText = `
                    position: fixed;
                    top: 20px;
                    right: 20px;
                    padding: 15px 20px;
                    border-radius: 6px;
                    color: white;
                    font-weight: 500;
                    z-index: 1000;
                    max-width: 400px;
                    background: ${type === 'success' ? '#38a169' : type === 'error' ? '#e53e3e' : '#4299e1'};
                    box-shadow: 0 4px 12px rgba(0,0,0,0.15);
                `;
                notification.textContent = message;
                document.body.appendChild(notification);
                
                setTimeout(() => {
                    notification.remove();
                }, 5000);
            }
            
            // Load documents on page load
            loadDocuments();
            
            // Auto-refresh every 10 seconds
            setInterval(loadDocuments, 10000);
        </script>
    </body>
    </html>
    """