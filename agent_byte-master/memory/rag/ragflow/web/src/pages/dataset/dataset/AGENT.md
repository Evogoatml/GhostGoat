# AGENT - dataset
**Auto-generated folder agent**
**Last Updated:** 2026-03-06 03:56:34
**Folder Path:** `/home/user/GhostGoat/core/reasoning/brain/rag/ragflow/web/src/pages/dataset/dataset`
**Agent ID:** `pending`

---

## Folder Context

This agent maintains awareness of all files in this folder and connects to the central neural network at `.backend/`

### Files Tracked (48)

#### .tsx Files (48)

- `../dataset-overview/dataset-filter.tsx`
  - Size: 2.7KB
  - Modified: 2026-03-03
- `../dataset-overview/index.tsx`
  - Size: 9.6KB
  - Modified: 2026-03-03
- `../dataset-overview/overview-table.tsx`
  - Size: 14.8KB
  - Modified: 2026-03-03
- `../dataset-setting/category-panel.tsx`
  - Size: 2.3KB
  - Modified: 2026-03-03
- `../dataset-setting/chunk-method-form.tsx`
  - Size: 2.4KB
  - Modified: 2026-03-03
- `../dataset-setting/chunk-method-learn-more.tsx`
  - Size: 1.1KB
  - Modified: 2026-03-03
- `../dataset-setting/components/added-source-card.tsx`
  - Size: 3.0KB
  - Modified: 2026-03-03
- `../dataset-setting/components/link-data-pipeline.tsx`
  - Size: 5.8KB
  - Modified: 2026-03-03
- `../dataset-setting/components/link-data-pipline-modal.tsx`
  - Size: 5.4KB
  - Modified: 2026-03-03
- `../dataset-setting/components/link-data-source-modal.tsx`
  - Size: 2.5KB
  - Modified: 2026-03-03
- `../dataset-setting/components/link-data-source.tsx`
  - Size: 6.9KB
  - Modified: 2026-03-03
- `../dataset-setting/components/tag-item.tsx`
  - Size: 3.6KB
  - Modified: 2026-03-03
- `../dataset-setting/configuration-form-container.tsx`
  - Size: 508B
  - Modified: 2026-03-03
- `../dataset-setting/configuration/audio.tsx`
  - Size: 481B
  - Modified: 2026-03-03
- `../dataset-setting/configuration/book.tsx`
  - Size: 817B
  - Modified: 2026-03-03
- `../dataset-setting/configuration/common-item.tsx`
  - Size: 8.2KB
  - Modified: 2026-03-03
- `../dataset-setting/configuration/email.tsx`
  - Size: 480B
  - Modified: 2026-03-03
- `../dataset-setting/configuration/knowledge-graph.tsx`
  - Size: 513B
  - Modified: 2026-03-03
- `../dataset-setting/configuration/laws.tsx`
  - Size: 818B
  - Modified: 2026-03-03
- `../dataset-setting/configuration/manual.tsx`
  - Size: 747B
  - Modified: 2026-03-03
- `../dataset-setting/configuration/naive.tsx`
  - Size: 1.2KB
  - Modified: 2026-03-03
- `../dataset-setting/configuration/one.tsx`
  - Size: 624B
  - Modified: 2026-03-03
- `../dataset-setting/configuration/paper.tsx`
  - Size: 818B
  - Modified: 2026-03-03
- `../dataset-setting/configuration/picture.tsx`
  - Size: 482B
  - Modified: 2026-03-03
- `../dataset-setting/configuration/presentation.tsx`
  - Size: 826B
  - Modified: 2026-03-03
- `../dataset-setting/configuration/qa.tsx`
  - Size: 168B
  - Modified: 2026-03-03
- `../dataset-setting/configuration/resume.tsx`
  - Size: 172B
  - Modified: 2026-03-03
- `../dataset-setting/configuration/table.tsx`
  - Size: 348B
  - Modified: 2026-03-03
- `../dataset-setting/configuration/tag.tsx`
  - Size: 186B
  - Modified: 2026-03-03
- `../dataset-setting/general-form.tsx`
  - Size: 3.0KB
  - Modified: 2026-03-03
- `../dataset-setting/index.tsx`
  - Size: 11.0KB
  - Modified: 2026-03-03
- `../dataset-setting/permission-form-field.tsx`
  - Size: 864B
  - Modified: 2026-03-03
- `../dataset-setting/saving-button.tsx`
  - Size: 2.2KB
  - Modified: 2026-03-03
- `../dataset-setting/tag-table/index.tsx`
  - Size: 8.7KB
  - Modified: 2026-03-03
- `../dataset-setting/tag-table/rename-dialog/index.tsx`
  - Size: 1.1KB
  - Modified: 2026-03-03
- `../dataset-setting/tag-table/rename-dialog/rename-form.tsx`
  - Size: 1.9KB
  - Modified: 2026-03-03
- `../dataset-setting/tag-tabs.tsx`
  - Size: 1010B
  - Modified: 2026-03-03
- `../dataset-setting/tag-word-cloud.tsx`
  - Size: 1.6KB
  - Modified: 2026-03-03
- `../dataset-title.tsx`
  - Size: 355B
  - Modified: 2026-03-03
- `dataset-action-cell.tsx`
  - Size: 3.5KB
  - Modified: 2026-03-03
- `dataset-table.tsx`
  - Size: 6.7KB
  - Modified: 2026-03-03
- `generate-button/generate.tsx`
  - Size: 10.3KB
  - Modified: 2026-03-03
- `index.tsx`
  - Size: 4.5KB
  - Modified: 2026-03-03
- `parsing-card.tsx`
  - Size: 2.4KB
  - Modified: 2026-03-03
- `parsing-status-cell.tsx`
  - Size: 5.7KB
  - Modified: 2026-03-03
- `set-meta-dialog.tsx`
  - Size: 3.3KB
  - Modified: 2026-03-03
- `use-bulk-operate-dataset.tsx`
  - Size: 3.3KB
  - Modified: 2026-03-03
- `use-dataset-table-columns.tsx`
  - Size: 5.8KB
  - Modified: 2026-03-03

---

## Statistics

- **Total Files:** 48
- **Total Size:** 154.7KB
- **File Types:** 1

---

## Neural Network Connection

This agent is connected to the central neural backend:

- **Backend Path:** `.backend/`
- **Knowledge Graph:** Shared across all agents
- **Agent Registry:** `.backend/agents.json`

### Query This Agent

```python
from core.distributed_agent_system import DistributedAgentSystem
system = DistributedAgentSystem()
context = system.backend.get_folder_context('/home/user/GhostGoat/core/reasoning/brain/rag/ragflow/web/src/pages/dataset/dataset')
```

---

## Purpose

This AGENT.md file provides:

1. **Folder Awareness** — Know what files exist here
2. **Context for AI** — Help AI understand this folder's purpose
3. **Navigation** — Quick reference for developers
4. **Neural Link** — Connection to central knowledge graph

**Note:** This file is auto-generated. Regenerate with `make agents` or `python -m core.distributed_agent_system`.

---

*Generated by GhostGoat Distributed Agent System*
*Last scan: 2026-03-06 03:56:34*
