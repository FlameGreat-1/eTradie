test_all_sessions_have_ranges PASSED [ 99%]
tests/ta/test_constants.py::TestSession::test_overlap_within_london_and_ny PASSED [ 99%]
tests/ta/test_orchestrator.py::test_fetch_sequence_success_primary_broker PASSED [ 99%]
tests/ta/test_orchestrator.py::test_fetch_sequence_fails_over_to_fallback PASSED [ 99%]
tests/ta/test_orchestrator.py::test_fetch_sequence_both_brokers_fail PASSED [100%]

==================================== ERRORS ====================================
__________ ERROR at setup of TestHealthEndpoints.test_health_endpoint __________
/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/pytest_asyncio/plugin.py:329: in _asyncgen_fixture_wrapper
    result = event_loop.run_until_complete(setup_task)
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/asyncio/base_events.py:691: in run_until_complete
    return future.result()
           ^^^^^^^^^^^^^^^
/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/pytest_asyncio/plugin.py:324: in setup
    res = await gen_obj.__anext__()  # type: ignore[union-attr]
          ^^^^^^^^^^^^^^^^^^^^^^^^^
tests/api/conftest.py:242: in app_client
    async with app.router.lifespan_context(app):
               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/contextlib.py:210: in __aenter__
    return await anext(self.gen)
           ^^^^^^^^^^^^^^^^^^^^^
/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/fastapi/routing.py:216: in merged_lifespan
    async with original_context(app) as maybe_original_state:
               ^^^^^^^^^^^^^^^^^^^^^
/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/contextlib.py:210: in __aenter__
    return await anext(self.gen)
           ^^^^^^^^^^^^^^^^^^^^^
/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/fastapi/routing.py:216: in merged_lifespan
    async with original_context(app) as maybe_original_state:
               ^^^^^^^^^^^^^^^^^^^^^
/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/contextlib.py:210: in __aenter__
    return await anext(self.gen)
           ^^^^^^^^^^^^^^^^^^^^^
/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/fastapi/routing.py:216: in merged_lifespan
    async with original_context(app) as maybe_original_state:
               ^^^^^^^^^^^^^^^^^^^^^
/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/contextlib.py:210: in __aenter__
    return await anext(self.gen)
           ^^^^^^^^^^^^^^^^^^^^^
/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/fastapi/routing.py:216: in merged_lifespan
    async with original_context(app) as maybe_original_state:
               ^^^^^^^^^^^^^^^^^^^^^
/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/contextlib.py:210: in __aenter__
    return await anext(self.gen)
           ^^^^^^^^^^^^^^^^^^^^^
/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/fastapi/routing.py:216: in merged_lifespan
    async with original_context(app) as maybe_original_state:
               ^^^^^^^^^^^^^^^^^^^^^
/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/contextlib.py:210: in __aenter__
    return await anext(self.gen)
           ^^^^^^^^^^^^^^^^^^^^^
/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/fastapi/routing.py:216: in merged_lifespan
    async with original_context(app) as maybe_original_state:
               ^^^^^^^^^^^^^^^^^^^^^
/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/contextlib.py:210: in __aenter__
    return await anext(self.gen)
           ^^^^^^^^^^^^^^^^^^^^^
/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/fastapi/routing.py:216: in merged_lifespan
    async with original_context(app) as maybe_original_state:
               ^^^^^^^^^^^^^^^^^^^^^
/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/contextlib.py:210: in __aenter__
    return await anext(self.gen)
           ^^^^^^^^^^^^^^^^^^^^^
/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/fastapi/routing.py:216: in merged_lifespan
    async with original_context(app) as maybe_original_state:
               ^^^^^^^^^^^^^^^^^^^^^
/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/contextlib.py:210: in __aenter__
    return await anext(self.gen)
           ^^^^^^^^^^^^^^^^^^^^^
/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/fastapi/routing.py:216: in merged_lifespan
    async with original_context(app) as maybe_original_state:
               ^^^^^^^^^^^^^^^^^^^^^
/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/contextlib.py:210: in __aenter__
    return await anext(self.gen)
           ^^^^^^^^^^^^^^^^^^^^^
/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/fastapi/routing.py:216: in merged_lifespan
    async with original_context(app) as maybe_original_state:
               ^^^^^^^^^^^^^^^^^^^^^
/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/contextlib.py:210: in __aenter__
    return await anext(self.gen)
           ^^^^^^^^^^^^^^^^^^^^^
src/engine/main.py:208: in lifespan
    await container.build_processor()
src/engine/dependencies.py:1061: in build_processor
    startup_cfg = get_processor_config()
                  ^^^^^^^^^^^^^^^^^^^^^^
src/engine/processor/config.py:296: in get_processor_config
    return ProcessorConfig()
           ^^^^^^^^^^^^^^^^^
