# AGENT — `python`

> Auto-generated folder agent. **Do not edit manually** — regenerated on every scan.

| Field | Value |
|---|---|
| **Folder** | `core/memory/rag/ragflow/sdk/python` |
| **Agent ID** | `e9646329` |
| **Last Updated** | `2026-04-30 03:40:13` |
| **Files Tracked** | `63` |
| **Total Size** | `402.9 KB` |
| **Neural Backend** | `../../../../../../.backend/` |

---

## Files in this Folder

#### `.json` (1 files)

- **`test/test_sdk_api/test_data/test.json`** — 2.1 KB, modified 2026-04-23

#### `.md` (1 files)

- **`test/test_sdk_api/test_data/test.md`** — 3.5 KB, modified 2026-04-23

#### `.py` (60 files)

- **`hello_ragflow.py`** — 674 B, modified 2026-04-23
- **`ragflow_sdk/__init__.py`** — 1.1 KB, modified 2026-04-23
- **`ragflow_sdk/modules/__init__.py`** — 621 B, modified 2026-04-23
- **`ragflow_sdk/modules/agent.py`** — 3.2 KB, modified 2026-04-23
- **`ragflow_sdk/modules/base.py`** — 1.8 KB, modified 2026-04-23
- **`ragflow_sdk/modules/chat.py`** — 3.6 KB, modified 2026-04-23
- **`ragflow_sdk/modules/chunk.py`** — 1.9 KB, modified 2026-04-23
- **`ragflow_sdk/modules/dataset.py`** — 5.3 KB, modified 2026-04-23
- **`ragflow_sdk/modules/document.py`** — 3.7 KB, modified 2026-04-23
- **`ragflow_sdk/modules/session.py`** — 4.8 KB, modified 2026-04-23
- **`ragflow_sdk/ragflow.py`** — 10.1 KB, modified 2026-04-23
- **`test/conftest.py`** — 4.6 KB, modified 2026-04-23
- **`test/libs/__init__.py`** — 622 B, modified 2026-04-23
- **`test/libs/auth.py`** — 860 B, modified 2026-04-23
- **`test/libs/utils/__init__.py`** — 2.0 KB, modified 2026-04-23
- **`test/libs/utils/file_utils.py`** — 2.9 KB, modified 2026-04-23
- **`test/libs/utils/hypothesis_utils.py`** — 1.0 KB, modified 2026-04-23
- **`test/test_frontend_api/common.py`** — 2.8 KB, modified 2026-04-23
- **`test/test_frontend_api/get_email.py`** — 733 B, modified 2026-04-23
- **`test/test_frontend_api/test_chunk.py`** — 2.4 KB, modified 2026-04-23
- **`test/test_frontend_api/test_dataset.py`** — 5.8 KB, modified 2026-04-23
- **`test/test_http_api/common.py`** — 9.2 KB, modified 2026-04-23
- **`test/test_http_api/conftest.py`** — 6.1 KB, modified 2026-04-23
- **`test/test_http_api/test_chat_assistant_management/conftest.py`** — 1.6 KB, modified 2026-04-23
- **`test/test_http_api/test_chat_assistant_management/test_create_chat_assistant.py`** — 12.1 KB, modified 2026-04-23
- **`test/test_http_api/test_chat_assistant_management/test_delete_chat_assistants.py`** — 5.3 KB, modified 2026-04-23
- **`test/test_http_api/test_chat_assistant_management/test_list_chat_assistants.py`** — 11.1 KB, modified 2026-04-23
- **`test/test_http_api/test_chat_assistant_management/test_update_chat_assistant.py`** — 12.5 KB, modified 2026-04-23
- **`test/test_http_api/test_chunk_management_within_dataset/conftest.py`** — 1.7 KB, modified 2026-04-23
- **`test/test_http_api/test_chunk_management_within_dataset/test_add_chunk.py`** — 10.5 KB, modified 2026-04-23
- **`test/test_http_api/test_chunk_management_within_dataset/test_delete_chunks.py`** — 7.8 KB, modified 2026-04-23
- **`test/test_http_api/test_chunk_management_within_dataset/test_list_chunks.py`** — 8.4 KB, modified 2026-04-23
- **`test/test_http_api/test_chunk_management_within_dataset/test_retrieval_chunks.py`** — 12.2 KB, modified 2026-04-23
- **`test/test_http_api/test_chunk_management_within_dataset/test_update_chunk.py`** — 10.4 KB, modified 2026-04-23
- **`test/test_http_api/test_dataset_mangement/conftest.py`** — 1.2 KB, modified 2026-04-23
- **`test/test_http_api/test_dataset_mangement/test_create_dataset.py`** — 34.9 KB, modified 2026-04-23
- **`test/test_http_api/test_dataset_mangement/test_delete_datasets.py`** — 8.0 KB, modified 2026-04-23
- **`test/test_http_api/test_dataset_mangement/test_list_datasets.py`** — 12.9 KB, modified 2026-04-23
- **`test/test_http_api/test_dataset_mangement/test_update_dataset.py`** — 35.7 KB, modified 2026-04-23
- **`test/test_http_api/test_file_management_within_dataset/conftest.py`** — 1.7 KB, modified 2026-04-23
- **`test/test_http_api/test_file_management_within_dataset/test_delete_documents.py`** — 6.4 KB, modified 2026-04-23
- **`test/test_http_api/test_file_management_within_dataset/test_download_document.py`** — 5.9 KB, modified 2026-04-23
- **`test/test_http_api/test_file_management_within_dataset/test_list_documents.py`** — 12.6 KB, modified 2026-04-23
- **`test/test_http_api/test_file_management_within_dataset/test_parse_documents.py`** — 8.4 KB, modified 2026-04-23
- **`test/test_http_api/test_file_management_within_dataset/test_stop_parse_documents.py`** — 8.6 KB, modified 2026-04-23
- **`test/test_http_api/test_file_management_within_dataset/test_update_document.py`** — 19.2 KB, modified 2026-04-23
- **`test/test_http_api/test_file_management_within_dataset/test_upload_documents.py`** — 8.5 KB, modified 2026-04-23
- **`test/test_http_api/test_session_management/conftest.py`** — 2.0 KB, modified 2026-04-23
- **`test/test_http_api/test_session_management/test_create_session_with_chat_assistant.py`** — 5.1 KB, modified 2026-04-23
- **`test/test_http_api/test_session_management/test_delete_sessions_with_chat_assistant.py`** — 7.3 KB, modified 2026-04-23
- **`test/test_http_api/test_session_management/test_list_sessions_with_chat_assistant.py`** — 11.1 KB, modified 2026-04-23
- **`test/test_http_api/test_session_management/test_update_session_with_chat_assistant.py`** — 7.1 KB, modified 2026-04-23
- **`test/test_sdk_api/common.py`** — 700 B, modified 2026-04-23
- **`test/test_sdk_api/get_email.py`** — 736 B, modified 2026-04-23
- **`test/test_sdk_api/t_agent.py`** — 1.2 KB, modified 2026-04-23
- **`test/test_sdk_api/t_chat.py`** — 4.3 KB, modified 2026-04-23
- **`test/test_sdk_api/t_chunk.py`** — 7.8 KB, modified 2026-04-23
- **`test/test_sdk_api/t_dataset.py`** — 3.0 KB, modified 2026-04-23
- **`test/test_sdk_api/t_document.py`** — 7.6 KB, modified 2026-04-23
- **`test/test_sdk_api/t_session.py`** — 5.4 KB, modified 2026-04-23

#### `.toml` (1 files)

- **`pyproject.toml`** — 898 B, modified 2026-04-23

---

## Statistics

| Metric | Value |
|---|---|
| Files | 63 |
| Size | 402.9 KB |
| Types | 4 |

---

## Neural Network Connection

This agent is part of GhostGoat's **Central Ordinance System**.
All agents share one neural backend at `.backend/`.

### Query this folder's context

```python
from core.ordinance.ordinance_client import OrdinanceClient

client = OrdinanceClient()

# All files in this folder
ctx = client.get_folder_context("/home/popic/GhostGoat/core/memory/rag/ragflow/sdk/python")

# Full-text search across all folders
results = client.search("your query")

# This agent's neighbours in the knowledge graph
neighbours = client.get_neighbours("e9646329")
```

---

*Generated by GhostGoat Ordinance System — Central Neural Backend*
*Scan time: 2026-04-30 03:40:13*
