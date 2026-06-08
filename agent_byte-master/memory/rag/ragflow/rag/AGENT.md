# AGENT — `rag`

> Auto-generated folder agent. **Do not edit manually** — regenerated on every scan.

| Field | Value |
|---|---|
| **Folder** | `core/memory/rag/ragflow/rag` |
| **Agent ID** | `e9227904` |
| **Last Updated** | `2026-04-30 03:39:59` |
| **Files Tracked** | `113` |
| **Total Size** | `1.40 MB` |
| **Neural Backend** | `../../../../../.backend/` |

---

## Files in this Folder

#### `.json` (4 files)

- **`flow/tests/dsl_examples/general_pdf_all.json`** — 3.6 KB, modified 2026-04-23
- **`flow/tests/dsl_examples/hierarchical_merger.json`** — 2.1 KB, modified 2026-04-23
- **`res/ner.json`** — 229.8 KB, modified 2026-04-23
- **`res/synonym.json`** — 262.1 KB, modified 2026-04-23

#### `.md` (30 files)

- **`prompts/analyze_task_system.md`** — 2.2 KB, modified 2026-04-23
- **`prompts/analyze_task_user.md`** — 526 B, modified 2026-04-23
- **`prompts/ask_summary.md`** — 575 B, modified 2026-04-23
- **`prompts/assign_toc_levels.md`** — 1.8 KB, modified 2026-04-23
- **`prompts/citation_plus.md`** — 384 B, modified 2026-04-23
- **`prompts/citation_prompt.md`** — 5.3 KB, modified 2026-04-23
- **`prompts/content_tagging_prompt.md`** — 873 B, modified 2026-04-23
- **`prompts/cross_languages_sys_prompt.md`** — 751 B, modified 2026-04-23
- **`prompts/cross_languages_user_prompt.md`** — 70 B, modified 2026-04-23
- **`prompts/full_question_prompt.md`** — 1.3 KB, modified 2026-04-23
- **`prompts/keyword_prompt.md`** — 410 B, modified 2026-04-23
- **`prompts/meta_filter.md`** — 4.2 KB, modified 2026-04-23
- **`prompts/next_step.md`** — 3.4 KB, modified 2026-04-23
- **`prompts/question_prompt.md`** — 523 B, modified 2026-04-23
- **`prompts/rank_memory.md`** — 857 B, modified 2026-04-23
- **`prompts/reflect.md`** — 3.0 KB, modified 2026-04-23
- **`prompts/related_question.md`** — 2.2 KB, modified 2026-04-23
- **`prompts/structured_output_prompt.md`** — 666 B, modified 2026-04-23
- **`prompts/summary4memory.md`** — 1.2 KB, modified 2026-04-23
- **`prompts/toc_detection.md`** — 1.9 KB, modified 2026-04-23
- **`prompts/toc_extraction.md`** — 1.8 KB, modified 2026-04-23
- **`prompts/toc_extraction_continue.md`** — 2.1 KB, modified 2026-04-23
- **`prompts/toc_from_text_system.md`** — 3.8 KB, modified 2026-04-23
- **`prompts/toc_from_text_user.md`** — 154 B, modified 2026-04-23
- **`prompts/toc_index.md`** — 704 B, modified 2026-04-23
- **`prompts/toc_relevance_system.md`** — 3.5 KB, modified 2026-04-23
- **`prompts/toc_relevance_user.md`** — 405 B, modified 2026-04-23
- **`prompts/tool_call_summary.md`** — 964 B, modified 2026-04-23
- **`prompts/vision_llm_describe_prompt.md`** — 1.2 KB, modified 2026-04-23
- **`prompts/vision_llm_figure_describe_prompt.md`** — 1.5 KB, modified 2026-04-23

#### `.py` (79 files)

