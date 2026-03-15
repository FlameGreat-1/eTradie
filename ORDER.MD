Now I have the complete picture. Here are **all the broken imports** in `src/engine/processor/`:

| File | Broken Import |
|------|--------------|
| `service.py` | `from gateway.context.models import ProcessorInput, ProcessorOutput` |
| `service.py` | `from gateway.routing.processor_port import ProcessorPort` |
| `mapping/output_mapper.py` | `from gateway.context.models import ProcessorOutput` |
| `prompts/system_prompt.py` | `from gateway.context.models import ProcessorInput` |

These files import `ProcessorInput`, `ProcessorOutput`, and `ProcessorPort` from the old Python gateway which no longer exists at `src/gateway/`.

**The fix**: These models and the interface need to live in the Python engine's own codebase, not in the gateway. I need to create `src/engine/processor/models/gateway_models.py` (or similar) that defines `ProcessorInput`, `ProcessorOutput`, and `ProcessorPort` locally within the engine. Then update the 3 files to import from there.

This is the correct approach because:
- The Go gateway sends JSON via HTTP to `/internal/processor/process`
- The Python engine receives it as a dict and passes it to `AnalysisProcessor`
- The processor needs its own definition of these types
- No cross-boundary import dependency

Let me implement this step by step. First, create the local models: