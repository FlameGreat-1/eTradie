import os

service_path = "src/engine/processor/service.py"

with open(service_path, "r") as f:
    text = f.read()

# Add Typing
if "AsyncGenerator" not in text:
    text = text.replace("from typing import Optional", "from typing import Optional, AsyncGenerator")

# Append at the end of class AnalysisProcessor:
stream_impl = """

    async def stream_process(
        self,
        context: ProcessorInput,
        *,
        user_id: str,
        trace_id: Optional[str] = None,
    ) -> AsyncGenerator[dict, None]:
        start = time.monotonic()
        symbol = context.symbol

        logger.info(
            "processor_stream_started",
            extra={
                "symbol": symbol,
                "trace_id": trace_id,
            },
        )

        try:
            async with asyncio.timeout(self._config.total_timeout_seconds):
                async for chunk in self._stream_execute(context, user_id=user_id, trace_id=trace_id, start=start):
                    yield chunk

        except Exception as exc:
            logger.error("stream_processor_failed", extra={"symbol": symbol, "error": str(exc)})
            yield {"type": "error", "message": str(exc)}

    async def _stream_execute(
        self,
        context: ProcessorInput,
        *,
        user_id: str,
        trace_id: Optional[str] = None,
        start: float,
    ) -> AsyncGenerator[dict, None]:
        symbol = context.symbol
        self._validate_context(context, trace_id=trace_id)

        system_prompt = build_system_prompt()
        user_message = build_user_message(context)
        prompt_hash = compute_prompt_hash(system_prompt, user_message)

        yield {"type": "status", "message": "Analyzing data...", "reasoning": ""}

        full_text = ""
        in_reasoning = False
        reasoning_buffer = ""
        
        try:
            async for chunk in self._llm.stream_call(
                system_prompt=system_prompt,
                user_message=user_message,
                trace_id=trace_id
            ):
                full_text += chunk
                
                if not in_reasoning:
                    target_key1 = '"explainable_reasoning": "'
                    key_idx = full_text.find(target_key1)
                    if key_idx != -1:
                        in_reasoning = True
                        val_start = key_idx + len(target_key1)
                        extracted = full_text[val_start:]
                        if '",' in extracted:
                            extracted = extracted.split('",')[0]
                            in_reasoning = False
                        reasoning_buffer += extracted
                        yield {"type": "reasoning_chunk", "text": extracted}
                else:
                    if '",' in chunk:
                        idx = chunk.find('",')
                        in_reasoning = False
                        valid_chunk = chunk[:idx]
                        reasoning_buffer += valid_chunk
                        yield {"type": "reasoning_chunk", "text": valid_chunk}
                    elif '"\\n' in chunk:
                        idx = chunk.find('"\\n')
                        in_reasoning = False
                        valid_chunk = chunk[:idx]
                        reasoning_buffer += valid_chunk
                        yield {"type": "reasoning_chunk", "text": valid_chunk}
                    else:
                        reasoning_buffer += chunk
                        yield {"type": "reasoning_chunk", "text": chunk}

        except Exception as exc:
            yield {"type": "error", "message": str(exc)}
            raise

        text = full_text.strip()
        if text.startswith("```json"):
            text = text[7:]
        elif text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()
        
        try:
            raw_dict = orjson.loads(text)
        except Exception:
            raw_dict = {"raw_text": full_text[:4096]}
            
        raw_dict["_llm_provider"] = self._llm.PROVIDER
        
        try:
            analysis_output, _ = parse_llm_response(full_text, require_citations=self._config.require_citations, trace_id=trace_id)
            processor_output = map_to_processor_output(analysis_output, raw_response=raw_dict)
            
            if hasattr(processor_output, "model_dump"):
                pd = processor_output.model_dump(mode="json")
            else:
                pd = processor_output
                
            yield {"type": "final", "data": pd}
        except Exception as exc:
            yield {"type": "error", "message": "Failed to validate final schema: " + str(exc)}
"""

if "def stream_process(" not in text:
    text += stream_impl
    with open(service_path, "w") as f:
        f.write(text)
    print("Patched service.py")
else:
    print("Already patched")