- **`__init__.py`** — 699 B, modified 2026-04-23
- **`app/__init__.py`** — 621 B, modified 2026-04-23
- **`app/audio.py`** — 2.2 KB, modified 2026-04-23
- **`app/book.py`** — 7.4 KB, modified 2026-04-23
- **`app/email.py`** — 4.5 KB, modified 2026-04-23
- **`app/laws.py`** — 7.8 KB, modified 2026-04-23
- **`app/manual.py`** — 13.0 KB, modified 2026-04-23
- **`app/naive.py`** — 38.8 KB, modified 2026-04-23
- **`app/one.py`** — 5.9 KB, modified 2026-04-23
- **`app/paper.py`** — 11.5 KB, modified 2026-04-23
- **`app/picture.py`** — 4.0 KB, modified 2026-04-23
- **`app/presentation.py`** — 8.4 KB, modified 2026-04-23
- **`app/qa.py`** — 18.9 KB, modified 2026-04-23
- **`app/resume.py`** — 6.9 KB, modified 2026-04-23
- **`app/table.py`** — 15.7 KB, modified 2026-04-23
- **`app/tag.py`** — 5.7 KB, modified 2026-04-23
- **`benchmark.py`** — 14.1 KB, modified 2026-04-23
- **`flow/__init__.py`** — 1.9 KB, modified 2026-04-23
- **`flow/base.py`** — 2.2 KB, modified 2026-04-23
- **`flow/extractor/__init__.py`** — 621 B, modified 2026-04-23
- **`flow/extractor/extractor.py`** — 4.2 KB, modified 2026-04-23
- **`flow/extractor/schema.py`** — 1.6 KB, modified 2026-04-23
- **`flow/file.py`** — 1.7 KB, modified 2026-04-23
- **`flow/hierarchical_merger/__init__.py`** — 621 B, modified 2026-04-23
- **`flow/hierarchical_merger/hierarchical_merger.py`** — 6.4 KB, modified 2026-04-23
- **`flow/hierarchical_merger/schema.py`** — 1.6 KB, modified 2026-04-23
- **`flow/parser/__init__.py`** — 620 B, modified 2026-04-23
- **`flow/parser/parser.py`** — 32.9 KB, modified 2026-04-23
- **`flow/parser/schema.py`** — 989 B, modified 2026-04-23
- **`flow/pipeline.py`** — 6.9 KB, modified 2026-04-23
- **`flow/splitter/__init__.py`** — 621 B, modified 2026-04-23
- **`flow/splitter/schema.py`** — 1.6 KB, modified 2026-04-23
- **`flow/splitter/splitter.py`** — 5.5 KB, modified 2026-04-23
- **`flow/tests/client.py`** — 2.1 KB, modified 2026-04-23
- **`flow/tokenizer/__init__.py`** — 620 B, modified 2026-04-23
- **`flow/tokenizer/schema.py`** — 2.5 KB, modified 2026-04-23
- **`flow/tokenizer/tokenizer.py`** — 8.0 KB, modified 2026-04-23
- **`llm/__init__.py`** — 6.6 KB, modified 2026-04-23
- **`llm/chat_model.py`** — 68.2 KB, modified 2026-04-23
- **`llm/cv_model.py`** — 43.2 KB, modified 2026-04-23
- **`llm/embedding_model.py`** — 33.6 KB, modified 2026-04-23
- **`llm/rerank_model.py`** — 17.0 KB, modified 2026-04-23
- **`llm/sequence2txt_model.py`** — 12.2 KB, modified 2026-04-23
- **`llm/tts_model.py`** — 14.4 KB, modified 2026-04-23
- **`nlp/__init__.py`** — 35.3 KB, modified 2026-04-23
- **`nlp/query.py`** — 10.8 KB, modified 2026-04-23
- **`nlp/rag_tokenizer.py`** — 1.3 KB, modified 2026-04-23
- **`nlp/search.py`** — 28.2 KB, modified 2026-04-23
- **`nlp/surname.py`** — 4.2 KB, modified 2026-04-23
- **`nlp/synonym.py`** — 3.1 KB, modified 2026-04-23
- **`nlp/term_weight.py`** — 8.1 KB, modified 2026-04-23
- **`prompts/__init__.py`** — 179 B, modified 2026-04-23
- **`prompts/generator.py`** — 31.0 KB, modified 2026-04-23
- **`prompts/template.py`** — 504 B, modified 2026-04-23
- **`raptor.py`** — 9.1 KB, modified 2026-04-23
- **`settings.py`** — 622 B, modified 2026-04-23
- **`svr/cache_file_svr.py`** — 1.8 KB, modified 2026-04-23
- **`svr/discord_svr.py`** — 2.6 KB, modified 2026-04-23
- **`svr/sync_data_source.py`** — 28.1 KB, modified 2026-04-23
- **`svr/task_executor.py`** — 47.6 KB, modified 2026-04-23
- **`utils/__init__.py`** — 623 B, modified 2026-04-23
- **`utils/azure_sas_conn.py`** — 3.0 KB, modified 2026-04-23
- **`utils/azure_spn_conn.py`** — 3.7 KB, modified 2026-04-23
- **`utils/base64_image.py`** — 2.8 KB, modified 2026-04-23
- **`utils/doc_store_conn.py`** — 7.5 KB, modified 2026-04-23
- **`utils/es_conn.py`** — 25.5 KB, modified 2026-04-23
- **`utils/file_utils.py`** — 8.2 KB, modified 2026-04-23
- **`utils/gcs_conn.py`** — 7.5 KB, modified 2026-04-23
- **`utils/infinity_conn.py`** — 39.8 KB, modified 2026-04-23
- **`utils/minio_conn.py`** — 6.0 KB, modified 2026-04-23
- **`utils/ob_conn.py`** — 65.7 KB, modified 2026-04-23
- **`utils/opendal_conn.py`** — 4.3 KB, modified 2026-04-23
- **`utils/opensearch_conn.py`** — 22.8 KB, modified 2026-04-23
- **`utils/oss_conn.py`** — 5.9 KB, modified 2026-04-23
- **`utils/raptor_utils.py`** — 4.4 KB, modified 2026-04-23
- **`utils/redis_conn.py`** — 14.1 KB, modified 2026-04-23
- **`utils/s3_conn.py`** — 7.7 KB, modified 2026-04-23
- **`utils/storage_factory.py`** — 622 B, modified 2026-04-23
- **`utils/tavily_conn.py`** — 2.3 KB, modified 2026-04-23

---

## Statistics

| Metric | Value |
|---|---|
| Files | 113 |
| Size | 1.40 MB |
| Types | 3 |

---

## Neural Network Connection

This agent is part of GhostGoat's **Central Ordinance System**.
All agents share one neural backend at `.backend/`.

### Query this folder's context

```python
from core.ordinance.ordinance_client import OrdinanceClient

client = OrdinanceClient()

# All files in this folder
ctx = client.get_folder_context("/home/popic/GhostGoat/core/memory/rag/ragflow/rag")

# Full-text search across all folders
results = client.search("your query")

# This agent's neighbours in the knowledge graph
neighbours = client.get_neighbours("e9227904")
```

---

*Generated by GhostGoat Ordinance System — Central Neural Backend*
*Scan time: 2026-04-30 03:39:59*
