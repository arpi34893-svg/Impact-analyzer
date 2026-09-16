# Agentic Code Reviewer: Project Status

## 1. Current Position

This project is a working prototype for repository-level change-impact analysis. It connects a Streamlit interface to a SWE-bench Lite dataset, repository checkout, patch parsing, AST dependency analysis, NetworkX graph processing, heuristic impact scoring, test correlation, and optional Gemini explanations.

The core proof of concept is implemented and the toy workflow has been verified locally. The project is not yet production-ready because dependency analysis, evaluation, repository management, and external integrations still need hardening.

Estimated status:

- Prototype implementation: approximately 75-80% complete
- Production hardening: approximately 20-25% complete
- Core analysis concept: implemented
- Industry-grade accuracy and integration: still in progress

## 2. End-to-End Pipeline

```text
SWE-bench instance
    -> Load issue metadata
    -> Clone repository
    -> Checkout base commit
    -> Parse the reference patch
    -> Identify changed files and lines
    -> Build AST-based NetworkX dependency graph
    -> Find impacted files
    -> Assign impact scores
    -> Compare predictions with test metadata
    -> Generate optional Gemini explanation
    -> Render Streamlit report
```

The central backend relationship is:

```text
pipeline.py
    |-- dataset_loader.py
    |-- repo_manager.py
    |-- patch_parser.py
    |-- parser_engine.py
    |-- impact_scorer.py
    `-- evaluator.py
