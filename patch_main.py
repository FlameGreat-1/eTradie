import os

main_path = "src/engine/main.py"

with open(main_path, "r") as f:
    text = f.read()

stream_endpoint = """
    from fastapi.responses import StreamingResponse
    import json

    @app.get("/api/analysis/stream-rerun")
    async def stream_rerun_analysis(
        request: Request,
        symbol: str,
        trace_id: Optional[str] = None,
        user: AuthenticatedUser = Depends(get_current_user),
    ):
        container: Container = request.app.state.container
        
        async def event_generator():
            try:
                processor = await _resolve_user_processor(container, user.user_id)
                user_broker = await _resolve_user_broker(container, user.user_id)
                
                yield f"data: {json.dumps({'type': 'status', 'message': 'Running Technical Analysis'})}\\n\\n"
                
                # Step 1: TA
                ta_result = await container.ta_orchestrator.analyze(
                    symbol=symbol,
                    broker_client=user_broker,
                    user_id=user.user_id,
                )
                ta_analysis = ta_result if isinstance(ta_result, dict) else (ta_result.model_dump(mode="json") if hasattr(ta_result, "model_dump") else {"raw": str(ta_result)})
                
                ta_status = ta_analysis.get("status", "")
                ta_has_candidates = bool(ta_analysis.get("smc_candidates")) or bool(ta_analysis.get("snd_candidates"))
                if ta_status in ("error", "insufficient_data") and not ta_has_candidates:
                    yield f"data: {json.dumps({'type': 'error', 'message': 'TA failed or insufficient data'})}\\n\\n"
                    return

                yield f"data: {json.dumps({'type': 'status', 'message': 'Collecting Macroeconomic Data'})}\\n\\n"
                
                # Step 2: Macro
                macro_analysis = {}
                collector_map = {
                    "central_bank": container.cb_collector,
                    "cot": container.cot_collector,
                    "economic": container.economic_collector,
                    "news": container.news_collector,
                    "calendar": container.calendar_collector,
                    "dxy": container.dxy_collector,
                    "intermarket": container.intermarket_collector,
                    "sentiment": container.sentiment_collector,
                }
                tasks = {name: c.collect() for name, c in collector_map.items()}
                raw_results = await asyncio.gather(*tasks.values(), return_exceptions=True)
                for name, result in zip(tasks.keys(), raw_results):
                    if isinstance(result, Exception):
                        macro_analysis[name] = None
                    elif isinstance(result, dict):
                        macro_analysis[name] = result
                    elif hasattr(result, "model_dump"):
                        macro_analysis[name] = result.model_dump(mode="json")
                    else:
                        macro_analysis[name] = {"raw": str(result)}

                macro_signals = derive_macro_signals(macro_analysis)
                ta_signals = derive_ta_signals(ta_analysis)

                yield f"data: {json.dumps({'type': 'status', 'message': 'Retrieving Knowledge Base RAG'})}\\n\\n"

                query_parts: list[str] = [symbol]
                if ta_signals["direction"]: query_parts.append(ta_signals["direction"])
                if ta_signals["overall_trend"] and ta_signals["overall_trend"] != "NEUTRAL": query_parts.append(f"trend {ta_signals['overall_trend'].lower()}")
                if ta_signals["framework"]: query_parts.append(ta_signals["framework"].upper())
                for pattern in ta_signals["patterns"]: query_parts.append(pattern.lower().replace("_", " "))
                for family in ta_signals["setup_families"]: query_parts.append(family.replace("_", " "))
                query_text = " ".join(query_parts)

                # Step 3: RAG
                bundle = await container.rag_orchestrator.retrieve_context(
                    query_text,
                    user.user_id,
                    strategy=None,
                    framework=ta_signals["framework"] or None,
                    setup_family=(ta_signals["setup_families"][0] if ta_signals["setup_families"] else None),
                    direction=ta_signals["direction"] or None,
                    timeframe=None,
                    style=None,
                    trace_id=trace_id,
                    symbol=symbol,
                    all_frameworks=ta_signals["all_frameworks"],
                    all_setup_families=ta_signals["setup_families"],
                    has_smc_candidates=ta_signals["has_smc"],
                    has_snd_candidates=ta_signals["has_snd"],
                    has_macro_data=macro_signals["has_macro_data"],
                    has_cot_data=macro_signals["has_cot_data"],
                    has_rate_decision=macro_signals["has_rate_decision"],
                    has_high_impact_event=macro_signals["has_high_impact_event"],
                    has_dxy_data=macro_signals["has_dxy_data"],
                    has_qe_qt=macro_signals["has_qe_qt"],
                    has_stagflation=macro_signals["stagflation_detected"],
                    has_cot_extremes=len(macro_signals["cot_extremes"]) > 0,
                    has_tff_data=macro_signals["has_tff_data"],
                    has_core_inflation=macro_signals["has_core_inflation"],
                    has_safe_haven_elevated=macro_signals["safe_haven_elevated"],
                    has_commodity_currencies_weak=macro_signals["commodity_currencies_weak"],
                    dxy_momentum=macro_signals["dxy_momentum"] or None,
                    risk_environment=macro_signals["risk_environment"] or None,
                )
                retrieved_knowledge = bundle.model_dump(mode="json") if hasattr(bundle, "model_dump") else (bundle if isinstance(bundle, dict) else {})

                metadata: dict = {
                    "symbol": symbol,
                    "source": "dashboard_rerun",
                    "trace_id": trace_id or "",
                    "overall_trend": ta_signals["overall_trend"],
                }

                processor_input = ProcessorInput(
                    symbol=symbol,
                    ta_analysis=ta_analysis,
                    macro_analysis=macro_analysis,
                    retrieved_knowledge=retrieved_knowledge,
                    metadata=metadata,
                )
                
                # Step 4: Stream Generator
                async for partial in processor.stream_process(
                    processor_input,
                    user_id=user.user_id,
                    trace_id=trace_id,
                ):
                    yield f"data: {json.dumps(partial)}\\n\\n"
                    
            except Exception as e:
                import traceback
                logger.error("stream_failed", extra={"error": str(e), "tb": traceback.format_exc()})
                yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\\n\\n"
                
        return StreamingResponse(event_generator(), media_type="text/event-stream")

"""

if "def stream_rerun_analysis" not in text:
    text = text.replace(
        "        return {\n            \"status\": \"completed\",\n            \"symbol\": symbol,\n            \"result\": processor_dict,\n            \"output_files\": saved,\n        }",
        "        return {\n            \"status\": \"completed\",\n            \"symbol\": symbol,\n            \"result\": processor_dict,\n            \"output_files\": saved,\n        }\n" + stream_endpoint
    )
    with open(main_path, "w") as f:
        f.write(text)
    print("Patched main.py")
else:
    print("Already patched")
