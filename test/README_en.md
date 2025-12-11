# Vectorization Service Test Scripts

中文: [README.md](README.md)

This directory contains a set of test scripts for the `core.vectorize` module.

## Test Scripts

### 1. test_vectorize.py - Functional tests

Comprehensive tests for vectorization service functionality including:

- Single-task add & processing
- Multi-task concurrent processing
- Task status monitoring
- File vectorization status queries
- Database record checks

**Usage:**

```bash
python test_vectorize.py
```

### 2. test_performance.py - Performance tests

Performance tests for the vectorization service, including:

- Processing time for files of different sizes
- Concurrency handling
- Memory usage monitoring
- Error handling performance

**Usage:**

```bash
python test_performance.py
```

**Note:** Memory monitoring requires `psutil`:

```bash
pip install psutil
```

### 3. test_cli.py - CLI tool tests

Command-line tools to test vectorization features.

**Usage:**

Add a single file task:

```bash
python test_cli.py add --file sample_ai_document.txt
```

Process a file and wait for completion:

```bash
python test_cli.py process --file sample_ai_document.txt
```

Monitor tasks:

```bash
python test_cli.py monitor --task-id <task_id>
```

List all tasks:

```bash
python test_cli.py list
```

Check vectorization status:

```bash
python test_cli.py status
python test_cli.py status --file-id <file_id>
```

Batch processing a directory:

```bash
python test_cli.py batch --directory /path/to/docs
python test_cli.py batch --directory /path/to/docs --pattern "*.txt"
```

### 4. sample_ai_document.txt - Sample test document

A sample document about AI technologies used for testing vectorization.

## Environment Requirements

### Required environment variables

Before running the tests, make sure the following environment variables are configured:

```bash
export OPENAI_API_KEY="your_api_key_here"
export MODEL_NAME="Qwen/Qwen3-Embedding-8B"  # or another supported model
export OPENAI_URL="https://api.siliconflow.cn/v1"  # or another endpoint
```

### Python dependencies

Install project dependencies:

```bash
pip install -r ../requirements.txt
```

## Test Flow

### Basic functional testing

1. Run the functional tests:

```bash
python test_vectorize.py
```

2. Check test results and confirm the test cases pass

3. Optional: run performance tests to evaluate system performance:

```bash
python test_performance.py
```

### CLI workflow

1. Process the sample document:

```bash
python test_cli.py process --file sample_ai_document.txt
```

2. Monitor processing progress and examine results

3. Check vectorization status:

```bash
python test_cli.py status
```

## Test Results

### Expected output on success

- ✓ All test cases pass
- Task states transition correctly (pending → processing → completed)
- File vectorization state is updated correctly
- Documents and vectors are recorded correctly in the database

## Common Issues & Troubleshooting

1. **Missing environment variables**

```
Error: missing required environment variables
Solution: set OPENAI_API_KEY, MODEL_NAME, and OPENAI_URL
```

2. **API call failure**

```
Error: failed to fetch embeddings
Solution: check API key and network connectivity
```

3. **File path issues**

```
Error: file not found
Solution: use absolute path or correct relative path from the working directory
```

4. **Database connection issues**

```
Error: database initialization failed
Solution: verify database file permissions and ensure write access
```

## Performance Benchmarks

Typical processing times (test environment):

- Small file (500 chars): 1-3 seconds
- Medium file (2000 chars): 3-8 seconds
- Large file (8000 chars): 8-20 seconds
- Very large file (15000 chars): 15-40 seconds

_Notes: actual performance depends on network, API latency, and system configuration._

## Extending tests

### Custom test files

1. Create files containing special characters
2. Create files with different encodings (UTF-8, GBK, etc.)

---

English version: [README.md](README.md)
