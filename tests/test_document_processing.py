import pytest
import asyncio
from decimal import Decimal
from datetime import date
from src.document_processor import DocumentClassifier, FieldExtractor
from src.models import DocumentType

@pytest.fixture
def classifier():
    return DocumentClassifier()

@pytest.fixture
def extractor():
    return FieldExtractor()

class TestDocumentClassifier:
    @pytest.mark.asyncio
    async def test_capital_call_classification(self, classifier):
        text = "CAPITAL CALL NOTICE - Fund ABC-III requests drawdown of $500,000"
        doc_type, confidence = await classifier.classify(text)
        assert doc_type == DocumentType.CAPITAL_CALL
        assert confidence > 0.3
    
    @pytest.mark.asyncio
    async def test_distribution_classification(self, classifier):
        text = "DISTRIBUTION NOTICE - Return of Capital payment of $250,000"
        doc_type, confidence = await classifier.classify(text)
        assert doc_type == DocumentType.DISTRIBUTION
        assert confidence > 0.3
    
    @pytest.mark.asyncio
    async def test_unknown_classification(self, classifier):
        text = "This is some random text without specific patterns"
        doc_type, confidence = await classifier.classify(text)
        assert doc_type == DocumentType.UNKNOWN

class TestFieldExtractor:
    def test_amount_extraction(self, extractor):
        text = "The amount requested is $1,500,000.50"
        amount = extractor.extract_amount(text)
        assert amount == Decimal('1500000.50')
    
    def test_fund_id_extraction(self, extractor):
        text = "Fund ID: ABC-III is making this call"
        fund_id = extractor.extract_fund_id(text)
        assert fund_id == "ABC-III"
    
    def test_date_extraction(self, extractor):
        text = "The call date is 12/15/2023"
        extracted_date = extractor.extract_date(text)
        assert extracted_date == date(2023, 12, 15)
    
    @pytest.mark.asyncio
    async def test_capital_call_extraction(self, extractor):
        text = '''
        CAPITAL CALL NOTICE
        Fund: ABC-III
        LP: LP-001
        Call Amount: $500,000
        Call Date: 10/15/2023
        Call Number: 5
        '''
        fields = await extractor.extract_capital_call_fields(text)
        assert fields['fund_id'] == 'ABC-III'
        assert fields['call_amount'] == Decimal('500000')
        assert fields['lp_id'] == 'LP-001'

if __name__ == "__main__":
    pytest.main([__file__])