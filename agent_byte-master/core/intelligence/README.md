# GhostGoat Intelligence System

The Intelligence System enables GhostGoat to develop dynamic, adaptive problem-solving capabilities by extracting reusable abilities from training data and applying them across different domains.

## Components

### 1. Ability Manager (`ability_manager.py`)
Manages a library of reusable ability templates that represent problem-solving patterns extracted from training data. These abilities are domain-agnostic and can be applied to various problem types.

### 2. Knowledge Frame Manager (`knowledge_frame_manager.py`)
Stores structured knowledge frames that capture domain-specific information, concepts, and relationships. These frames provide context for ability application.

### 3. Pattern Recognizer (`pattern_recognizer.py`)
Analyzes problem descriptions to identify recognized algorithmic patterns and map them to relevant ability templates.

### 4. Analogical Transferer (`analogical_transferer.py`)
Enables cross-domain transfer of abilities by mapping known problem patterns to new domains through analogical reasoning.

### 5. Self-Directed Learner (`self_directed_learner.py`)
Tracks system interactions and learns from successes and failures to improve ability selection and parameter tuning over time.

## Architecture

```
User Query
    │
    ▼
┌──────────────────┐
│ Pattern Recognizer│──→ Recognized Patterns
└──────────────────┘
    │
    ▼
┌──────────────────┐
│  Ability Manager  │──→ Relevant Abilities
└──────────────────┘
    │
    ▼
┌──────────────────┐
│Knowledge Frame   │──→ Domain Knowledge
│   Manager        │
└──────────────────┘
    │
    ▼
┌──────────────────┐
│Analogical        │──→ Transferred Abilities
│   Transferer     │
└──────────────────┘
    │
    ▼
┌──────────────────┐
│  LLM Integration │──→ Enhanced Context
│  (brain/system)  │
└──────────────────┘
    │
    ▼
Enriched Prompt → LLM → Response
    │
    ▼
┌──────────────────┐
│ Self-Directed    │──→ Learning Updates
│    Learner       │
└──────────────────┘
```

## Configuration

The intelligence system is configured via environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `ENABLE_INTELLIGENCE` | `true` | Enable/disable intelligence system |
| `ABILITY_LIBRARY_PATH` | `./data/abilities` | Path to ability storage |
| `KNOWLEDGE_FRAME_PATH` | `./data/knowledge_frames` | Path to knowledge frame storage |
| `PATTERN_RECOGNITION_THRESHOLD` | `0.7` | Minimum confidence for pattern matching |
| `ANALOGICAL_TRANSFER_DEPTH` | `3` | Depth of analogical transfer |
| `SELF_DIRECTED_LEARNING_ENABLED` | `true` | Enable self-directed learning |

## Usage

The intelligence system is automatically integrated into GhostGoat's brain system. When enabled:
1. Pattern recognizer identifies problem patterns from user queries
2. Ability manager retrieves relevant ability templates
3. Knowledge frame manager provides domain context
4. Analogical transferer enables cross-domain application
5. All components work together to provide enhanced context to the LLM

## Extending the System

### Adding New Abilities
Create a new `AbilityTemplate` and add it to `AbilityManager._initialize_core_abilities()` or add it dynamically at runtime.

### Adding New Knowledge Frames
Create a new `KnowledgeFrame` and add it to `KnowledgeFrameManager._initialize_core_knowledge()` or add it dynamically via `add_frame()`.

### Adding New Patterns
Define a new pattern in `PatternRecognizer._initialize_patterns()` with keywords, indicator phrases, and applicable abilities.