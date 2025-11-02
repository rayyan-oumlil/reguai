# Regulatory Document Processing - Chunking Implementation

## Overview

Updated the regulatory document processing pipeline to handle large documents that exceed Claude's token limits by implementing recursive chunking, similar to the 10K extraction approach.

## Changes Made

### 1. **Enhanced `extract_key_info` Method**

- **Previous**: Limited to first 4,000 characters only
- **New**: Processes up to 3.5M characters with automatic chunking

**Key Features**:

- Automatically detects when a document exceeds Claude Sonnet's limits
- Recursively splits documents into smaller chunks
- Processes each chunk independently
- Intelligently merges results from multiple chunks
- Handles throttling with exponential backoff
- Maximum recursion depth of 10 to prevent infinite loops

### 2. **Improved `classify_regulation_with_legalbert` Method**

- **Previous**: Used only 2,000 characters for classification
- **New**: Uses 10,000 characters for better context
- Upgraded to Claude Sonnet 4.5 (via inference profile `us.anthropic.claude-sonnet-4-5-v1:0`)
- Increased max_tokens from 100 to 200 for better explanations

### 3. **Result Merging Logic**

The system now intelligently merges extraction results from multiple chunks:

- **Title**: Takes the longer/more complete title
- **Country**: Uses first non-empty value found
- **Effective Date**: Uses first non-empty value found
- **Affected Sectors**: Merges and deduplicates lists
- **Key Requirements**: Merges and deduplicates lists
- **Penalties**: Takes the longer/more complete description

### 4. **Files Updated**

- `notebooks/extraction/extract_regulatory_files.ipynb`
- `scripts/process_regulatory_document.py`

## Technical Details

### Chunking Strategy

```python
# If document exceeds limit:
1. Split document in half at nearest newline
2. Process first half recursively
3. Process second half recursively
4. Merge results using intelligent merging logic
5. Handle throttling with exponential backoff (5s → 10s → 15s...)
```

### Size Limits

- **Claude Sonnet 4.5**: ~3.5M characters (~1M tokens)
- **Classification**: 10,000 characters (provides better context)
- **LegalBERT**: 512 tokens (unchanged, BERT limitation)

### Error Handling

- Detects `"too long"` or `"validationexception"` errors
- Automatically splits and retries
- Handles API throttling with delays
- Gracefully degrades to partial results if max depth reached

## Benefits

1. **Complete Document Coverage**: No longer limited to first 4,000 characters
2. **Robust Processing**: Handles documents of any size up to 3.5M characters
3. **Better Accuracy**: More context leads to better classification and extraction
4. **Fault Tolerant**: Handles API throttling and errors gracefully
5. **Consistent with 10K Extraction**: Uses same proven approach

## Usage Examples

### Notebook Usage

```python
processor = RegulatoryDocumentProcessor()
result = processor.process_document('path/to/large_document.xml')
# Automatically chunks if needed
```

### Standalone Script Usage

```bash
python scripts/process_regulatory_document.py \
  --file_path path/to/large_document.xml \
  --output_dir output/
# Automatically chunks if needed
```

### Lambda Usage

The Lambda function automatically uses chunking - no changes needed to event format.

## Performance Notes

- **Small documents (<100K chars)**: No impact, processes as before
- **Medium documents (100K-3.5M chars)**: Single API call, slight increase in processing time
- **Large documents (>3.5M chars)**: Multiple API calls with chunking
  - 2 chunks: ~2x processing time
  - 4 chunks: ~4x processing time
  - Throttling delays may add 5-30 seconds per chunk

## Testing Recommendations

1. Test with various document sizes:

   - Small (< 100K chars)
   - Medium (100K - 1M chars)
   - Large (1M - 3.5M chars)
   - Very large (> 3.5M chars)

2. Verify result quality:

   - Check that all sections are covered
   - Verify list merging (no duplicates)
   - Ensure key information isn't lost

3. Monitor API usage:
   - Large documents will use more API calls
   - Consider cost implications for batch processing

## Future Enhancements

Potential improvements:

1. Smart chunking based on document structure (sections, articles)
2. Parallel processing of chunks (instead of sequential)
3. Caching of intermediate results
4. Progressive summarization for extremely large documents
5. Cost optimization by using smaller models for initial passes

## Related Documentation

- `GUIDE_COMPLET_PROJET_DATATHON.md` - Full project guide
- `README_REGULATORY_PROCESSOR.md` - Script usage documentation
- `notebooks/extraction/extract_data_points_10k.ipynb` - Original chunking implementation