/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/pydantic_settings/main.py:176: in __init__
    super().__init__(
E   pydantic_core._pydantic_core.ValidationError: 1 validation error for ProcessorConfig
E     Value error, Provider 'anthropic' requires PROCESSOR_ANTHROPIC_API_KEY to be set [type=value_error, input_value={}, input_type=dict]
E       For further information visit https://errors.pydantic.dev/2.9/v/value_error
---------------------------- Captured stdout setup -----------------------------
{"extra": {"trace_id": null}, "event": "db_read_error", "level": "ERROR", "logger": "engine.shared.db.connection", "timestamp": "2026-06-13T09:07:39.690116Z", "exception": "Traceback (most recent call last):\n  File \"/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/sqlalchemy/dialects/postgresql/asyncpg.py\", line 521, in _prepare_and_execute\n    prepared_stmt, attributes = await adapt_connection._prepare(\n                                ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\n  File \"/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/sqlalchemy/dialects/postgresql/asyncpg.py\", line 768, in _prepare\n    prepared_stmt = await self._connection.prepare(\n                    ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\n  File \"/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/asyncpg/connection.py\", line 635, in prepare\n    return await self._prepare(\n           ^^^^^^^^^^^^^^^^^^^^\n  File \"/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/asyncpg/connection.py\", line 653, in _prepare\n    stmt = await self._get_statement(\n           ^^^^^^^^^^^^^^^^^^^^^^^^^^\n  File \"/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/asyncpg/connection.py\", line 432, in _get_statement\n    statement = await self._protocol.prepare(\n                ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\n  File \"asyncpg/protocol/protocol.pyx\", line 165, in prepare\nasyncpg.exceptions.UndefinedTableError: relation \"broker_connections\" does not exist\n\nThe above exception was the direct cause of the following exception:\n\nTraceback (most recent call last):\n  File \"/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/sqlalchemy/engine/base.py\", line 1964, in _exec_single_context\n    self.dialect.do_execute(\n  File \"/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/sqlalchemy/engine/default.py\", line 942, in do_execute\n    cursor.execute(statement, parameters)\n  File \"/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/sqlalchemy/dialects/postgresql/asyncpg.py\", line 580, in execute\n    self._adapt_connection.await_(\n  File \"/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/sqlalchemy/util/_concurrency_py3k.py\", line 132, in await_only\n    return current.parent.switch(awaitable)  # type: ignore[no-any-return,attr-defined] # noqa: E501\n           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\n  File \"/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/sqlalchemy/util/_concurrency_py3k.py\", line 196, in greenlet_spawn\n    value = await result\n            ^^^^^^^^^^^^\n  File \"/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/sqlalchemy/dialects/postgresql/asyncpg.py\", line 558, in _prepare_and_execute\n    self._handle_exception(error)\n  File \"/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/sqlalchemy/dialects/postgresql/asyncpg.py\", line 508, in _handle_exception\n    self._adapt_connection._handle_exception(error)\n  File \"/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/sqlalchemy/dialects/postgresql/asyncpg.py\", line 792, in _handle_exception\n    raise translated_error from error\nsqlalchemy.dialects.postgresql.asyncpg.AsyncAdapt_asyncpg_dbapi.ProgrammingError: <class 'asyncpg.exceptions.UndefinedTableError'>: relation \"broker_connections\" does not exist\n\nThe above exception was the direct cause of the following exception:\n\nTraceback (most recent call last):\n  File \"/home/runner/work/eTradie/eTradie/src/engine/shared/db/connection.py\", line 244, in read_session\n    yield session\n  File \"/home/runner/work/eTradie/eTradie/src/engine/dependencies.py\", line 593, in refresh_active_user_connections\n    result = await session.execute(stmt)\n             ^^^^^^^^^^^^^^^^^^^^^^^^^^^\n  File \"/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/sqlalchemy/ext/asyncio/session.py\", line 463, in execute\n    result = await greenlet_spawn(\n             ^^^^^^^^^^^^^^^^^^^^^\n  File \"/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/sqlalchemy/util/_concurrency_py3k.py\", line 201, in greenlet_spawn\n    result = context.throw(*sys.exc_info())\n             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\n  File \"/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/sqlalchemy/orm/session.py\", line 2365, in execute\n    return self._execute_internal(\n           ^^^^^^^^^^^^^^^^^^^^^^^\n  File \"/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/sqlalchemy/orm/session.py\", line 2251, in _execute_internal\n    result: Result[Any] = compile_state_cls.orm_execute_statement(\n                          ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\n  File \"/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/sqlalchemy/orm/context.py\", line 305, in orm_execute_statement\n    result = conn.execute(\n             ^^^^^^^^^^^^^\n  File \"/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/sqlalchemy/engine/base.py\", line 1416, in execute\n    return meth(\n           ^^^^^\n  File \"/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/sqlalchemy/sql/elements.py\", line 516, in _execute_on_connection\n    return connection._execute_clauseelement(\n           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\n  File \"/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/sqlalchemy/engine/base.py\", line 1638, in _execute_clauseelement\n    ret = self._execute_context(\n          ^^^^^^^^^^^^^^^^^^^^^^\n  File \"/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/sqlalchemy/engine/base.py\", line 1843, in _execute_context\n    return self._exec_single_context(\n           ^^^^^^^^^^^^^^^^^^^^^^^^^^\n  File \"/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/sqlalchemy/engine/base.py\", line 1983, in _exec_single_context\n    self._handle_dbapi_exception(\n  File \"/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/sqlalchemy/engine/base.py\", line 2352, in _handle_dbapi_exception\n    raise sqlalchemy_exception.with_traceback(exc_info[2]) from e\n  File \"/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/sqlalchemy/engine/base.py\", line 1964, in _exec_single_context\n    self.dialect.do_execute(\n  File \"/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/sqlalchemy/engine/default.py\", line 942, in do_execute\n    cursor.execute(statement, parameters)\n  File \"/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/sqlalchemy/dialects/postgresql/asyncpg.py\", line 580, in execute\n    self._adapt_connection.await_(\n  File \"/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/sqlalchemy/util/_concurrency_py3k.py\", line 132, in await_only\n    return current.parent.switch(awaitable)  # type: ignore[no-any-return,attr-defined] # noqa: E501\n           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\n  File \"/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/sqlalchemy/util/_concurrency_py3k.py\", line 196, in greenlet_spawn\n    value = await result\n            ^^^^^^^^^^^^\n  File \"/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/sqlalchemy/dialects/postgresql/asyncpg.py\", line 558, in _prepare_and_execute\n    self._handle_exception(error)\n  File \"/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/sqlalchemy/dialects/postgresql/asyncpg.py\", line 508, in _handle_exception\n    self._adapt_connection._handle_exception(error)\n  File \"/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/sqlalchemy/dialects/postgresql/asyncpg.py\", line 792, in _handle_exception\n    raise translated_error from error\nsqlalchemy.exc.ProgrammingError: (sqlalchemy.dialects.postgresql.asyncpg.ProgrammingError) <class 'asyncpg.exceptions.UndefinedTableError'>: relation \"broker_connections\" does not exist\n[SQL: SELECT broker_connections.connection_type, count(distinct(broker_connections.user_id)) AS count_1 \nFROM broker_connections \nWHERE broker_connections.is_active IS true GROUP BY broker_connections.connection_type]\n(Background on this error at: https://sqlalche.me/e/20/f405)"}
{"extra": {"error": "VAULT_ADDR is not set", "error_type": "ConfigurationError"}, "event": "hosted_recovery_startup_failed", "level": "ERROR", "logger": "engine.main", "timestamp": "2026-06-13T09:07:39.748309Z"}
____________ ERROR at setup of TestHealthEndpoints.test_health_rag _____________
/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/pytest_asyncio/plugin.py:329: in _asyncgen_fixture_wrapper
    result = event_loop.run_until_complete(setup_task)
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/asyncio/base_events.py:691: in run_until_complete
    return future.result()
           ^^^^^^^^^^^^^^^
/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/pytest_asyncio/plugin.py:324: in setup
    res = await gen_obj.__anext__()  # type: ignore[union-attr]
          ^^^^^^^^^^^^^^^^^^^^^^^^^
tests/api/conftest.py:242: in app_client
    async with app.router.lifespan_context(app):
               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/contextlib.py:210: in __aenter__
    return await anext(self.gen)
           ^^^^^^^^^^^^^^^^^^^^^
/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/fastapi/routing.py:216: in merged_lifespan
    async with original_context(app) as maybe_original_state:
               ^^^^^^^^^^^^^^^^^^^^^
/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/contextlib.py:210: in __aenter__
    return await anext(self.gen)
           ^^^^^^^^^^^^^^^^^^^^^
/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/fastapi/routing.py:216: in merged_lifespan
    async with original_context(app) as maybe_original_state:
               ^^^^^^^^^^^^^^^^^^^^^
/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/contextlib.py:210: in __aenter__



    return await anext(self.gen)
           ^^^^^^^^^^^^^^^^^^^^^
/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/fastapi/routing.py:216: in merged_lifespan
    async with original_context(app) as maybe_original_state:
               ^^^^^^^^^^^^^^^^^^^^^
/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/contextlib.py:210: in __aenter__
    return await anext(self.gen)
           ^^^^^^^^^^^^^^^^^^^^^
/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/fastapi/routing.py:216: in merged_lifespan
    async with original_context(app) as maybe_original_state:
               ^^^^^^^^^^^^^^^^^^^^^
/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/contextlib.py:210: in __aenter__
    return await anext(self.gen)
           ^^^^^^^^^^^^^^^^^^^^^
/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/fastapi/routing.py:216: in merged_lifespan
    async with original_context(app) as maybe_original_state:
               ^^^^^^^^^^^^^^^^^^^^^
/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/contextlib.py:210: in __aenter__
    return await anext(self.gen)
           ^^^^^^^^^^^^^^^^^^^^^
/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/fastapi/routing.py:216: in merged_lifespan
    async with original_context(app) as maybe_original_state:
               ^^^^^^^^^^^^^^^^^^^^^
/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/contextlib.py:210: in __aenter__
    return await anext(self.gen)
           ^^^^^^^^^^^^^^^^^^^^^
/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/fastapi/routing.py:216: in merged_lifespan
    async with original_context(app) as maybe_original_state:
               ^^^^^^^^^^^^^^^^^^^^^
/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/contextlib.py:210: in __aenter__
    return await anext(self.gen)
           ^^^^^^^^^^^^^^^^^^^^^
/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/fastapi/routing.py:216: in merged_lifespan
    async with original_context(app) as maybe_original_state:
               ^^^^^^^^^^^^^^^^^^^^^
/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/contextlib.py:210: in __aenter__
    return await anext(self.gen)
           ^^^^^^^^^^^^^^^^^^^^^
/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/fastapi/routing.py:216: in merged_lifespan
    async with original_context(app) as maybe_original_state:
               ^^^^^^^^^^^^^^^^^^^^^
/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/contextlib.py:210: in __aenter__
    return await anext(self.gen)
           ^^^^^^^^^^^^^^^^^^^^^
/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/fastapi/routing.py:216: in merged_lifespan
    async with original_context(app) as maybe_original_state:
               ^^^^^^^^^^^^^^^^^^^^^
/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/contextlib.py:210: in __aenter__
    return await anext(self.gen)
           ^^^^^^^^^^^^^^^^^^^^^
src/engine/main.py:208: in lifespan
    await container.build_processor()
src/engine/dependencies.py:1061: in build_processor
    startup_cfg = get_processor_config()
                  ^^^^^^^^^^^^^^^^^^^^^^
src/engine/processor/config.py:296: in get_processor_config
    return ProcessorConfig()
           ^^^^^^^^^^^^^^^^^
/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/pydantic_settings/main.py:176: in __init__
    super().__init__(
E   pydantic_core._pydantic_core.ValidationError: 1 validation error for ProcessorConfig
E     Value error, Provider 'anthropic' requires PROCESSOR_ANTHROPIC_API_KEY to be set [type=value_error, input_value={}, input_type=dict]
E       For further information visit https://errors.pydantic.dev/2.9/v/value_error
---------------------------- Captured stdout setup -----------------------------
{"extra": {"trace_id": null}, "event": "db_read_error", "level": "ERROR", "logger": "engine.shared.db.connection", "timestamp": "2026-06-13T09:07:40.837953Z", "exception": "Traceback (most recent call last):\n  File \"/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/sqlalchemy/dialects/postgresql/asyncpg.py\", line 521, in _prepare_and_execute\n    prepared_stmt, attributes = await adapt_connection._prepare(\n                                ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\n  File \"/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/sqlalchemy/dialects/postgresql/asyncpg.py\", line 768, in _prepare\n    prepared_stmt = await self._connection.prepare(\n                    ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\n  File \"/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/asyncpg/connection.py\", line 635, in prepare\n    return await self._prepare(\n           ^^^^^^^^^^^^^^^^^^^^\n  File \"/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/asyncpg/connection.py\", line 653, in _prepare\n    stmt = await self._get_statement(\n           ^^^^^^^^^^^^^^^^^^^^^^^^^^\n  File \"/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/asyncpg/connection.py\", line 432, in _get_statement\n    statement = await self._protocol.prepare(\n                ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\n  File \"asyncpg/protocol/protocol.pyx\", line 165, in prepare\nasyncpg.exceptions.UndefinedTableError: relation \"broker_connections\" does not exist\n\nThe above exception was the direct cause of the following exception:\n\nTraceback (most recent call last):\n  File \"/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/sqlalchemy/engine/base.py\", line 1964, in _exec_single_context\n    self.dialect.do_execute(\n  File \"/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/sqlalchemy/engine/default.py\", line 942, in do_execute\n    cursor.execute(statement, parameters)\n  File \"/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/sqlalchemy/dialects/postgresql/asyncpg.py\", line 580, in execute\n    self._adapt_connection.await_(\n  File \"/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/sqlalchemy/util/_concurrency_py3k.py\", line 132, in await_only\n    return current.parent.switch(awaitable)  # type: ignore[no-any-return,attr-defined] # noqa: E501\n           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\n  File \"/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/sqlalchemy/util/_concurrency_py3k.py\", line 196, in greenlet_spawn\n    value = await result\n            ^^^^^^^^^^^^\n  File \"/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/sqlalchemy/dialects/postgresql/asyncpg.py\", line 558, in _prepare_and_execute\n    self._handle_exception(error)\n  File \"/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/sqlalchemy/dialects/postgresql/asyncpg.py\", line 508, in _handle_exception\n    self._adapt_connection._handle_exception(error)\n  File \"/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/sqlalchemy/dialects/postgresql/asyncpg.py\", line 792, in _handle_exception\n    raise translated_error from error\nsqlalchemy.dialects.postgresql.asyncpg.AsyncAdapt_asyncpg_dbapi.ProgrammingError: <class 'asyncpg.exceptions.UndefinedTableError'>: relation \"broker_connections\" does not exist\n\nThe above exception was the direct cause of the following exception:\n\nTraceback (most recent call last):\n  File \"/home/runner/work/eTradie/eTradie/src/engine/shared/db/connection.py\", line 244, in read_session\n    yield session\n  File \"/home/runner/work/eTradie/eTradie/src/engine/dependencies.py\", line 593, in refresh_active_user_connections\n    result = await session.execute(stmt)\n             ^^^^^^^^^^^^^^^^^^^^^^^^^^^\n  File \"/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/sqlalchemy/ext/asyncio/session.py\", line 463, in execute\n    result = await greenlet_spawn(\n             ^^^^^^^^^^^^^^^^^^^^^\n  File \"/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/sqlalchemy/util/_concurrency_py3k.py\", line 201, in greenlet_spawn\n    result = context.throw(*sys.exc_info())\n             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\n  File \"/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/sqlalchemy/orm/session.py\", line 2365, in execute\n    return self._execute_internal(\n           ^^^^^^^^^^^^^^^^^^^^^^^\n  File \"/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/sqlalchemy/orm/session.py\", line 2251, in _execute_internal\n    result: Result[Any] = compile_state_cls.orm_execute_statement(\n                          ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\n  File \"/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/sqlalchemy/orm/context.py\", line 305, in orm_execute_statement\n    result = conn.execute(\n             ^^^^^^^^^^^^^\n  File \"/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/sqlalchemy/engine/base.py\", line 1416, in execute\n    return meth(\n           ^^^^^\n  File \"/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/sqlalchemy/sql/elements.py\", line 516, in _execute_on_connection\n    return connection._execute_clauseelement(\n           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\n  File \"/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/sqlalchemy/engine/base.py\", line 1638, in _execute_clauseelement\n    ret = self._execute_context(\n          ^^^^^^^^^^^^^^^^^^^^^^\n  File \"/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/sqlalchemy/engine/base.py\", line 1843, in _execute_context\n    return self._exec_single_context(\n           ^^^^^^^^^^^^^^^^^^^^^^^^^^\n  File \"/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/sqlalchemy/engine/base.py\", line 1983, in _exec_single_context\n    self._handle_dbapi_exception(\n  File \"/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/sqlalchemy/engine/base.py\", line 2352, in _handle_dbapi_exception\n    raise sqlalchemy_exception.with_traceback(exc_info[2]) from e\n  File \"/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/sqlalchemy/engine/base.py\", line 1964, in _exec_single_context\n    self.dialect.do_execute(\n  File \"/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/sqlalchemy/engine/default.py\", line 942, in do_execute\n    cursor.execute(statement, parameters)\n  File \"/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/sqlalchemy/dialects/postgresql/asyncpg.py\", line 580, in execute\n    self._adapt_connection.await_(\n  File \"/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/sqlalchemy/util/_concurrency_py3k.py\", line 132, in await_only\n    return current.parent.switch(awaitable)  # type: ignore[no-any-return,attr-defined] # noqa: E501\n           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\n  File \"/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/sqlalchemy/util/_concurrency_py3k.py\", line 196, in greenlet_spawn\n    value = await result\n            ^^^^^^^^^^^^\n  File \"/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/sqlalchemy/dialects/postgresql/asyncpg.py\", line 558, in _prepare_and_execute\n    self._handle_exception(error)\n  File \"/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/sqlalchemy/dialects/postgresql/asyncpg.py\", line 508, in _handle_exception\n    self._adapt_connection._handle_exception(error)\n  File \"/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/sqlalchemy/dialects/postgresql/asyncpg.py\", line 792, in _handle_exception\n    raise translated_error from error\nsqlalchemy.exc.ProgrammingError: (sqlalchemy.dialects.postgresql.asyncpg.ProgrammingError) <class 'asyncpg.exceptions.UndefinedTableError'>: relation \"broker_connections\" does not exist\n[SQL: SELECT broker_connections.connection_type, count(distinct(broker_connections.user_id)) AS count_1 \nFROM broker_connections \nWHERE broker_connections.is_active IS true GROUP BY broker_connections.connection_type]\n(Background on this error at: https://sqlalche.me/e/20/f405)"}
{"extra": {"error": "VAULT_ADDR is not set", "error_type": "ConfigurationError"}, "event": "hosted_recovery_startup_failed", "level": "ERROR", "logger": "engine.main", "timestamp": "2026-06-13T09:07:40.885886Z"}
------------------------------ Captured log setup ------------------------------
ERROR    engine.shared.db.connection:connection.py:251 {'extra': {'trace_id': None}, 'event': 'db_read_error', 'level': 'ERROR', 'logger': 'engine.shared.db.connection', 'timestamp': '2026-06-13T09:07:40.837953Z', 'exception': 'Traceback (most recent call last):\n  File "/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/sqlalchemy/dialects/postgresql/asyncpg.py", line 521, in _prepare_and_execute\n    prepared_stmt, attributes = await adapt_connection._prepare(\n                                ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\n  File "/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/sqlalchemy/dialects/postgresql/asyncpg.py", line 768, in _prepare\n    prepared_stmt = await self._connection.prepare(\n                    ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\n  File "/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/asyncpg/connection.py", line 635, in prepare\n    return await self._prepare(\n           ^^^^^^^^^^^^^^^^^^^^\n  File "/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/asyncpg/connection.py", line 653, in _prepare\n    stmt = await self._get_statement(\n           ^^^^^^^^^^^^^^^^^^^^^^^^^^\n  File "/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/asyncpg/connection.py", line 432, in _get_statement\n    statement = await self._protocol.prepare(\n                ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\n  File "asyncpg/protocol/protocol.pyx", line 165, in prepare\nasyncpg.exceptions.UndefinedTableError: relation "broker_connections" does not exist\n\nThe above exception was the direct cause of the following exception:\n\nTraceback (most recent call last):\n  File "/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/sqlalchemy/engine/base.py", line 1964, in _exec_single_context\n    self.dialect.do_execute(\n  File "/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/sqlalchemy/engine/default.py", line 942, in do_execute\n    cursor.execute(statement, parameters)\n  File "/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/sqlalchemy/dialects/postgresql/asyncpg.py", line 580, in execute\n    self._adapt_connection.await_(\n  File "/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/sqlalchemy/util/_concurrency_py3k.py", line 132, in await_only\n    return current.parent.switch(awaitable)  # type: ignore[no-any-return,attr-defined] # noqa: E501\n           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\n  File "/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/sqlalchemy/util/_concurrency_py3k.py", line 196, in greenlet_spawn\n    value = await result\n            ^^^^^^^^^^^^\n  File "/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/sqlalchemy/dialects/postgresql/asyncpg.py", line 558, in _prepare_and_execute\n    self._handle_exception(error)\n  File "/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/sqlalchemy/dialects/postgresql/asyncpg.py", line 508, in _handle_exception\n    self._adapt_connection._handle_exception(error)\n  File "/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/sqlalchemy/dialects/postgresql/asyncpg.py", line 792, in _handle_exception\n    raise translated_error from error\nsqlalchemy.dialects.postgresql.asyncpg.AsyncAdapt_asyncpg_dbapi.ProgrammingError: <class \'asyncpg.exceptions.UndefinedTableError\'>: relation "broker_connections" does not exist\n\nThe above exception was the direct cause of the following exception:\n\nTraceback (most recent call last):\n  File "/home/runner/work/eTradie/eTradie/src/engine/shared/db/connection.py", line 244, in read_session\n    yield session\n  File "/home/runner/work/eTradie/eTradie/src/engine/dependencies.py", line 593, in refresh_active_user_connections\n    result = await session.execute(stmt)\n             ^^^^^^^^^^^^^^^^^^^^^^^^^^^\n  File "/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/sqlalchemy/ext/asyncio/session.py", line 463, in execute\n    result = await greenlet_spawn(\n             ^^^^^^^^^^^^^^^^^^^^^\n  File "/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/sqlalchemy/util/_concurrency_py3k.py", line 201, in greenlet_spawn\n    result = context.throw(*sys.exc_info())\n             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\n  File "/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/sqlalchemy/orm/session.py", line 2365, in execute\n    return self._execute_internal(\n           ^^^^^^^^^^^^^^^^^^^^^^^\n  File "/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/sqlalchemy/orm/session.py", line 2251, in _execute_internal\n    result: Result[Any] = compile_state_cls.orm_execute_statement(\n                          ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\n  File "/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/sqlalchemy/orm/context.py", line 305, in orm_execute_statement\n    result = conn.execute(\n             ^^^^^^^^^^^^^\n  File "/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/sqlalchemy/engine/base.py", line 1416, in execute\n    return meth(\n           ^^^^^\n  File "/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/sqlalchemy/sql/elements.py", line 516, in _execute_on_connection\n    return connection._execute_clauseelement(\n           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\n  File "/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/sqlalchemy/engine/base.py", line 1638, in _execute_clauseelement\n    ret = self._execute_context(\n          ^^^^^^^^^^^^^^^^^^^^^^\n  File "/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/sqlalchemy/engine/base.py", line 1843, in _execute_context\n    return self._exec_single_context(\n           ^^^^^^^^^^^^^^^^^^^^^^^^^^\n  File "/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/sqlalchemy/engine/base.py", line 1983, in _exec_single_context\n    self._handle_dbapi_exception(\n  File "/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/sqlalchemy/engine/base.py", line 2352, in _handle_dbapi_exception\n    raise sqlalchemy_exception.with_traceback(exc_info[2]) from e\n  File "/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/sqlalchemy/engine/base.py", line 1964, in _exec_single_context\n    self.dialect.do_execute(\n  File "/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/sqlalchemy/engine/default.py", line 942, in do_execute\n    cursor.execute(statement, parameters)\n  File "/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/sqlalchemy/dialects/postgresql/asyncpg.py", line 580, in execute\n    self._adapt_connection.await_(\n  File "/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/sqlalchemy/util/_concurrency_py3k.py", line 132, in await_only\n    return current.parent.switch(awaitable)  # type: ignore[no-any-return,attr-defined] # noqa: E501\n           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\n  File "/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/sqlalchemy/util/_concurrency_py3k.py", line 196, in greenlet_spawn\n    value = await result\n            ^^^^^^^^^^^^\n  File "/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/sqlalchemy/dialects/postgresql/asyncpg.py", line 558, in _prepare_and_execute\n    self._handle_exception(error)\n  File "/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/sqlalchemy/dialects/postgresql/asyncpg.py", line 508, in _handle_exception\n    self._adapt_connection._handle_exception(error)\n  File "/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/sqlalchemy/dialects/postgresql/asyncpg.py", line 792, in _handle_exception\n    raise translated_error from error\nsqlalchemy.exc.ProgrammingError: (sqlalchemy.dialects.postgresql.asyncpg.ProgrammingError) <class \'asyncpg.exceptions.UndefinedTableError\'>: relation "broker_connections" does not exist\n[SQL: SELECT broker_connections.connection_type, count(distinct(broker_connections.user_id)) AS count_1 \nFROM broker_connections \nWHERE broker_connections.is_active IS true GROUP BY broker_connections.connection_type]\n(Background on this error at: https://sqlalche.me/e/20/f405)'}
Traceback (most recent call last):
  File "/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/sqlalchemy/dialects/postgresql/asyncpg.py", line 521, in _prepare_and_execute
    prepared_stmt, attributes = await adapt_connection._prepare(
                                ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/sqlalchemy/dialects/postgresql/asyncpg.py", line 768, in _prepare
    prepared_stmt = await self._connection.prepare(
                    ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/asyncpg/connection.py", line 635, in prepare
    return await self._prepare(
           ^^^^^^^^^^^^^^^^^^^^
  File "/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/asyncpg/connection.py", line 653, in _prepare
    stmt = await self._get_statement(
           ^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/asyncpg/connection.py", line 432, in _get_statement
    statement = await self._protocol.prepare(
                ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "asyncpg/protocol/protocol.pyx", line 165, in prepare
asyncpg.exceptions.UndefinedTableError: relation "broker_connections" does not exist

The above exception was the direct cause of the following exception:

Traceback (most recent call last):
  File "/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/sqlalchemy/engine/base.py", line 1964, in _exec_single_context
    self.dialect.do_execute(
  File "/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/sqlalchemy/engine/default.py", line 942, in do_execute
    cursor.execute(statement, parameters)
  File "/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/sqlalchemy/dialects/postgresql/asyncpg.py", line 580, in execute
    self._adapt_connection.await_(
  File "/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/sqlalchemy/util/_concurrency_py3k.py", line 132, in await_only
    return current.parent.switch(awaitable)  # type: ignore[no-any-return,attr-defined] # noqa: E501
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/sqlalchemy/util/_concurrency_py3k.py", line 196, in greenlet_spawn
    value = await result
            ^^^^^^^^^^^^
  File "/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/sqlalchemy/dialects/postgresql/asyncpg.py", line 558, in _prepare_and_execute
    self._handle_exception(error)
  File "/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/sqlalchemy/dialects/postgresql/asyncpg.py", line 508, in _handle_exception
    self._adapt_connection._handle_exception(error)
  File "/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/sqlalchemy/dialects/postgresql/asyncpg.py", line 792, in _handle_exception
    raise translated_error from error
sqlalchemy.dialects.postgresql.asyncpg.AsyncAdapt_asyncpg_dbapi.ProgrammingError: <class 'asyncpg.exceptions.UndefinedTableError'>: relation "broker_connections" does not exist

The above exception was the direct cause of the following exception:

Traceback (most recent call last):
  File "/home/runner/work/eTradie/eTradie/src/engine/shared/db/connection.py", line 244, in read_session
    yield session
  File "/home/runner/work/eTradie/eTradie/src/engine/dependencies.py", line 593, in refresh_active_user_connections
    result = await session.execute(stmt)
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/sqlalchemy/ext/asyncio/session.py", line 463, in execute
    result = await greenlet_spawn(
             ^^^^^^^^^^^^^^^^^^^^^
  File "/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/sqlalchemy/util/_concurrency_py3k.py", line 201, in greenlet_spawn
    result = context.throw(*sys.exc_info())
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/sqlalchemy/orm/session.py", line 2365, in execute
    return self._execute_internal(


 context.throw(*sys.exc_info())
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/sqlalchemy/orm/session.py", line 2365, in execute
    return self._execute_internal(
           ^^^^^^^^^^^^^^^^^^^^^^^
  File "/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/sqlalchemy/orm/session.py", line 2251, in _execute_internal
    result: Result[Any] = compile_state_cls.orm_execute_statement(
                          ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/sqlalchemy/orm/context.py", line 305, in orm_execute_statement
    result = conn.execute(
             ^^^^^^^^^^^^^
  File "/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/sqlalchemy/engine/base.py", line 1416, in execute
    return meth(
           ^^^^^
  File "/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/sqlalchemy/sql/elements.py", line 516, in _execute_on_connection
    return connection._execute_clauseelement(
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/sqlalchemy/engine/base.py", line 1638, in _execute_clauseelement
    ret = self._execute_context(
          ^^^^^^^^^^^^^^^^^^^^^^
  File "/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/sqlalchemy/engine/base.py", line 1843, in _execute_context
    return self._exec_single_context(
           ^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/sqlalchemy/engine/base.py", line 1983, in _exec_single_context
    self._handle_dbapi_exception(
  File "/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/sqlalchemy/engine/base.py", line 2352, in _handle_dbapi_exception
    raise sqlalchemy_exception.with_traceback(exc_info[2]) from e
  File "/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/sqlalchemy/engine/base.py", line 1964, in _exec_single_context
    self.dialect.do_execute(
  File "/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/sqlalchemy/engine/default.py", line 942, in do_execute
    cursor.execute(statement, parameters)
  File "/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/sqlalchemy/dialects/postgresql/asyncpg.py", line 580, in execute
    self._adapt_connection.await_(
  File "/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/sqlalchemy/util/_concurrency_py3k.py", line 132, in await_only
    return current.parent.switch(awaitable)  # type: ignore[no-any-return,attr-defined] # noqa: E501
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/sqlalchemy/util/_concurrency_py3k.py", line 196, in greenlet_spawn
    value = await result
            ^^^^^^^^^^^^
  File "/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/sqlalchemy/dialects/postgresql/asyncpg.py", line 558, in _prepare_and_execute
    self._handle_exception(error)
  File "/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/sqlalchemy/dialects/postgresql/asyncpg.py", line 508, in _handle_exception
    self._adapt_connection._handle_exception(error)
  File "/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/sqlalchemy/dialects/postgresql/asyncpg.py", line 792, in _handle_exception
    raise translated_error from error
sqlalchemy.exc.ProgrammingError: (sqlalchemy.dialects.postgresql.asyncpg.ProgrammingError) <class 'asyncpg.exceptions.UndefinedTableError'>: relation "broker_connections" does not exist
[SQL: SELECT broker_connections.connection_type, count(distinct(broker_connections.user_id)) AS count_1 
FROM broker_connections 
WHERE broker_connections.is_active IS true GROUP BY broker_connections.connection_type]
(Background on this error at: https://sqlalche.me/e/20/f405)
ERROR    engine.main:main.py:203 {'extra': {'error': 'VAULT_ADDR is not set', 'error_type': 'ConfigurationError'}, 'event': 'hosted_recovery_startup_failed', 'level': 'ERROR', 'logger': 'engine.main', 'timestamp': '2026-06-13T09:07:40.885886Z'}
__________ ERROR at setup of TestAnalysisLatest.test_analysis_latest ___________
/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/pytest_asyncio/plugin.py:329: in _asyncgen_fixture_wrapper
    result = event_loop.run_until_complete(setup_task)
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/asyncio/base_events.py:691: in run_until_complete
    return future.result()
           ^^^^^^^^^^^^^^^
/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/pytest_asyncio/plugin.py:324: in setup
    res = await gen_obj.__anext__()  # type: ignore[union-attr]
          ^^^^^^^^^^^^^^^^^^^^^^^^^
tests/api/conftest.py:242: in app_client
    async with app.router.lifespan_context(app):
               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/contextlib.py:210: in __aenter__
    return await anext(self.gen)
           ^^^^^^^^^^^^^^^^^^^^^
/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/fastapi/routing.py:216: in merged_lifespan
    async with original_context(app) as maybe_original_state:
               ^^^^^^^^^^^^^^^^^^^^^
/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/contextlib.py:210: in __aenter__
    return await anext(self.gen)
           ^^^^^^^^^^^^^^^^^^^^^
/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/fastapi/routing.py:216: in merged_lifespan
    async with original_context(app) as maybe_original_state:
               ^^^^^^^^^^^^^^^^^^^^^
/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/contextlib.py:210: in __aenter__
    return await anext(self.gen)
           ^^^^^^^^^^^^^^^^^^^^^
/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/fastapi/routing.py:216: in merged_lifespan
    async with original_context(app) as maybe_original_state:
               ^^^^^^^^^^^^^^^^^^^^^
/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/contextlib.py:210: in __aenter__
    return await anext(self.gen)
           ^^^^^^^^^^^^^^^^^^^^^
/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/fastapi/routing.py:216: in merged_lifespan
    async with original_context(app) as maybe_original_state:
               ^^^^^^^^^^^^^^^^^^^^^
/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/contextlib.py:210: in __aenter__
    return await anext(self.gen)
           ^^^^^^^^^^^^^^^^^^^^^
/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/fastapi/routing.py:216: in merged_lifespan
    async with original_context(app) as maybe_original_state:
               ^^^^^^^^^^^^^^^^^^^^^
/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/contextlib.py:210: in __aenter__
    return await anext(self.gen)
           ^^^^^^^^^^^^^^^^^^^^^
/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/fastapi/routing.py:216: in merged_lifespan
    async with original_context(app) as maybe_original_state:
               ^^^^^^^^^^^^^^^^^^^^^
/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/contextlib.py:210: in __aenter__
    return await anext(self.gen)
           ^^^^^^^^^^^^^^^^^^^^^
/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/fastapi/routing.py:216: in merged_lifespan
    async with original_context(app) as maybe_original_state:
               ^^^^^^^^^^^^^^^^^^^^^
/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/contextlib.py:210: in __aenter__
    return await anext(self.gen)
           ^^^^^^^^^^^^^^^^^^^^^
/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/fastapi/routing.py:216: in merged_lifespan
    async with original_context(app) as maybe_original_state:
               ^^^^^^^^^^^^^^^^^^^^^
/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/contextlib.py:210: in __aenter__
    return await anext(self.gen)
           ^^^^^^^^^^^^^^^^^^^^^
/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/fastapi/routing.py:216: in merged_lifespan
    async with original_context(app) as maybe_original_state:
               ^^^^^^^^^^^^^^^^^^^^^
/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/contextlib.py:210: in __aenter__
    return await anext(self.gen)
           ^^^^^^^^^^^^^^^^^^^^^
/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/fastapi/routing.py:216: in merged_lifespan
    async with original_context(app) as maybe_original_state:
               ^^^^^^^^^^^^^^^^^^^^^
/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/contextlib.py:210: in __aenter__
    return await anext(self.gen)
           ^^^^^^^^^^^^^^^^^^^^^
src/engine/main.py:208: in lifespan
    await container.build_processor()
src/engine/dependencies.py:1061: in build_processor
    startup_cfg = get_processor_config()
                  ^^^^^^^^^^^^^^^^^^^^^^
src/engine/processor/config.py:296: in get_processor_config

   return ProcessorConfig()
           ^^^^^^^^^^^^^^^^^
/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/pydantic_settings/main.py:176: in __init__
    super().__init__(
E   pydantic_core._pydantic_core.ValidationError: 1 validation error for ProcessorConfig
E     Value error, Provider 'anthropic' requires PROCESSOR_ANTHROPIC_API_KEY to be set [type=value_error, input_value={}, input_type=dict]
E       For further information visit https://errors.pydantic.dev/2.9/v/value_error
---------------------------- Captured stdout setup -----------------------------
{"extra": {"trace_id": null}, "event": "db_read_error", "level": "ERROR", "logger": "engine.shared.db.connection", "timestamp": "2026-06-13T09:07:41.620554Z", "exception": "Traceback (most recent call last):\n  File \"/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/sqlalchemy/dialects/postgresql/asyncpg.py\", line 521, in _prepare_and_execute\n    prepared_stmt, attributes = await adapt_connection._prepare(\n                                ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\n  File \"/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/sqlalchemy/dialects/postgresql/asyncpg.py\", line 768, in _prepare\n    prepared_stmt = await self._connection.prepare(\n                    ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\n  File \"/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/asyncpg/connection.py\", line 635, in prepare\n    return await self._prepare(\n           ^^^^^^^^^^^^^^^^^^^^\n  File \"/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/asyncpg/connection.py\", line 653, in _prepare\n    stmt = await self._get_statement(\n           ^^^^^^^^^^^^^^^^^^^^^^^^^^\n  File \"/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/asyncpg/connection.py\", line 432, in _get_statement\n    statement = await self._protocol.prepare(\n                ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\n  File \"asyncpg/protocol/protocol.pyx\", line 165, in prepare\nasyncpg.exceptions.UndefinedTableError: relation \"broker_connections\" does not exist\n\nThe above exception was the direct cause of the following exception:\n\nTraceback (most recent call last):\n  File \"/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/sqlalchemy/engine/base.py\", line 1964, in _exec_single_context\n    self.dialect.do_execute(\n  File \"/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/sqlalchemy/engine/default.py\", line 942, in do_execute\n    cursor.execute(statement, parameters)\n  File \"/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/sqlalchemy/dialects/postgresql/asyncpg.py\", line 580, in execute\n    self._adapt_connection.await_(\n  File \"/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/sqlalchemy/util/_concurrency_py3k.py\", line 132, in await_only\n    return current.parent.switch(awaitable)  # type: ignore[no-any-return,attr-defined] # noqa: E501\n           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\n  File \"/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/sqlalchemy/util/_concurrency_py3k.py\", line 196, in greenlet_spawn\n    value = await result\n            ^^^^^^^^^^^^\n  File \"/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/sqlalchemy/dialects/postgresql/asyncpg.py\", line 558, in _prepare_and_execute\n    self._handle_exception(error)\n  File \"/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/sqlalchemy/dialects/postgresql/asyncpg.py\", line 508, in _handle_exception\n    self._adapt_connection._handle_exception(error)\n  File \"/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/sqlalchemy/dialects/postgresql/asyncpg.py\", line 792, in _handle_exception\n    raise translated_error from error\nsqlalchemy.dialects.postgresql.asyncpg.AsyncAdapt_asyncpg_dbapi.ProgrammingError: <class 'asyncpg.exceptions.UndefinedTableError'>: relation \"broker_connections\" does not exist\n\nThe above exception was the direct cause of the following exception:\n\nTraceback (most recent call last):\n  File \"/home/runner/work/eTradie/eTradie/src/engine/shared/db/connection.py\", line 244, in read_session\n    yield session\n  File \"/home/runner/work/eTradie/eTradie/src/engine/dependencies.py\", line 593, in refresh_active_user_connections\n    result = await session.execute(stmt)\n             ^^^^^^^^^^^^^^^^^^^^^^^^^^^\n  File \"/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/sqlalchemy/ext/asyncio/session.py\", line 463, in execute\n    result = await greenlet_spawn(\n             ^^^^^^^^^^^^^^^^^^^^^\n  File \"/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/sqlalchemy/util/_concurrency_py3k.py\", line 201, in greenlet_spawn\n    result = context.throw(*sys.exc_info())\n             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\n  File \"/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/sqlalchemy/orm/session.py\", line 2365, in execute\n    return self._execute_internal(\n           ^^^^^^^^^^^^^^^^^^^^^^^\n  File \"/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/sqlalchemy/orm/session.py\", line 2251, in _execute_internal\n    result: Result[Any] = compile_state_cls.orm_execute_statement(\n                          ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\n  File \"/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/sqlalchemy/orm/context.py\", line 305, in orm_execute_statement\n    result = conn.execute(\n             ^^^^^^^^^^^^^\n  File \"/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/sqlalchemy/engine/base.py\", line 1416, in execute\n    return meth(\n           ^^^^^\n  File \"/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/sqlalchemy/sql/elements.py\", line 516, in _execute_on_connection\n    return connection._execute_clauseelement(\n           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\n  File \"/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/sqlalchemy/engine/base.py\", line 1638, in _execute_clauseelement\n    ret = self._execute_context(\n          ^^^^^^^^^^^^^^^^^^^^^^\n  File \"/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/sqlalchemy/engine/base.py\", line 1843, in _execute_context\n    return self._exec_single_context(\n           ^^^^^^^^^^^^^^^^^^^^^^^^^^\n  File \"/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/sqlalchemy/engine/base.py\", line 1983, in _exec_single_context\n    self._handle_dbapi_exception(\n  File \"/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/sqlalchemy/engine/base.py\", line 2352, in _handle_dbapi_exception\n    raise sqlalchemy_exception.with_traceback(exc_info[2]) from e\n  File \"/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/sqlalchemy/engine/base.py\", line 1964, in _exec_single_context\n    self.dialect.do_execute(\n  File \"/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/sqlalchemy/engine/default.py\", line 942, in do_execute\n    cursor.execute(statement, parameters)\n  File \"/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/sqlalchemy/dialects/postgresql/asyncpg.py\", line 580, in execute\n    self._adapt_connection.await_(\n  File \"/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/sqlalchemy/util/_concurrency_py3k.py\", line 132, in await_only\n    return current.parent.switch(awaitable)  # type: ignore[no-any-return,attr-defined] # noqa: E501\n           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\n  File \"/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/sqlalchemy/util/_concurrency_py3k.py\", line 196, in greenlet_spawn\n    value = await result\n            ^^^^^^^^^^^^\n  File \"/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/sqlalchemy/dialects/postgresql/asyncpg.py\", line 558, in _prepare_and_execute\n    self._handle_exception(error)\n  File \"/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/sqlalchemy/dialects/postgresql/asyncpg.py\", line 508, in _handle_exception\n    self._adapt_connection._handle_exception(error)\n  File \"/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/sqlalchemy/dialects/postgresql/asyncpg.py\", line 792, in _handle_exception\n    raise translated_error from error\nsqlalchemy.exc.ProgrammingError: (sqlalchemy.dialects.postgresql.asyncpg.ProgrammingError) <class 'asyncpg.exceptions.UndefinedTableError'>: relation \"broker_connections\" does not exist\n[SQL: SELECT broker_connections.connection_type, count(distinct(broker_connections.user_id)) AS count_1 \nFROM broker_connections \nWHERE broker_connections.is_active IS true GROUP BY broker_connections.connection_type]\n(Background on this error at: https://sqlalche.me/e/20/f405)"}
{"extra": {"error": "VAULT_ADDR is not set", "error_type": "ConfigurationError"}, "event": "hosted_recovery_startup_failed", "level": "ERROR", "logger": "engine.main", "timestamp": "2026-06-13T09:07:41.669911Z"}
------------------------------ Captured log setup ------------------------------
ERROR    engine.shared.db.connection:connection.py:251 {'extra': {'trace_id': None}, 'event': 'db_read_error', 'level': 'ERROR', 'logger': 'engine.shared.db.connection', 'timestamp': '2026-06-13T09:07:41.620554Z', 'exception': 'Traceback (most recent call last):\n  File "/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/sqlalchemy/dialects/postgresql/asyncpg.py", line 521, in _prepare_and_execute\n    prepared_stmt, attributes = await adapt_connection._prepare(\n                                ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\n  File "/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/sqlalchemy/dialects/postgresql/asyncpg.py", line 768, in _prepare\n    prepared_stmt = await self._connection.prepare(\n                    ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\n  File "/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/asyncpg/connection.py", line 635, in prepare\n    return await self._prepare(\n           ^^^^^^^^^^^^^^^^^^^^\n  File "/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/asyncpg/connection.py", line 653, in _prepare\n    stmt = await self._get_statement(\n           ^^^^^^^^^^^^^^^^^^^^^^^^^^\n  File "/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/asyncpg/connection.py", line 432, in _get_statement\n    statement = await self._protocol.prepare(\n                ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\n  File "asyncpg/protocol/protocol.pyx", line 165, in prepare\nasyncpg.exceptions.UndefinedTableError: relation "broker_connections" does not exist\n\nThe above exception was the direct cause of the following exception:\n\nTraceback (most recent call last):\n  File "/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/sqlalchemy/engine/base.py", line 1964, in _exec_single_context\n    self.dialect.do_execute(\n  File "/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/sqlalchemy/engine/default.py", line 942, in do_execute\n    cursor.execute(statement, parameters)\n  File "/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/sqlalchemy/dialects/postgresql/asyncpg.py", line 580, in execute\n    self._adapt_connection.await_(\n  File "/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/sqlalchemy/util/_concurrency_py3k.py", line 132, in await_only\n    return current.parent.switch(awaitable)  # type: ignore[no-any-return,attr-defined] # noqa: E501\n           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\n  File "/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/sqlalchemy/util/_concurrency_py3k.py", line 196, in greenlet_spawn\n    value = await result\n            ^^^^^^^^^^^^\n  File "/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/sqlalchemy/dialects/postgresql/asyncpg.py", line 558, in _prepare_and_execute\n    self._handle_exception(error)\n  File "/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/sqlalchemy/dialects/postgresql/asyncpg.py", line 508, in _handle_exception\n    self._adapt_connection._handle_exception(error)\n  File "/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/sqlalchemy/dialects/postgresql/asyncpg.py", line 792, in _handle_exception\n    raise translated_error from error\nsqlalchemy.dialects.postgresql.asyncpg.AsyncAdapt_asyncpg_dbapi.ProgrammingError: <class \'asyncpg.exceptions.UndefinedTableError\'>: relation "broker_connections" does not exist\n\nThe above exception was the direct cause of the following exception:\n\nTraceback (most recent call last):\n  File "/home/runner/work/eTradie/eTradie/src/engine/shared/db/connection.py", line 244, in read_session\n    yield session\n  File "/home/runner/work/eTradie/eTradie/src/engine/dependencies.py", line 593, in refresh_active_user_connections\n    result = await session.execute(stmt)\n             ^^^^^^^^^^^^^^^^^^^^^^^^^^^\n  File "/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/sqlalchemy/ext/asyncio/session.py", line 463, in execute\n    result = await greenlet_spawn(\n             ^^^^^^^^^^^^^^^^^^^^^\n  File "/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/sqlalchemy/util/_concurrency_py3k.py", line 201, in greenlet_spawn\n    result = context.throw(*sys.exc_info())\n             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\n  File "/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/sqlalchemy/orm/session.py", line 2365, in execute\n    return self._execute_internal(\n           ^^^^^^^^^^^^^^^^^^^^^^^\n  File "/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/sqlalchemy/orm/session.py", line 2251, in _execute_internal\n    result: Result[Any] = compile_state_cls.orm_execute_statement(\n                          ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\n  File "/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/sqlalchemy/orm/context.py", line 305, in orm_execute_statement\n    result = conn.execute(\n             ^^^^^^^^^^^^^\n  File "/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/sqlalchemy/engine/base.py", line 1416, in execute\n    return meth(\n           ^^^^^\n  File "/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/sqlalchemy/sql/elements.py", line 516, in _execute_on_connection\n    return connection._execute_clauseelement(\n           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\n  File "/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/sqlalchemy/engine/base.py", line 1638, in _execute_clauseelement\n    ret = self._execute_context(\n          ^^^^^^^^^^^^^^^^^^^^^^\n  File "/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/sqlalchemy/engine/base.py", line 1843, in _execute_context\n    return self._exec_single_context(\n           ^^^^^^^^^^^^^^^^^^^^^^^^^^\n  File "/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/sqlalchemy/engine/base.py", line 1983, in _exec_single_context\n    self._handle_dbapi_exception(\n  File "/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/sqlalchemy/engine/base.py", line 2352, in _handle_dbapi_exception\n    raise sqlalchemy_exception.with_traceback(exc_info[2]) from e\n  File "/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/sqlalchemy/engine/base.py", line 1964, in _exec_single_context\n    self.dialect.do_execute(\n  File "/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/sqlalchemy/engine/default.py", line 942, in do_execute\n    cursor.execute(statement, parameters)\n  File "/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/sqlalchemy/dialects/postgresql/asyncpg.py", line 580, in execute\n    self._adapt_connection.await_(\n  File "/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/sqlalchemy/util/_concurrency_py3k.py", line 132, in await_only\n    return current.parent.switch(awaitable)  # type: ignore[no-any-return,attr-defined] # noqa: E501\n           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\n  File "/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/sqlalchemy/util/_concurrency_py3k.py", line 196, in greenlet_spawn\n    value = await result\n            ^^^^^^^^^^^^\n  File "/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/sqlalchemy/dialects/postgresql/asyncpg.py", line 558, in _prepare_and_execute\n    self._handle_exception(error)\n  File "/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/sqlalchemy/dialects/postgresql/asyncpg.py", line 508, in _handle_exception\n    self._adapt_connection._handle_exception(error)\n  File "/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/sqlalchemy/dialects/postgresql/asyncpg.py", line 792, in _handle_exception\n    raise translated_error from error\nsqlalchemy.exc.ProgrammingError: (sqlalchemy.dialects.postgresql.asyncpg.ProgrammingError) <class \'asyncpg.exceptions.UndefinedTableError\'>: relation "broker_connections" does not exist\n[SQL: SELECT broker_connections.connection_type, count(distinct(broker_connections.user_id)) AS count_1 \nFROM broker_connections \nWHERE broker_connections.is_active IS true GROUP BY broker_connections.connection_type]\n(Background on this error at: https://sqlalche.me/e/20/f405)'}
Traceback (most recent call last):
  File "/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/sqlalchemy/dialects/postgresql/asyncpg.py", line 521, in _prepare_and_execute
    prepared_stmt, attributes = await adapt_connection._prepare(
                                ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/sqlalchemy/dialects/postgresql/asyncpg.py", line 768, in _prepare
    prepared_stmt = await self._connection.prepare(
                    ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/asyncpg/connection.py", line 635, in prepare
    return await self._prepare(
           ^^^^^^^^^^^^^^^^^^^^
  File "/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/asyncpg/connection.py", line 653, in _prepare
    stmt = await self._get_statement(
           ^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/asyncpg/connection.py", line 432, in _get_statement
    statement = await self._protocol.prepare(
                ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "asyncpg/protocol/protocol.pyx", line 165, in prepare
asyncpg.exceptions.UndefinedTableError: relation "broker_connections" does not exist

The above exception was the direct cause of the following exception:

Traceback (most recent call last):
  File "/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/sqlalchemy/engine/base.py", line 1964, in _exec_single_context
    self.dialect.do_execute(
  File "/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/sqlalchemy/engine/default.py", line 942, in do_execute
    cursor.execute(statement, parameters)
  File "/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/sqlalchemy/dialects/postgresql/asyncpg.py", line 580, in execute
    self._adapt_connection.await_(
  File "/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/sqlalchemy/util/_concurrency_py3k.py", line 132, in await_only
    return current.parent.switch(awaitable)  # type: ignore[no-any-return,attr-defined] # noqa: E501
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/sqlalchemy/util/_concurrency_py3k.py", line 196, in greenlet_spawn
    value = await result
            ^^^^^^^^^^^^
  File "/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/sqlalchemy/dialects/postgresql/asyncpg.py", line 558, in _prepare_and_execute
    self._handle_exception(error)
  File "/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/sqlalchemy/dialects/postgresql/asyncpg.py", line 508, in _handle_exception
    self._adapt_connection._handle_exception(error)
  File "/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/sqlalchemy/dialects/postgresql/asyncpg.py", line 792, in _handle_exception
    raise translated_error from error
sqlalchemy.dialects.postgresql.asyncpg.AsyncAdapt_asyncpg_dbapi.ProgrammingError: <class 'asyncpg.exceptions.UndefinedTableError'>: relation "broker_connections" does not exist

The above exception was the direct cause of the following exception:

Traceback (most recent call last):
  File "/home/runner/work/eTradie/eTradie/src/engine/shared/db/connection.py", line 244, in read_session
    yield session
  File "/home/runner/work/eTradie/eTradie/src/engine/dependencies.py", line 593, in refresh_active_user_connections
    result = await session.execute(stmt)
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/sqlalchemy/ext/asyncio/session.py", line 463, in execute
    result = await greenlet_spawn(
             ^^^^^^^^^^^^^^^^^^^^^
  File "/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/sqlalchemy/util/_concurrency_py3k.py", line 201, in greenlet_spawn
    result = context.throw(*sys.exc_info())
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/sqlalchemy/orm/session.py", line 2365, in execute
    return self._execute_internal(
           ^^^^^^^^^^^^^^^^^^^^^^^
  File "/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/sqlalchemy/orm/session.py", line 2251, in _execute_internal
    result: Result[Any] = compile_state_cls.orm_execute_statement(
                          ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/sqlalchemy/orm/context.py", line 305, in orm_execute_statement
    result = conn.execute(
             ^^^^^^^^^^^^^
  File "/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/sqlalchemy/engine/base.py", line 1416, in execute
    return meth(
           ^^^^^
  File "/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/sqlalchemy/sql/elements.py", line 516, in _execute_on_connection
    return connection._execute_clauseelement(
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/sqlalchemy/engine/base.py", line 1638, in _execute_clauseelement
    ret = self._execute_context(
          ^^^^^^^^^^^^^^^^^^^^^^
  File "/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/sqlalchemy/engine/base.py", line 1843, in _execute_context
    return self._exec_single_context(
           ^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/sqlalchemy/engine/base.py", line 1983, in _exec_single_context
    self._handle_dbapi_exception(
  File "/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/sqlalchemy/engine/base.py", line 2352, in _handle_dbapi_exception
    raise sqlalchemy_exception.with_traceback(exc_info[2]) from e
  File "/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/sqlalchemy/engine/base.py", line 1964, in _exec_single_context
    self.dialect.do_execute(
  File "/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/sqlalchemy/engine/default.py", line 942, in do_execute
    cursor.execute(statement, parameters)
  File "/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/sqlalchemy/dialects/postgresql/asyncpg.py", line 580, in execute
    self._adapt_connection.await_(
  File "/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/sqlalchemy/util/_concurrency_py3k.py", line 132, in await_only
    return current.parent.switch(awaitable)  # type: ignore[no-any-return,attr-defined] # noqa: E501
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/sqlalchemy/util/_concurrency_py3k.py", line 196, in greenlet_spawn
    value = await result
            ^^^^^^^^^^^^






      0      0      0   100%
src/engine/ta/storage/schemas/candle.py                                        25      0      0      0   100%
src/engine/ta/storage/schemas/snapshot.py                                      38      0      0      0   100%
src/engine/ta/storage/uow.py                                                  117     74     20      0    31%   35-41, 45-47, 51-53, 57-59, 63-65, 68-77, 80-89, 107-113, 117-119, 123-125, 129-131, 135-137, 140-149, 152-161, 172, 181
src/engine/verify_chroma.py                                                    23     23     10      0     0%   1-38
-----------------------------------------------------------------------------------------------------------------------
TOTAL                                                                       24865  13541   6260    385    39%

=========================== short test summary info ============================
FAILED tests/chaos/test_prometheusrule_renders.py::test_mt_node_chart_renders_memory_leak_rule - AssertionError: helm template mt-node failed: Error: execution error at (mt-node/templates/externalsecret-platform.yaml:11:18): helm/mt-node: .Values.externalSecrets.platform.vaultPath is required when externalSecrets.enabled=true. Set it to etradie/services/mt-node/<env>.
  
  Use --debug flag to render out invalid YAML
  
assert 1 == 0
 +  where 1 = CompletedProcess(args=['helm', 'template', 'release', '/home/runner/work/eTradie/eTradie/helm/mt-node', '--namespace', 'etradie-system', '--set', 'image.repository=ghcr.io/ci-stub/etradie-mt-node', '--set', 'mtConnection.enabled=true', '--set', 'mtConnection.connectionId=test-1234567890', '--set', 'mtConnection.userId=u-1', '--set', 'mtConnection.server=Exness-MT5Trial9', '--set', 'mtConnection.sealedSecretName=test-secret'], returncode=1, stdout='', stderr='Error: execution error at (mt-node/templates/externalsecret-platform.yaml:11:18): helm/mt-node: .Values.externalSecrets.platform.vaultPath is required when externalSecrets.enabled=true. Set it to etradie/services/mt-node/<env>.\n\nUse --debug flag to render out invalid YAML\n').returncode
FAILED tests/chaos/test_watchdog_broker_disconnect_inproc.py::test_watchdog_terminates_mt_on_consecutive_health_failures - pytest.PytestUnraisableExceptionWarning: Exception ignored in: <coroutine object HostedRecoveryService._loop at 0x7f6b1bfa33d0>
Enable tracemalloc to get traceback where the object was allocated.
See https://docs.pytest.org/en/stable/how-to/capture-warnings.html#resource-warnings for more info.
FAILED tests/ta/broker/test_mt5_config.py::TestMT5ConfigProviderValidation::test_metaapi_provider_requires_token - Failed: DID NOT RAISE <class 'pydantic_core._pydantic_core.ValidationError'>
ERROR tests/api/test_dashboard_api.py::TestHealthEndpoints::test_health_endpoint - pydantic_core._pydantic_core.ValidationError: 1 validation error for ProcessorConfig
  Value error, Provider 'anthropic' requires PROCESSOR_ANTHROPIC_API_KEY to be set [type=value_error, input_value={}, input_type=dict]
    For further information visit https://errors.pydantic.dev/2.9/v/value_error
ERROR tests/api/test_dashboard_api.py::TestHealthEndpoints::test_health_rag - pydantic_core._pydantic_core.ValidationError: 1 validation error for ProcessorConfig
  Value error, Provider 'anthropic' requires PROCESSOR_ANTHROPIC_API_KEY to be set [type=value_error, input_value={}, input_type=dict]
    For further information visit https://errors.pydantic.dev/2.9/v/value_error
ERROR tests/api/test_dashboard_api.py::TestAnalysisLatest::test_analysis_latest - pydantic_core._pydantic_core.ValidationError: 1 validation error for ProcessorConfig
  Value error, Provider 'anthropic' requires PROCESSOR_ANTHROPIC_API_KEY to be set [type=value_error, input_value={}, input_type=dict]
    For further information visit https://errors.pydantic.dev/2.9/v/value_error
ERROR tests/api/test_dashboard_api.py::TestAnalysisLatest::test_analysis_latest_filter_by_pair - pydantic_core._pydantic_core.ValidationError: 1 validation error for ProcessorConfig
  Value error, Provider 'anthropic' requires PROCESSOR_ANTHROPIC_API_KEY to be set [type=value_error, input_value={}, input_type=dict]
    For further information visit https://errors.pydantic.dev/2.9/v/value_error
ERROR tests/api/test_dashboard_api.py::TestAnalysisLatest::test_analysis_latest_limit - pydantic_core._pydantic_core.ValidationError: 1 validation error for ProcessorConfig
  Value error, Provider 'anthropic' requires PROCESSOR_ANTHROPIC_API_KEY to be set [type=value_error, input_value={}, input_type=dict]
    For further information visit https://errors.pydantic.dev/2.9/v/value_error
ERROR tests/api/test_dashboard_api.py::TestAnalysisHistory::test_analysis_history - pydantic_core._pydantic_core.ValidationError: 1 validation error for ProcessorConfig
  Value error, Provider 'anthropic' requires PROCESSOR_ANTHROPIC_API_KEY to be set [type=value_error, input_value={}, input_type=dict]
    For further information visit https://errors.pydantic.dev/2.9/v/value_error
ERROR tests/api/test_dashboard_api.py::TestAnalysisHistory::test_analysis_history_filter_status - pydantic_core._pydantic_core.ValidationError: 1 validation error for ProcessorConfig
  Value error, Provider 'anthropic' requires PROCESSOR_ANTHROPIC_API_KEY to be set [type=value_error, input_value={}, input_type=dict]
    For further information visit https://errors.pydantic.dev/2.9/v/value_error
ERROR tests/api/test_dashboard_api.py::TestAnalysisHistory::test_analysis_history_filter_grade - pydantic_core._pydantic_core.ValidationError: 1 validation error for ProcessorConfig
  Value error, Provider 'anthropic' requires PROCESSOR_ANTHROPIC_API_KEY to be set [type=value_error, input_value={}, input_type=dict]
    For further information visit https://errors.pydantic.dev/2.9/v/value_error
ERROR tests/api/test_dashboard_api.py::TestAnalysisHistory::test_analysis_history_filter_provider - pydantic_core._pydantic_core.ValidationError: 1 validation error for ProcessorConfig
  Value error, Provider 'anthropic' requires PROCESSOR_ANTHROPIC_API_KEY to be set [type=value_error, input_value={}, input_type=dict]
    For further information visit https://errors.pydantic.dev/2.9/v/value_error
ERROR tests/api/test_dashboard_api.py::TestAnalysisHistory::test_analysis_history_pagination - pydantic_core._pydantic_core.ValidationError: 1 validation error for ProcessorConfig
  Value error, Provider 'anthropic' requires PROCESSOR_ANTHROPIC_API_KEY to be set [type=value_error, input_value={}, input_type=dict]
    For further information visit https://errors.pydantic.dev/2.9/v/value_error
ERROR tests/api/test_dashboard_api.py::TestAnalysisStats::test_analysis_stats - pydantic_core._pydantic_core.ValidationError: 1 validation error for ProcessorConfig
  Value error, Provider 'anthropic' requires PROCESSOR_ANTHROPIC_API_KEY to be set [type=value_error, input_value={}, input_type=dict]
    For further information visit https://errors.pydantic.dev/2.9/v/value_error
ERROR tests/api/test_dashboard_api.py::TestAnalysisStats::test_analysis_stats_filter_pair - pydantic_core._pydantic_core.ValidationError: 1 validation error for ProcessorConfig
  Value error, Provider 'anthropic' requires PROCESSOR_ANTHROPIC_API_KEY to be set [type=value_error, input_value={}, input_type=dict]
    For further information visit https://errors.pydantic.dev/2.9/v/value_error
ERROR tests/api/test_dashboard_api.py::TestAnalysisDetail::test_analysis_detail - pydantic_core._pydantic_core.ValidationError: 1 validation error for ProcessorConfig
  Value error, Provider 'anthropic' requires PROCESSOR_ANTHROPIC_API_KEY to be set [type=value_error, input_value={}, input_type=dict]
    For further information visit https://errors.pydantic.dev/2.9/v/value_error
ERROR tests/api/test_dashboard_api.py::TestAnalysisDetail::test_analysis_detail_not_found - pydantic_core._pydantic_core.ValidationError: 1 validation error for ProcessorConfig
  Value error, Provider 'anthropic' requires PROCESSOR_ANTHROPIC_API_KEY to be set [type=value_error, input_value={}, input_type=dict]
    For further information visit https://errors.pydantic.dev/2.9/v/value_error
ERROR tests/api/test_dashboard_api.py::TestAnalysisRerun::test_analysis_rerun_ta_unavailable - pydantic_core._pydantic_core.ValidationError: 1 validation error for ProcessorConfig
  Value error, Provider 'anthropic' requires PROCESSOR_ANTHROPIC_API_KEY to be set [type=value_error, input_value={}, input_type=dict]
    For further information visit https://errors.pydantic.dev/2.9/v/value_error
ERROR tests/api/test_dashboard_api.py::TestAnalysisRerun::test_analysis_rerun_empty_symbol - pydantic_core._pydantic_core.ValidationError: 1 validation error for ProcessorConfig
  Value error, Provider 'anthropic' requires PROCESSOR_ANTHROPIC_API_KEY to be set [type=value_error, input_value={}, input_type=dict]
    For further information visit https://errors.pydantic.dev/2.9/v/value_error
ERROR tests/api/test_dashboard_api.py::TestAnalysisRerun::test_analysis_rerun_no_auth - pydantic_core._pydantic_core.ValidationError: 1 validation error for ProcessorConfig
  Value error, Provider 'anthropic' requires PROCESSOR_ANTHROPIC_API_KEY to be set [type=value_error, input_value={}, input_type=dict]
    For further information visit https://errors.pydantic.dev/2.9/v/value_error
ERROR tests/api/test_dashboard_api.py::TestProcessorConfig::test_processor_models - pydantic_core._pydantic_core.ValidationError: 1 validation error for ProcessorConfig
  Value error, Provider 'anthropic' requires PROCESSOR_ANTHROPIC_API_KEY to be set [type=value_error, input_value={}, input_type=dict]
    For further information visit https://errors.pydantic.dev/2.9/v/value_error
ERROR tests/api/test_dashboard_api.py::TestProcessorConfig::test_processor_config_get - pydantic_core._pydantic_core.ValidationError: 1 validation error for ProcessorConfig
  Value error, Provider 'anthropic' requires PROCESSOR_ANTHROPIC_API_KEY to be set [type=value_error, input_value={}, input_type=dict]
    For further information visit https://errors.pydantic.dev/2.9/v/value_error
ERROR tests/api/test_dashboard_api.py::TestProcessorConfig::test_processor_config_update_temperature - pydantic_core._pydantic_core.ValidationError: 1 validation error for ProcessorConfig
  Value error, Provider 'anthropic' requires PROCESSOR_ANTHROPIC_API_KEY to be set [type=value_error, input_value={}, input_type=dict]
    For further information visit https://errors.pydantic.dev/2.9/v/value_error
ERROR tests/api/test_dashboard_api.py::TestProcessorConfig::test_processor_config_update_invalid_provider - pydantic_core._pydantic_core.ValidationError: 1 validation error for ProcessorConfig
  Value error, Provider 'anthropic' requires PROCESSOR_ANTHROPIC_API_KEY to be set [type=value_error, input_value={}, input_type=dict]
    For further information visit https://errors.pydantic.dev/2.9/v/value_error
ERROR tests/api/test_dashboard_api.py::TestProcessorConfig::test_regular_user_rejected_from_processor_models - pydantic_core._pydantic_core.ValidationError: 1 validation error for ProcessorConfig
  Value error, Provider 'anthropic' requires PROCESSOR_ANTHROPIC_API_KEY to be set [type=value_error, input_value={}, input_type=dict]
    For further information visit https://errors.pydantic.dev/2.9/v/value_error
ERROR tests/api/test_dashboard_api.py::TestProcessorConfig::test_regular_user_rejected_from_processor_config_get - pydantic_core._pydantic_core.ValidationError: 1 validation error for ProcessorConfig
  Value error, Provider 'anthropic' requires PROCESSOR_ANTHROPIC_API_KEY to be set [type=value_error, input_value={}, input_type=dict]
    For further information visit https://errors.pydantic.dev/2.9/v/value_error
ERROR tests/api/test_dashboard_api.py::TestProcessorConfig::test_regular_user_rejected_from_processor_config_put - pydantic_core._pydantic_core.ValidationError: 1 validation error for ProcessorConfig
  Value error, Provider 'anthropic' requires PROCESSOR_ANTHROPIC_API_KEY to be set [type=value_error, input_value={}, input_type=dict]
    For further information visit https://errors.pydantic.dev/2.9/v/value_error
ERROR tests/api/test_dashboard_api.py::TestProcessorConfig::test_no_auth_returns_401 - pydantic_core._pydantic_core.ValidationError: 1 validation error for ProcessorConfig
  Value error, Provider 'anthropic' requires PROCESSOR_ANTHROPIC_API_KEY to be set [type=value_error, input_value={}, input_type=dict]
    For further information visit https://errors.pydantic.dev/2.9/v/value_error
======= 3 failed, 496 passed, 23 skipped, 25 errors in 70.50s (0:01:10) ========
Error: Process completed with exit code 1.
0s