```

## 3. Implemented Modules

### `app.py`

**Status:** Working prototype.

This is the Streamlit presentation layer. It provides:

- Toy demo mode using `target_repo`
- SWE-bench instance selection
- Overview metrics
- Raw patch/diff view
- Impact map
- AI review tab
- Agent execution trace
- Final report
- Markdown report download
- HIGH, MEDIUM, and LOW risk badges

It calls:

```python
run_workflow()
analyze_real_instance(instance_index)
```

The UI expects structured data from the real pipeline, including `raw_patch` and `changed_files_count`.

### `agent_workflow.py`

**Status:** Working, but needs cleanup and consolidation.

This module provides two types of orchestration:

#### Toy workflow

```text
ImpactAgent -> ReviewAgent -> END
```

`ImpactAgent` builds a dependency graph and finds impacted files. `ReviewAgent` asks Gemini for a plain-language explanation and creates a Markdown report.

#### Real workflow

The real workflow calls `run_full_pipeline()` and then adds a Gemini explanation.

Known cleanup areas:

- Duplicate imports
- Two real-instance workflow functions with overlapping responsibilities
- Gemini is attempted inside `analyze_real_instance()` even when the UI option is disabled
- LangGraph is used for toy mode but not for the real pipeline

### `pipeline.py`

**Status:** Mostly working and central to real analysis.

This module coordinates the real SWE-bench path:

1. Load the dataset.
2. Select an instance.
3. Clone and checkout the repository.
4. Parse the patch.
5. Build the dependency graph.
6. Find impacted files.
7. Score impacted files.
8. Evaluate against SWE-bench test metadata.
9. Return structured results.

The result currently includes:

- `instance_id`
- `repo`
- `changed_file`
- `changed_lines`
- `changed_files_count`
- `raw_patch`
- `impacted_scored`
- `evaluation`
- `problem_statement`

Important limitation: only the first changed file is currently analyzed:

```python
primary_changed_file = changed[0]["file"]
```

A multi-file patch should be analyzed as one complete change set.

### `dataset_loader.py`

**Status:** Implemented.

Loads `SWE-bench/SWE-bench_Lite` from Hugging Face and exposes the fields needed by the pipeline:

- Repository name
- Base commit
- Problem statement
- Reference patch
- Test patch
- `FAIL_TO_PASS`
- `PASS_TO_PASS`

The default split is `test`.

### `repo_manager.py`

**Status:** Implemented for local experiments.

Responsibilities:

- Create the `repositories/` cache directory
- Clone a GitHub repository
- Reuse an existing local clone
- Checkout the SWE-bench base commit
- Optionally delete a cached repository

Production improvements are needed for invalid clones, missing commits, concurrent runs, uncommitted changes, network failures, and timeouts.

### `patch_parser.py`

**Status:** Working.

Uses `unidiff` to parse the SWE-bench unified diff and return entries such as:

```python
[
    {
        "file": "package/module.py",
        "changed_lines": [10, 11, 12],
    }
]
```

Deleted-only files are skipped. Added and removed lines are recorded using the available target or source line number.

### `parser_engine.py`

**Status:** Working for basic local Python imports.

This is the main static-analysis component. It:

- Walks through Python files
- Parses source code with the standard `ast` module
- Adds file nodes to a NetworkX directed graph
- Adds function and class nodes
- Detects local `import` and `from ... import ...` relationships
- Finds graph ancestors of a changed file

Example relationship:

```text
main.py -> utils.py
```

This means `main.py` imports `utils.py`, so it may be affected when `utils.py` changes.

Important limitation: it is currently file/import-level analysis. It does not reliably determine whether a specific function, class, method, callback, or dynamically imported symbol is actually used.

### `impact_scorer.py`

**Status:** Working heuristic.

Scores files using graph distance from the changed file:

| Situation | Score | Level |
|---|---:|---|
| Changed file | 1.00 | HIGH |
| Direct dependency | 0.80 | HIGH |
| Two-hop dependency | 0.50 | MEDIUM |
| Weak, distant, or disconnected relationship | 0.20 | LOW |
| Test file | Minimum 0.40 | MEDIUM or higher |

The scoring is transparent and easy to understand, but it is not yet a calibrated risk model.

### `evaluator.py`

**Status:** Implemented heuristic.

Compares predicted impacted files with SWE-bench `FAIL_TO_PASS` and `PASS_TO_PASS` test identifiers. It calculates an approximate recall value using filename matching.

```text
recall = matched tests / total ground-truth tests
```

This does not execute tests and should not be interpreted as proven behavioral correctness.

### `target_repo/`

**Status:** Working demonstration repository.

The toy repository contains a small dependency relationship:

```text
main.py -> utils.py
```

The toy workflow was executed successfully and detected `main.py` as impacted by a change to `utils.py`.

### `requirements.txt`

**Status:** Present and usable for development.

It declares the major dependencies:

- NetworkX
- LangGraph
- LangChain Google GenAI
- Pydantic
- Streamlit
- Hugging Face datasets
- GitPython
- Unidiff

Most dependencies use minimum-version constraints. Reproducible deployment would benefit from pinned versions or a lock file.

### `Dockerfile`

**Status:** Present and usable as a basic container definition.

It installs the requirements, copies the project, exposes Streamlit port `8501`, and starts the application.

Production improvements should include a health check, non-root execution, pinned base image, and environment-variable documentation.

## 4. Verified Behavior

The current modules compile successfully with Python syntax checking.

The toy workflow was executed successfully:

```text
Changed file: utils.py
Impacted file: main.py
```

The deterministic AST and NetworkX analysis worked correctly for the toy repository.

Gemini was attempted but failed because the configured credentials were invalid:

```text
401 Unauthenticated
ACCESS_TOKEN_TYPE_UNSUPPORTED
```

Therefore:

- Static analysis works without Gemini.
- AI explanation requires a valid `GEMINI_API_KEY`.
- The current Gemini failure is an external configuration issue, not a Python syntax failure.

## 5. Current Gaps and Required Updates

### Priority 1: Analyze all changed files

`pipeline.py` currently selects only `changed[0]`. It should:

- Analyze every changed file
- Combine impacted files across the patch
- Preserve changed lines per file
- Score the complete change set
- Return all changed file names

### Priority 2: Improve dependency accuracy

`parser_engine.py` should become symbol-aware. Future analysis should consider:

- Imported functions and classes
- Actual call sites
- Methods and inheritance
- Re-exports
- Package `__init__.py` behavior
- Relative imports
- Dynamic imports where possible
- Configuration and entry-point relationships

### Priority 3: Replace heuristic evaluation with test execution

`evaluator.py` should eventually run selected tests and record:

- Tests failing before the change
- Tests passing after the change
- Tests selected by the analyzer
- Precision
- Recall
- F1 score
- False positives and false negatives

### Priority 4: Connect UI controls to backend behavior

The `show_tests` checkbox is currently displayed but does not change the analysis or rendering. It should control test-impact metrics and test-related output.

The `show_ai` option controls display, but the backend still attempts the Gemini request before the UI decides whether to display it. The request should be skipped when AI explanation is disabled.

### Priority 5: Harden repository management

`repo_manager.py` should handle:

- Invalid or incomplete local clones
- Missing Git commits
- Network failures
- Concurrent requests
- Stale working-tree changes
- Clone and checkout timeouts
- Safe cache invalidation

### Priority 6: Improve AI and status reporting

The UI currently treats the presence of `GEMINI_API_KEY` as proof that Gemini is available. A key can exist but still be invalid.

The system should distinguish between:

```text
Not configured
Configured but unavailable
Request successful
Request failed
```

Static analysis should always remain usable when Gemini is unavailable.

### Priority 7: Improve rendering safety

The diff viewer uses `unsafe_allow_html=True` to render patch lines. Patch text should be HTML-escaped before insertion so source content cannot be interpreted as markup.

### Priority 8: Add automated tests

The repository currently needs focused tests for:

- Patch parsing
- Import resolution
- Graph construction
- Impact detection
- Score classification
- Evaluator matching
- Multi-file patches
- Missing or invalid Gemini configuration
- Repository checkout failures
- UI result-field compatibility

## 6. Industry Readiness Assessment

The project is currently best described as a research or demonstration prototype.

### Already demonstrated

```text
Real issue dataset
    + repository checkout
    + patch parsing
    + AST import graph
    + NetworkX dependency traversal
    + heuristic impact scoring
    + approximate test correlation
    + optional LLM explanation
    + interactive report
```

### Still required for production use

```text
File-level analysis -> symbol-level analysis
First changed file -> complete patch analysis
Filename matching -> actual test validation
Local demo -> CI and GitHub integration
Basic cache -> reliable repository service
Single-user UI -> authentication and persistence
```

## 7. Overall Conclusion

The project is not an empty skeleton. The main pipeline is connected and the toy path has been verified end to end.

The completed work is concentrated in the core proof of concept:

- Dataset loading
- Repository checkout
- Patch parsing
- AST parsing
- NetworkX graph creation
- Impact discovery
- Risk scoring
- Streamlit reporting
- Basic Gemini integration

The next phase should focus on correctness and reliability rather than rebuilding the project. The most valuable next implementation step is multi-file and symbol-level impact analysis, followed by real test execution and CI integration.
