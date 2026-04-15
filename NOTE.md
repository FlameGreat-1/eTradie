[engine.ta.storage.repositories.candidate] extra={'symbol': 'US30X10M', 'pattern': 'SOP', 'direction': 'BEARISH'}
etradie-engine  | 2026-04-15T17:20:09.461275Z [DEBUG    ] snd_candidate_created          [engine.ta.storage.repositories.candidate] extra={'symbol': 'US30X10M', 'pattern': 'SOP', 'direction': 'BEARISH'}
etradie-engine  | 2026-04-15T17:20:09.467098Z [DEBUG    ] snd_candidate_created          [engine.ta.storage.repositories.candidate] extra={'symbol': 'US30X10M', 'pattern': 'QML_BASELINE', 'direction': 'BEARISH'}
etradie-engine  | 2026-04-15T17:20:09.471155Z [DEBUG    ] snd_candidate_created          [engine.ta.storage.repositories.candidate] extra={'symbol': 'US30X10M', 'pattern': 'QML_KILLER_TYPE2', 'direction': 'BEARISH'}
etradie-engine  | 2026-04-15T17:20:09.473593Z [DEBUG    ] snd_candidate_duplicate_skipped [engine.ta.storage.repositories.candidate] extra={'symbol': 'US30X10M', 'pattern': 'QMH_BASELINE', 'entry_price': 46509.3}
etradie-engine  | 2026-04-15T17:20:09.473952Z [ERROR    ] snd_candidate_persistence_failed [engine.ta.orchestrator] extra={'symbol': 'US30X10M', 'pattern': 'QMH_BASELINE', 'error': 'This result object is closed.'}
etradie-engine  | Traceback (most recent call last):
etradie-engine  |   File "/app/src/engine/ta/orchestrator.py", line 1065, in _persist_all_results
etradie-engine  |     await uow.candidate_repo.create_snd_candidate(
etradie-engine  |   File "/app/src/engine/ta/storage/repositories/candidate.py", line 152, in create_snd_candidate
etradie-engine  |     return existing.scalar_one_or_none()
etradie-engine  |            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 1485, in scalar_one_or_none
etradie-engine  |     return self._only_one_row(
etradie-engine  |            ^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 749, in _only_one_row
etradie-engine  |     row: Optional[_InterimRowType[Any]] = onerow(hard_close=True)
etradie-engine  |                                           ^^^^^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 2255, in _fetchone_impl
etradie-engine  |     self._raise_hard_closed()
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 2241, in _raise_hard_closed
etradie-engine  |     raise exc.ResourceClosedError("This result object is closed.")
etradie-engine  | sqlalchemy.exc.ResourceClosedError: This result object is closed.
etradie-engine  | 2026-04-15T17:20:09.480310Z [DEBUG    ] snd_candidate_duplicate_skipped [engine.ta.storage.repositories.candidate] extra={'symbol': 'US30X10M', 'pattern': 'QMH_BASELINE', 'entry_price': 47649.1}
etradie-engine  | 2026-04-15T17:20:09.480651Z [ERROR    ] snd_candidate_persistence_failed [engine.ta.orchestrator] extra={'symbol': 'US30X10M', 'pattern': 'QMH_BASELINE', 'error': 'This result object is closed.'}
etradie-engine  | Traceback (most recent call last):
etradie-engine  |   File "/app/src/engine/ta/orchestrator.py", line 1065, in _persist_all_results
etradie-engine  |     await uow.candidate_repo.create_snd_candidate(
etradie-engine  |   File "/app/src/engine/ta/storage/repositories/candidate.py", line 152, in create_snd_candidate
etradie-engine  |     return existing.scalar_one_or_none()
etradie-engine  |            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 1485, in scalar_one_or_none
etradie-engine  |     return self._only_one_row(
etradie-engine  |            ^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 749, in _only_one_row
etradie-engine  |     row: Optional[_InterimRowType[Any]] = onerow(hard_close=True)
etradie-engine  |                                           ^^^^^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 2255, in _fetchone_impl
etradie-engine  |     self._raise_hard_closed()
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 2241, in _raise_hard_closed
etradie-engine  |     raise exc.ResourceClosedError("This result object is closed.")
etradie-engine  | sqlalchemy.exc.ResourceClosedError: This result object is closed.
etradie-engine  | 2026-04-15T17:20:09.484777Z [DEBUG    ] snd_candidate_duplicate_skipped [engine.ta.storage.repositories.candidate] extra={'symbol': 'US30X10M', 'pattern': 'QMH_BASELINE', 'entry_price': 47854.7}
etradie-engine  | 2026-04-15T17:20:09.485143Z [ERROR    ] snd_candidate_persistence_failed [engine.ta.orchestrator] extra={'symbol': 'US30X10M', 'pattern': 'QMH_BASELINE', 'error': 'This result object is closed.'}
etradie-engine  | Traceback (most recent call last):
etradie-engine  |   File "/app/src/engine/ta/orchestrator.py", line 1065, in _persist_all_results
etradie-engine  |     await uow.candidate_repo.create_snd_candidate(
etradie-engine  |   File "/app/src/engine/ta/storage/repositories/candidate.py", line 152, in create_snd_candidate
etradie-engine  |     return existing.scalar_one_or_none()
etradie-engine  |            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 1485, in scalar_one_or_none
etradie-engine  |     return self._only_one_row(
etradie-engine  |            ^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 749, in _only_one_row
etradie-engine  |     row: Optional[_InterimRowType[Any]] = onerow(hard_close=True)
etradie-engine  |                                           ^^^^^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 2255, in _fetchone_impl
etradie-engine  |     self._raise_hard_closed()
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 2241, in _raise_hard_closed
etradie-engine  |     raise exc.ResourceClosedError("This result object is closed.")
etradie-engine  | sqlalchemy.exc.ResourceClosedError: This result object is closed.
etradie-engine  | 2026-04-15T17:20:09.489436Z [DEBUG    ] snd_candidate_duplicate_skipped [engine.ta.storage.repositories.candidate] extra={'symbol': 'US30X10M', 'pattern': 'QMH_BASELINE', 'entry_price': 48091.1}
etradie-engine  | 2026-04-15T17:20:09.489808Z [ERROR    ] snd_candidate_persistence_failed [engine.ta.orchestrator] extra={'symbol': 'US30X10M', 'pattern': 'QMH_BASELINE', 'error': 'This result object is closed.'}
etradie-engine  | Traceback (most recent call last):
etradie-engine  |   File "/app/src/engine/ta/orchestrator.py", line 1065, in _persist_all_results
etradie-engine  |     await uow.candidate_repo.create_snd_candidate(
etradie-engine  |   File "/app/src/engine/ta/storage/repositories/candidate.py", line 152, in create_snd_candidate
etradie-engine  |     return existing.scalar_one_or_none()
etradie-engine  |            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 1485, in scalar_one_or_none
etradie-engine  |     return self._only_one_row(
etradie-engine  |            ^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 749, in _only_one_row
etradie-engine  |     row: Optional[_InterimRowType[Any]] = onerow(hard_close=True)
etradie-engine  |                                           ^^^^^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 2255, in _fetchone_impl
etradie-engine  |     self._raise_hard_closed()
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 2241, in _raise_hard_closed
etradie-engine  |     raise exc.ResourceClosedError("This result object is closed.")
etradie-engine  | sqlalchemy.exc.ResourceClosedError: This result object is closed.
etradie-engine  | 2026-04-15T17:20:09.496088Z [DEBUG    ] snd_candidate_duplicate_skipped [engine.ta.storage.repositories.candidate] extra={'symbol': 'US30X10M', 'pattern': 'QMH_BASELINE', 'entry_price': 47543.5}
etradie-engine  | 2026-04-15T17:20:09.496631Z [ERROR    ] snd_candidate_persistence_failed [engine.ta.orchestrator] extra={'symbol': 'US30X10M', 'pattern': 'QMH_BASELINE', 'error': 'This result object is closed.'}
etradie-engine  | Traceback (most recent call last):
etradie-engine  |   File "/app/src/engine/ta/orchestrator.py", line 1065, in _persist_all_results
etradie-engine  |     await uow.candidate_repo.create_snd_candidate(
etradie-engine  |   File "/app/src/engine/ta/storage/repositories/candidate.py", line 152, in create_snd_candidate
etradie-engine  |     return existing.scalar_one_or_none()
etradie-engine  |            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 1485, in scalar_one_or_none
etradie-engine  |     return self._only_one_row(
etradie-engine  |            ^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 749, in _only_one_row
etradie-engine  |     row: Optional[_InterimRowType[Any]] = onerow(hard_close=True)
etradie-engine  |                                           ^^^^^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 2255, in _fetchone_impl
etradie-engine  |     self._raise_hard_closed()
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 2241, in _raise_hard_closed
etradie-engine  |     raise exc.ResourceClosedError("This result object is closed.")
etradie-engine  | sqlalchemy.exc.ResourceClosedError: This result object is closed.
etradie-engine  | 2026-04-15T17:20:09.502171Z [DEBUG    ] snd_candidate_duplicate_skipped [engine.ta.storage.repositories.candidate] extra={'symbol': 'US30X10M', 'pattern': 'QMH_BASELINE', 'entry_price': 48226.2}
etradie-engine  | 2026-04-15T17:20:09.502678Z [ERROR    ] snd_candidate_persistence_failed [engine.ta.orchestrator] extra={'symbol': 'US30X10M', 'pattern': 'QMH_BASELINE', 'error': 'This result object is closed.'}
etradie-engine  | Traceback (most recent call last):
etradie-engine  |   File "/app/src/engine/ta/orchestrator.py", line 1065, in _persist_all_results
etradie-engine  |     await uow.candidate_repo.create_snd_candidate(
etradie-engine  |   File "/app/src/engine/ta/storage/repositories/candidate.py", line 152, in create_snd_candidate
etradie-engine  |     return existing.scalar_one_or_none()
etradie-engine  |            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 1485, in scalar_one_or_none
etradie-engine  |     return self._only_one_row(
etradie-engine  |            ^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 749, in _only_one_row
etradie-engine  |     row: Optional[_InterimRowType[Any]] = onerow(hard_close=True)
etradie-engine  |                                           ^^^^^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 2255, in _fetchone_impl
etradie-engine  |     self._raise_hard_closed()
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 2241, in _raise_hard_closed
etradie-engine  |     raise exc.ResourceClosedError("This result object is closed.")
etradie-engine  | sqlalchemy.exc.ResourceClosedError: This result object is closed.
etradie-engine  | 2026-04-15T17:20:09.507486Z [DEBUG    ] snd_candidate_duplicate_skipped [engine.ta.storage.repositories.candidate] extra={'symbol': 'US30X10M', 'pattern': 'QMH_KILLER_TYPE2', 'entry_price': 48226.2}
etradie-engine  | 2026-04-15T17:20:09.508131Z [ERROR    ] snd_candidate_persistence_failed [engine.ta.orchestrator] extra={'symbol': 'US30X10M', 'pattern': 'QMH_KILLER_TYPE2', 'error': 'This result object is closed.'}
etradie-engine  | Traceback (most recent call last):
etradie-engine  |   File "/app/src/engine/ta/orchestrator.py", line 1065, in _persist_all_results
etradie-engine  |     await uow.candidate_repo.create_snd_candidate(
etradie-engine  |   File "/app/src/engine/ta/storage/repositories/candidate.py", line 152, in create_snd_candidate
etradie-engine  |     return existing.scalar_one_or_none()
etradie-engine  |            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 1485, in scalar_one_or_none
etradie-engine  |     return self._only_one_row(
etradie-engine  |            ^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 749, in _only_one_row
etradie-engine  |     row: Optional[_InterimRowType[Any]] = onerow(hard_close=True)
etradie-engine  |                                           ^^^^^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 2255, in _fetchone_impl
etradie-engine  |     self._raise_hard_closed()
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 2241, in _raise_hard_closed
etradie-engine  |     raise exc.ResourceClosedError("This result object is closed.")
etradie-engine  | sqlalchemy.exc.ResourceClosedError: This result object is closed.
etradie-engine  | 2026-04-15T17:20:09.515356Z [DEBUG    ] snd_candidate_duplicate_skipped [engine.ta.storage.repositories.candidate] extra={'symbol': 'US30X10M', 'pattern': 'SOP', 'entry_price': 47626.8}
etradie-engine  | 2026-04-15T17:20:09.515839Z [ERROR    ] snd_candidate_persistence_failed [engine.ta.orchestrator] extra={'symbol': 'US30X10M', 'pattern': 'SOP', 'error': 'This result object is closed.'}
etradie-engine  | Traceback (most recent call last):
etradie-engine  |   File "/app/src/engine/ta/orchestrator.py", line 1065, in _persist_all_results
etradie-engine  |     await uow.candidate_repo.create_snd_candidate(
etradie-engine  |   File "/app/src/engine/ta/storage/repositories/candidate.py", line 152, in create_snd_candidate
etradie-engine  |     return existing.scalar_one_or_none()
etradie-engine  |            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 1485, in scalar_one_or_none
etradie-engine  |     return self._only_one_row(
etradie-engine  |            ^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 749, in _only_one_row
etradie-engine  |     row: Optional[_InterimRowType[Any]] = onerow(hard_close=True)
etradie-engine  |                                           ^^^^^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 2255, in _fetchone_impl
etradie-engine  |     self._raise_hard_closed()
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 2241, in _raise_hard_closed
etradie-engine  |     raise exc.ResourceClosedError("This result object is closed.")
etradie-engine  | sqlalchemy.exc.ResourceClosedError: This result object is closed.
etradie-engine  | 2026-04-15T17:20:09.522231Z [DEBUG    ] snd_candidate_duplicate_skipped [engine.ta.storage.repositories.candidate] extra={'symbol': 'US30X10M', 'pattern': 'SOP', 'entry_price': 47782.9}
etradie-engine  | 2026-04-15T17:20:09.523029Z [ERROR    ] snd_candidate_persistence_failed [engine.ta.orchestrator] extra={'symbol': 'US30X10M', 'pattern': 'SOP', 'error': 'This result object is closed.'}
etradie-engine  | Traceback (most recent call last):
etradie-engine  |   File "/app/src/engine/ta/orchestrator.py", line 1065, in _persist_all_results
etradie-engine  |     await uow.candidate_repo.create_snd_candidate(
etradie-engine  |   File "/app/src/engine/ta/storage/repositories/candidate.py", line 152, in create_snd_candidate
etradie-engine  |     return existing.scalar_one_or_none()
etradie-engine  |            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 1485, in scalar_one_or_none
etradie-engine  |     return self._only_one_row(
etradie-engine  |            ^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 749, in _only_one_row
etradie-engine  |     row: Optional[_InterimRowType[Any]] = onerow(hard_close=True)
etradie-engine  |                                           ^^^^^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 2255, in _fetchone_impl
etradie-engine  |     self._raise_hard_closed()
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 2241, in _raise_hard_closed
etradie-engine  |     raise exc.ResourceClosedError("This result object is closed.")
etradie-engine  | sqlalchemy.exc.ResourceClosedError: This result object is closed.
etradie-engine  | 2026-04-15T17:20:09.530009Z [DEBUG    ] snd_candidate_created          [engine.ta.storage.repositories.candidate] extra={'symbol': 'US30X10M', 'pattern': 'SND_CONTINUATION', 'direction': 'BULLISH'}
etradie-engine  | 2026-04-15T17:20:09.532873Z [DEBUG    ] snd_candidate_duplicate_skipped [engine.ta.storage.repositories.candidate] extra={'symbol': 'US30X10M', 'pattern': 'SOP', 'entry_price': 47952.8}
etradie-engine  | 2026-04-15T17:20:09.533193Z [ERROR    ] snd_candidate_persistence_failed [engine.ta.orchestrator] extra={'symbol': 'US30X10M', 'pattern': 'SOP', 'error': 'This result object is closed.'}
etradie-engine  | Traceback (most recent call last):
etradie-engine  |   File "/app/src/engine/ta/orchestrator.py", line 1065, in _persist_all_results
etradie-engine  |     await uow.candidate_repo.create_snd_candidate(
etradie-engine  |   File "/app/src/engine/ta/storage/repositories/candidate.py", line 152, in create_snd_candidate
etradie-engine  |     return existing.scalar_one_or_none()
etradie-engine  |            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 1485, in scalar_one_or_none
etradie-engine  |     return self._only_one_row(
etradie-engine  |            ^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 749, in _only_one_row
etradie-engine  |     row: Optional[_InterimRowType[Any]] = onerow(hard_close=True)
etradie-engine  |                                           ^^^^^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 2255, in _fetchone_impl
etradie-engine  |     self._raise_hard_closed()
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 2241, in _raise_hard_closed
etradie-engine  |     raise exc.ResourceClosedError("This result object is closed.")
etradie-engine  | sqlalchemy.exc.ResourceClosedError: This result object is closed.
etradie-engine  | 2026-04-15T17:20:09.538761Z [DEBUG    ] snd_candidate_duplicate_skipped [engine.ta.storage.repositories.candidate] extra={'symbol': 'US30X10M', 'pattern': 'SOP', 'entry_price': 48070.4}
etradie-engine  | 2026-04-15T17:20:09.539303Z [ERROR    ] snd_candidate_persistence_failed [engine.ta.orchestrator] extra={'symbol': 'US30X10M', 'pattern': 'SOP', 'error': 'This result object is closed.'}
etradie-engine  | Traceback (most recent call last):
etradie-engine  |   File "/app/src/engine/ta/orchestrator.py", line 1065, in _persist_all_results
etradie-engine  |     await uow.candidate_repo.create_snd_candidate(
etradie-engine  |   File "/app/src/engine/ta/storage/repositories/candidate.py", line 152, in create_snd_candidate
etradie-engine  |     return existing.scalar_one_or_none()
etradie-engine  |            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 1485, in scalar_one_or_none
etradie-engine  |     return self._only_one_row(
etradie-engine  |            ^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 749, in _only_one_row
etradie-engine  |     row: Optional[_InterimRowType[Any]] = onerow(hard_close=True)
etradie-engine  |                                           ^^^^^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 2255, in _fetchone_impl
etradie-engine  |     self._raise_hard_closed()
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 2241, in _raise_hard_closed
etradie-engine  |     raise exc.ResourceClosedError("This result object is closed.")
etradie-engine  | sqlalchemy.exc.ResourceClosedError: This result object is closed.
etradie-engine  | 2026-04-15T17:20:09.544174Z [DEBUG    ] snd_candidate_duplicate_skipped [engine.ta.storage.repositories.candidate] extra={'symbol': 'US30X10M', 'pattern': 'SOP', 'entry_price': 47968.5}
etradie-engine  | 2026-04-15T17:20:09.544543Z [ERROR    ] snd_candidate_persistence_failed [engine.ta.orchestrator] extra={'symbol': 'US30X10M', 'pattern': 'SOP', 'error': 'This result object is closed.'}
etradie-engine  | Traceback (most recent call last):
etradie-engine  |   File "/app/src/engine/ta/orchestrator.py", line 1065, in _persist_all_results
etradie-engine  |     await uow.candidate_repo.create_snd_candidate(
etradie-engine  |   File "/app/src/engine/ta/storage/repositories/candidate.py", line 152, in create_snd_candidate
etradie-engine  |     return existing.scalar_one_or_none()
etradie-engine  |            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 1485, in scalar_one_or_none
etradie-engine  |     return self._only_one_row(
etradie-engine  |            ^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 749, in _only_one_row
etradie-engine  |     row: Optional[_InterimRowType[Any]] = onerow(hard_close=True)
etradie-engine  |                                           ^^^^^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 2255, in _fetchone_impl
etradie-engine  |     self._raise_hard_closed()
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 2241, in _raise_hard_closed
etradie-engine  |     raise exc.ResourceClosedError("This result object is closed.")
etradie-engine  | sqlalchemy.exc.ResourceClosedError: This result object is closed.
etradie-engine  | 2026-04-15T17:20:09.549125Z [DEBUG    ] snd_candidate_duplicate_skipped [engine.ta.storage.repositories.candidate] extra={'symbol': 'US30X10M', 'pattern': 'SOP', 'entry_price': 47967.7}
etradie-engine  | 2026-04-15T17:20:09.549482Z [ERROR    ] snd_candidate_persistence_failed [engine.ta.orchestrator] extra={'symbol': 'US30X10M', 'pattern': 'SOP', 'error': 'This result object is closed.'}
etradie-engine  | Traceback (most recent call last):
etradie-engine  |   File "/app/src/engine/ta/orchestrator.py", line 1065, in _persist_all_results
etradie-engine  |     await uow.candidate_repo.create_snd_candidate(
etradie-engine  |   File "/app/src/engine/ta/storage/repositories/candidate.py", line 152, in create_snd_candidate
etradie-engine  |     return existing.scalar_one_or_none()
etradie-engine  |            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 1485, in scalar_one_or_none
etradie-engine  |     return self._only_one_row(
etradie-engine  |            ^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 749, in _only_one_row
etradie-engine  |     row: Optional[_InterimRowType[Any]] = onerow(hard_close=True)
etradie-engine  |                                           ^^^^^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 2255, in _fetchone_impl
etradie-engine  |     self._raise_hard_closed()
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 2241, in _raise_hard_closed
etradie-engine  |     raise exc.ResourceClosedError("This result object is closed.")
etradie-engine  | sqlalchemy.exc.ResourceClosedError: This result object is closed.
etradie-engine  | 2026-04-15T17:20:09.555885Z [DEBUG    ] snd_candidate_duplicate_skipped [engine.ta.storage.repositories.candidate] extra={'symbol': 'US30X10M', 'pattern': 'SOP', 'entry_price': 47949.7}
etradie-engine  | 2026-04-15T17:20:09.556202Z [ERROR    ] snd_candidate_persistence_failed [engine.ta.orchestrator] extra={'symbol': 'US30X10M', 'pattern': 'SOP', 'error': 'This result object is closed.'}
etradie-engine  | Traceback (most recent call last):
etradie-engine  |   File "/app/src/engine/ta/orchestrator.py", line 1065, in _persist_all_results
etradie-engine  |     await uow.candidate_repo.create_snd_candidate(
etradie-engine  |   File "/app/src/engine/ta/storage/repositories/candidate.py", line 152, in create_snd_candidate
etradie-engine  |     return existing.scalar_one_or_none()
etradie-engine  |            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 1485, in scalar_one_or_none
etradie-engine  |     return self._only_one_row(
etradie-engine  |            ^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 749, in _only_one_row
etradie-engine  |     row: Optional[_InterimRowType[Any]] = onerow(hard_close=True)
etradie-engine  |                                           ^^^^^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 2255, in _fetchone_impl
etradie-engine  |     self._raise_hard_closed()
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 2241, in _raise_hard_closed
etradie-engine  |     raise exc.ResourceClosedError("This result object is closed.")
etradie-engine  | sqlalchemy.exc.ResourceClosedError: This result object is closed.
etradie-engine  | 2026-04-15T17:20:09.561523Z [DEBUG    ] snd_candidate_created          [engine.ta.storage.repositories.candidate] extra={'symbol': 'US30X10M', 'pattern': 'SOP', 'direction': 'BULLISH'}
etradie-engine  | 2026-04-15T17:20:09.565433Z [DEBUG    ] snd_candidate_created          [engine.ta.storage.repositories.candidate] extra={'symbol': 'US30X10M', 'pattern': 'SND_CONTINUATION', 'direction': 'BULLISH'}
etradie-engine  | 2026-04-15T17:20:09.571761Z [DEBUG    ] snd_candidate_duplicate_skipped [engine.ta.storage.repositories.candidate] extra={'symbol': 'US30X10M', 'pattern': 'SOP', 'entry_price': 48183.7}
etradie-engine  | 2026-04-15T17:20:09.572206Z [ERROR    ] snd_candidate_persistence_failed [engine.ta.orchestrator] extra={'symbol': 'US30X10M', 'pattern': 'SOP', 'error': 'This result object is closed.'}
etradie-engine  | Traceback (most recent call last):
etradie-engine  |   File "/app/src/engine/ta/orchestrator.py", line 1065, in _persist_all_results
etradie-engine  |     await uow.candidate_repo.create_snd_candidate(
etradie-engine  |   File "/app/src/engine/ta/storage/repositories/candidate.py", line 152, in create_snd_candidate
etradie-engine  |     return existing.scalar_one_or_none()
etradie-engine  |            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 1485, in scalar_one_or_none
etradie-engine  |     return self._only_one_row(
etradie-engine  |            ^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 749, in _only_one_row
etradie-engine  |     row: Optional[_InterimRowType[Any]] = onerow(hard_close=True)
etradie-engine  |                                           ^^^^^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 2255, in _fetchone_impl
etradie-engine  |     self._raise_hard_closed()
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 2241, in _raise_hard_closed
etradie-engine  |     raise exc.ResourceClosedError("This result object is closed.")
etradie-engine  | sqlalchemy.exc.ResourceClosedError: This result object is closed.
etradie-engine  | 2026-04-15T17:20:09.576149Z [DEBUG    ] snd_candidate_duplicate_skipped [engine.ta.storage.repositories.candidate] extra={'symbol': 'US30X10M', 'pattern': 'SOP', 'entry_price': 48284.7}
etradie-engine  | 2026-04-15T17:20:09.576479Z [ERROR    ] snd_candidate_persistence_failed [engine.ta.orchestrator] extra={'symbol': 'US30X10M', 'pattern': 'SOP', 'error': 'This result object is closed.'}
etradie-engine  | Traceback (most recent call last):
etradie-engine  |   File "/app/src/engine/ta/orchestrator.py", line 1065, in _persist_all_results
etradie-engine  |     await uow.candidate_repo.create_snd_candidate(
etradie-engine  |   File "/app/src/engine/ta/storage/repositories/candidate.py", line 152, in create_snd_candidate
etradie-engine  |     return existing.scalar_one_or_none()
etradie-engine  |            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 1485, in scalar_one_or_none
etradie-engine  |     return self._only_one_row(
etradie-engine  |            ^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 749, in _only_one_row
etradie-engine  |     row: Optional[_InterimRowType[Any]] = onerow(hard_close=True)
etradie-engine  |                                           ^^^^^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 2255, in _fetchone_impl
etradie-engine  |     self._raise_hard_closed()
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 2241, in _raise_hard_closed
etradie-engine  |     raise exc.ResourceClosedError("This result object is closed.")
etradie-engine  | sqlalchemy.exc.ResourceClosedError: This result object is closed.
etradie-engine  | 2026-04-15T17:20:09.584966Z [DEBUG    ] snd_candidate_created          [engine.ta.storage.repositories.candidate] extra={'symbol': 'US30X10M', 'pattern': 'FAKEOUT_KING', 'direction': 'BULLISH'}
etradie-engine  | 2026-04-15T17:20:09.589577Z [DEBUG    ] snd_candidate_created          [engine.ta.storage.repositories.candidate] extra={'symbol': 'US30X10M', 'pattern': 'SND_CONTINUATION', 'direction': 'BULLISH'}
etradie-engine  | 2026-04-15T17:20:09.592490Z [DEBUG    ] snd_candidate_duplicate_skipped [engine.ta.storage.repositories.candidate] extra={'symbol': 'US30X10M', 'pattern': 'FAKEOUT_KING', 'entry_price': 48596.7}
etradie-engine  | 2026-04-15T17:20:09.592815Z [ERROR    ] snd_candidate_persistence_failed [engine.ta.orchestrator] extra={'symbol': 'US30X10M', 'pattern': 'FAKEOUT_KING', 'error': 'This result object is closed.'}
etradie-engine  | Traceback (most recent call last):
etradie-engine  |   File "/app/src/engine/ta/orchestrator.py", line 1065, in _persist_all_results
etradie-engine  |     await uow.candidate_repo.create_snd_candidate(
etradie-engine  |   File "/app/src/engine/ta/storage/repositories/candidate.py", line 152, in create_snd_candidate
etradie-engine  |     return existing.scalar_one_or_none()
etradie-engine  |            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 1485, in scalar_one_or_none
etradie-engine  |     return self._only_one_row(
etradie-engine  |            ^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 749, in _only_one_row
etradie-engine  |     row: Optional[_InterimRowType[Any]] = onerow(hard_close=True)
etradie-engine  |                                           ^^^^^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 2255, in _fetchone_impl
etradie-engine  |     self._raise_hard_closed()
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 2241, in _raise_hard_closed
etradie-engine  |     raise exc.ResourceClosedError("This result object is closed.")
etradie-engine  | sqlalchemy.exc.ResourceClosedError: This result object is closed.
etradie-engine  | 2026-04-15T17:20:09.601485Z [DEBUG    ] snd_candidate_created          [engine.ta.storage.repositories.candidate] extra={'symbol': 'US30X10M', 'pattern': 'SND_CONTINUATION', 'direction': 'BULLISH'}
etradie-engine  | 2026-04-15T17:20:09.606618Z [DEBUG    ] snd_candidate_created          [engine.ta.storage.repositories.candidate] extra={'symbol': 'US30X10M', 'pattern': 'QMH_BASELINE', 'direction': 'BULLISH'}
etradie-engine  | 2026-04-15T17:20:09.609517Z [DEBUG    ] snd_candidate_duplicate_skipped [engine.ta.storage.repositories.candidate] extra={'symbol': 'US30X10M', 'pattern': 'QML_BASELINE', 'entry_price': 47626.8}
etradie-engine  | 2026-04-15T17:20:09.610068Z [ERROR    ] snd_candidate_persistence_failed [engine.ta.orchestrator] extra={'symbol': 'US30X10M', 'pattern': 'QML_BASELINE', 'error': 'This result object is closed.'}
etradie-engine  | Traceback (most recent call last):
etradie-engine  |   File "/app/src/engine/ta/orchestrator.py", line 1065, in _persist_all_results
etradie-engine  |     await uow.candidate_repo.create_snd_candidate(
etradie-engine  |   File "/app/src/engine/ta/storage/repositories/candidate.py", line 152, in create_snd_candidate
etradie-engine  |     return existing.scalar_one_or_none()
etradie-engine  |            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 1485, in scalar_one_or_none
etradie-engine  |     return self._only_one_row(
etradie-engine  |            ^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 749, in _only_one_row
etradie-engine  |     row: Optional[_InterimRowType[Any]] = onerow(hard_close=True)
etradie-engine  |                                           ^^^^^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 2255, in _fetchone_impl
etradie-engine  |     self._raise_hard_closed()
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 2241, in _raise_hard_closed
etradie-engine  |     raise exc.ResourceClosedError("This result object is closed.")
etradie-engine  | sqlalchemy.exc.ResourceClosedError: This result object is closed.
etradie-engine  | 2026-04-15T17:20:09.615237Z [DEBUG    ] snd_candidate_duplicate_skipped [engine.ta.storage.repositories.candidate] extra={'symbol': 'US30X10M', 'pattern': 'QML_BASELINE', 'entry_price': 47952.8}
etradie-engine  | 2026-04-15T17:20:09.616097Z [ERROR    ] snd_candidate_persistence_failed [engine.ta.orchestrator] extra={'symbol': 'US30X10M', 'pattern': 'QML_BASELINE', 'error': 'This result object is closed.'}
etradie-engine  | Traceback (most recent call last):
etradie-engine  |   File "/app/src/engine/ta/orchestrator.py", line 1065, in _persist_all_results
etradie-engine  |     await uow.candidate_repo.create_snd_candidate(
etradie-engine  |   File "/app/src/engine/ta/storage/repositories/candidate.py", line 152, in create_snd_candidate
etradie-engine  |     return existing.scalar_one_or_none()
etradie-engine  |            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 1485, in scalar_one_or_none
etradie-engine  |     return self._only_one_row(
etradie-engine  |            ^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 749, in _only_one_row
etradie-engine  |     row: Optional[_InterimRowType[Any]] = onerow(hard_close=True)
etradie-engine  |                                           ^^^^^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 2255, in _fetchone_impl
etradie-engine  |     self._raise_hard_closed()
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 2241, in _raise_hard_closed
etradie-engine  |     raise exc.ResourceClosedError("This result object is closed.")
etradie-engine  | sqlalchemy.exc.ResourceClosedError: This result object is closed.
etradie-engine  | 2026-04-15T17:20:09.619957Z [DEBUG    ] snd_candidate_duplicate_skipped [engine.ta.storage.repositories.candidate] extra={'symbol': 'US30X10M', 'pattern': 'QML_BASELINE', 'entry_price': 47797.6}
etradie-engine  | 2026-04-15T17:20:09.620275Z [ERROR    ] snd_candidate_persistence_failed [engine.ta.orchestrator] extra={'symbol': 'US30X10M', 'pattern': 'QML_BASELINE', 'error': 'This result object is closed.'}
etradie-engine  | Traceback (most recent call last):
etradie-engine  |   File "/app/src/engine/ta/orchestrator.py", line 1065, in _persist_all_results
etradie-engine  |     await uow.candidate_repo.create_snd_candidate(
etradie-engine  |   File "/app/src/engine/ta/storage/repositories/candidate.py", line 152, in create_snd_candidate
etradie-engine  |     return existing.scalar_one_or_none()
etradie-engine  |            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 1485, in scalar_one_or_none
etradie-engine  |     return self._only_one_row(
etradie-engine  |            ^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 749, in _only_one_row
etradie-engine  |     row: Optional[_InterimRowType[Any]] = onerow(hard_close=True)
etradie-engine  |                                           ^^^^^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 2255, in _fetchone_impl
etradie-engine  |     self._raise_hard_closed()
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 2241, in _raise_hard_closed
etradie-engine  |     raise exc.ResourceClosedError("This result object is closed.")
etradie-engine  | sqlalchemy.exc.ResourceClosedError: This result object is closed.
etradie-engine  | 2026-04-15T17:20:09.624162Z [DEBUG    ] snd_candidate_duplicate_skipped [engine.ta.storage.repositories.candidate] extra={'symbol': 'US30X10M', 'pattern': 'QML_BASELINE', 'entry_price': 47906.7}
etradie-engine  | 2026-04-15T17:20:09.624509Z [ERROR    ] snd_candidate_persistence_failed [engine.ta.orchestrator] extra={'symbol': 'US30X10M', 'pattern': 'QML_BASELINE', 'error': 'This result object is closed.'}
etradie-engine  | Traceback (most recent call last):
etradie-engine  |   File "/app/src/engine/ta/orchestrator.py", line 1065, in _persist_all_results
etradie-engine  |     await uow.candidate_repo.create_snd_candidate(
etradie-engine  |   File "/app/src/engine/ta/storage/repositories/candidate.py", line 152, in create_snd_candidate
etradie-engine  |     return existing.scalar_one_or_none()
etradie-engine  |            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 1485, in scalar_one_or_none
etradie-engine  |     return self._only_one_row(
etradie-engine  |            ^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 749, in _only_one_row
etradie-engine  |     row: Optional[_InterimRowType[Any]] = onerow(hard_close=True)
etradie-engine  |                                           ^^^^^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 2255, in _fetchone_impl
etradie-engine  |     self._raise_hard_closed()
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 2241, in _raise_hard_closed
etradie-engine  |     raise exc.ResourceClosedError("This result object is closed.")
etradie-engine  | sqlalchemy.exc.ResourceClosedError: This result object is closed.
etradie-engine  | 2026-04-15T17:20:09.630080Z [DEBUG    ] snd_candidate_duplicate_skipped [engine.ta.storage.repositories.candidate] extra={'symbol': 'US30X10M', 'pattern': 'QML_KILLER_TYPE2', 'entry_price': 47906.7}
etradie-engine  | 2026-04-15T17:20:09.630821Z [ERROR    ] snd_candidate_persistence_failed [engine.ta.orchestrator] extra={'symbol': 'US30X10M', 'pattern': 'QML_KILLER_TYPE2', 'error': 'This result object is closed.'}
etradie-engine  | Traceback (most recent call last):
etradie-engine  |   File "/app/src/engine/ta/orchestrator.py", line 1065, in _persist_all_results
etradie-engine  |     await uow.candidate_repo.create_snd_candidate(
etradie-engine  |   File "/app/src/engine/ta/storage/repositories/candidate.py", line 152, in create_snd_candidate
etradie-engine  |     return existing.scalar_one_or_none()
etradie-engine  |            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 1485, in scalar_one_or_none
etradie-engine  |     return self._only_one_row(
etradie-engine  |            ^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 749, in _only_one_row
etradie-engine  |     row: Optional[_InterimRowType[Any]] = onerow(hard_close=True)
etradie-engine  |                                           ^^^^^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 2255, in _fetchone_impl
etradie-engine  |     self._raise_hard_closed()
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 2241, in _raise_hard_closed
etradie-engine  |     raise exc.ResourceClosedError("This result object is closed.")
etradie-engine  | sqlalchemy.exc.ResourceClosedError: This result object is closed.
etradie-engine  | 2026-04-15T17:20:09.634524Z [DEBUG    ] snd_candidate_duplicate_skipped [engine.ta.storage.repositories.candidate] extra={'symbol': 'US30X10M', 'pattern': 'SOP', 'entry_price': 47666.2}
etradie-engine  | 2026-04-15T17:20:09.634965Z [ERROR    ] snd_candidate_persistence_failed [engine.ta.orchestrator] extra={'symbol': 'US30X10M', 'pattern': 'SOP', 'error': 'This result object is closed.'}
etradie-engine  | Traceback (most recent call last):
etradie-engine  |   File "/app/src/engine/ta/orchestrator.py", line 1065, in _persist_all_results
etradie-engine  |     await uow.candidate_repo.create_snd_candidate(
etradie-engine  |   File "/app/src/engine/ta/storage/repositories/candidate.py", line 152, in create_snd_candidate
etradie-engine  |     return existing.scalar_one_or_none()
etradie-engine  |            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 1485, in scalar_one_or_none
etradie-engine  |     return self._only_one_row(
etradie-engine  |            ^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 749, in _only_one_row
etradie-engine  |     row: Optional[_InterimRowType[Any]] = onerow(hard_close=True)
etradie-engine  |                                           ^^^^^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 2255, in _fetchone_impl
etradie-engine  |     self._raise_hard_closed()
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 2241, in _raise_hard_closed
etradie-engine  |     raise exc.ResourceClosedError("This result object is closed.")
etradie-engine  | sqlalchemy.exc.ResourceClosedError: This result object is closed.
etradie-engine  | 2026-04-15T17:20:09.639063Z [DEBUG    ] snd_candidate_duplicate_skipped [engine.ta.storage.repositories.candidate] extra={'symbol': 'US30X10M', 'pattern': 'SOP', 'entry_price': 47679.4}
etradie-engine  | 2026-04-15T17:20:09.639383Z [ERROR    ] snd_candidate_persistence_failed [engine.ta.orchestrator] extra={'symbol': 'US30X10M', 'pattern': 'SOP', 'error': 'This result object is closed.'}
etradie-engine  | Traceback (most recent call last):
etradie-engine  |   File "/app/src/engine/ta/orchestrator.py", line 1065, in _persist_all_results
etradie-engine  |     await uow.candidate_repo.create_snd_candidate(
etradie-engine  |   File "/app/src/engine/ta/storage/repositories/candidate.py", line 152, in create_snd_candidate
etradie-engine  |     return existing.scalar_one_or_none()
etradie-engine  |            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 1485, in scalar_one_or_none
etradie-engine  |     return self._only_one_row(
etradie-engine  |            ^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 749, in _only_one_row
etradie-engine  |     row: Optional[_InterimRowType[Any]] = onerow(hard_close=True)
etradie-engine  |                                           ^^^^^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 2255, in _fetchone_impl
etradie-engine  |     self._raise_hard_closed()
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 2241, in _raise_hard_closed
etradie-engine  |     raise exc.ResourceClosedError("This result object is closed.")
etradie-engine  | sqlalchemy.exc.ResourceClosedError: This result object is closed.
etradie-engine  | 2026-04-15T17:20:09.644393Z [DEBUG    ] snd_candidate_duplicate_skipped [engine.ta.storage.repositories.candidate] extra={'symbol': 'US30X10M', 'pattern': 'SOP', 'entry_price': 47675.2}
etradie-engine  | 2026-04-15T17:20:09.644950Z [ERROR    ] snd_candidate_persistence_failed [engine.ta.orchestrator] extra={'symbol': 'US30X10M', 'pattern': 'SOP', 'error': 'This result object is closed.'}
etradie-engine  | Traceback (most recent call last):
etradie-engine  |   File "/app/src/engine/ta/orchestrator.py", line 1065, in _persist_all_results
etradie-engine  |     await uow.candidate_repo.create_snd_candidate(
etradie-engine  |   File "/app/src/engine/ta/storage/repositories/candidate.py", line 152, in create_snd_candidate
etradie-engine  |     return existing.scalar_one_or_none()
etradie-engine  |            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 1485, in scalar_one_or_none
etradie-engine  |     return self._only_one_row(
etradie-engine  |            ^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 749, in _only_one_row
etradie-engine  |     row: Optional[_InterimRowType[Any]] = onerow(hard_close=True)
etradie-engine  |                                           ^^^^^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 2255, in _fetchone_impl
etradie-engine  |     self._raise_hard_closed()
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 2241, in _raise_hard_closed
etradie-engine  |     raise exc.ResourceClosedError("This result object is closed.")
etradie-engine  | sqlalchemy.exc.ResourceClosedError: This result object is closed.
etradie-engine  | 2026-04-15T17:20:09.648932Z [DEBUG    ] snd_candidate_duplicate_skipped [engine.ta.storage.repositories.candidate] extra={'symbol': 'US30X10M', 'pattern': 'SOP', 'entry_price': 47687.0}
etradie-engine  | 2026-04-15T17:20:09.649266Z [ERROR    ] snd_candidate_persistence_failed [engine.ta.orchestrator] extra={'symbol': 'US30X10M', 'pattern': 'SOP', 'error': 'This result object is closed.'}
etradie-engine  | Traceback (most recent call last):
etradie-engine  |   File "/app/src/engine/ta/orchestrator.py", line 1065, in _persist_all_results
etradie-engine  |     await uow.candidate_repo.create_snd_candidate(
etradie-engine  |   File "/app/src/engine/ta/storage/repositories/candidate.py", line 152, in create_snd_candidate
etradie-engine  |     return existing.scalar_one_or_none()
etradie-engine  |            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 1485, in scalar_one_or_none
etradie-engine  |     return self._only_one_row(
etradie-engine  |            ^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 749, in _only_one_row
etradie-engine  |     row: Optional[_InterimRowType[Any]] = onerow(hard_close=True)
etradie-engine  |                                           ^^^^^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 2255, in _fetchone_impl
etradie-engine  |     self._raise_hard_closed()
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 2241, in _raise_hard_closed
etradie-engine  |     raise exc.ResourceClosedError("This result object is closed.")
etradie-engine  | sqlalchemy.exc.ResourceClosedError: This result object is closed.
etradie-engine  | 2026-04-15T17:20:09.654256Z [DEBUG    ] snd_candidate_created          [engine.ta.storage.repositories.candidate] extra={'symbol': 'US30X10M', 'pattern': 'SOP', 'direction': 'BEARISH'}
etradie-engine  | 2026-04-15T17:20:09.656691Z [DEBUG    ] snd_candidate_duplicate_skipped [engine.ta.storage.repositories.candidate] extra={'symbol': 'US30X10M', 'pattern': 'SOP', 'entry_price': 48529.2}
etradie-engine  | 2026-04-15T17:20:09.657008Z [ERROR    ] snd_candidate_persistence_failed [engine.ta.orchestrator] extra={'symbol': 'US30X10M', 'pattern': 'SOP', 'error': 'This result object is closed.'}
etradie-engine  | Traceback (most recent call last):
etradie-engine  |   File "/app/src/engine/ta/orchestrator.py", line 1065, in _persist_all_results
etradie-engine  |     await uow.candidate_repo.create_snd_candidate(
etradie-engine  |   File "/app/src/engine/ta/storage/repositories/candidate.py", line 152, in create_snd_candidate
etradie-engine  |     return existing.scalar_one_or_none()
etradie-engine  |            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 1485, in scalar_one_or_none
etradie-engine  |     return self._only_one_row(
etradie-engine  |            ^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 749, in _only_one_row
etradie-engine  |     row: Optional[_InterimRowType[Any]] = onerow(hard_close=True)
etradie-engine  |                                           ^^^^^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 2255, in _fetchone_impl
etradie-engine  |     self._raise_hard_closed()
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 2241, in _raise_hard_closed
etradie-engine  |     raise exc.ResourceClosedError("This result object is closed.")
etradie-engine  | sqlalchemy.exc.ResourceClosedError: This result object is closed.
etradie-engine  | 2026-04-15T17:20:09.666206Z [DEBUG    ] snd_candidate_created          [engine.ta.storage.repositories.candidate] extra={'symbol': 'US30X10M', 'pattern': 'SOP', 'direction': 'BEARISH'}
etradie-engine  | 2026-04-15T17:20:09.671099Z [DEBUG    ] snd_candidate_created          [engine.ta.storage.repositories.candidate] extra={'symbol': 'US30X10M', 'pattern': 'SND_CONTINUATION', 'direction': 'BEARISH'}
etradie-engine  | 2026-04-15T17:20:09.677654Z [DEBUG    ] snd_candidate_created          [engine.ta.storage.repositories.candidate] extra={'symbol': 'US30X10M', 'pattern': 'SOP', 'direction': 'BEARISH'}
etradie-engine  | 2026-04-15T17:20:09.680602Z [DEBUG    ] snd_candidate_duplicate_skipped [engine.ta.storage.repositories.candidate] extra={'symbol': 'US30X10M', 'pattern': 'FAKEOUT_KING', 'entry_price': 48580.1}
etradie-engine  | 2026-04-15T17:20:09.681017Z [ERROR    ] snd_candidate_persistence_failed [engine.ta.orchestrator] extra={'symbol': 'US30X10M', 'pattern': 'FAKEOUT_KING', 'error': 'This result object is closed.'}
etradie-engine  | Traceback (most recent call last):
etradie-engine  |   File "/app/src/engine/ta/orchestrator.py", line 1065, in _persist_all_results
etradie-engine  |     await uow.candidate_repo.create_snd_candidate(
etradie-engine  |   File "/app/src/engine/ta/storage/repositories/candidate.py", line 152, in create_snd_candidate
etradie-engine  |     return existing.scalar_one_or_none()
etradie-engine  |            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 1485, in scalar_one_or_none
etradie-engine  |     return self._only_one_row(
etradie-engine  |            ^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 749, in _only_one_row
etradie-engine  |     row: Optional[_InterimRowType[Any]] = onerow(hard_close=True)
etradie-engine  |                                           ^^^^^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 2255, in _fetchone_impl
etradie-engine  |     self._raise_hard_closed()
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 2241, in _raise_hard_closed
etradie-engine  |     raise exc.ResourceClosedError("This result object is closed.")
etradie-engine  | sqlalchemy.exc.ResourceClosedError: This result object is closed.
etradie-engine  | 2026-04-15T17:20:09.685977Z [DEBUG    ] snd_candidate_created          [engine.ta.storage.repositories.candidate] extra={'symbol': 'US30X10M', 'pattern': 'SND_CONTINUATION', 'direction': 'BEARISH'}
etradie-engine  | 2026-04-15T17:20:09.689782Z [DEBUG    ] snd_candidate_duplicate_skipped [engine.ta.storage.repositories.candidate] extra={'symbol': 'US30X10M', 'pattern': 'FAKEOUT_KING', 'entry_price': 48581.2}
etradie-engine  | 2026-04-15T17:20:09.695447Z [ERROR    ] snd_candidate_persistence_failed [engine.ta.orchestrator] extra={'symbol': 'US30X10M', 'pattern': 'FAKEOUT_KING', 'error': 'This result object is closed.'}
etradie-engine  | Traceback (most recent call last):
etradie-engine  |   File "/app/src/engine/ta/orchestrator.py", line 1065, in _persist_all_results
etradie-engine  |     await uow.candidate_repo.create_snd_candidate(
etradie-engine  |   File "/app/src/engine/ta/storage/repositories/candidate.py", line 152, in create_snd_candidate
etradie-engine  |     return existing.scalar_one_or_none()
etradie-engine  |            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 1485, in scalar_one_or_none
etradie-engine  |     return self._only_one_row(
etradie-engine  |            ^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 749, in _only_one_row
etradie-engine  |     row: Optional[_InterimRowType[Any]] = onerow(hard_close=True)
etradie-engine  |                                           ^^^^^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 2255, in _fetchone_impl
etradie-engine  |     self._raise_hard_closed()
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 2241, in _raise_hard_closed
etradie-engine  |     raise exc.ResourceClosedError("This result object is closed.")
etradie-engine  | sqlalchemy.exc.ResourceClosedError: This result object is closed.
etradie-engine  | 2026-04-15T17:20:09.709535Z [DEBUG    ] snd_candidate_created          [engine.ta.storage.repositories.candidate] extra={'symbol': 'US30X10M', 'pattern': 'SND_CONTINUATION', 'direction': 'BEARISH'}
etradie-engine  | 2026-04-15T17:20:09.713613Z [DEBUG    ] snd_candidate_duplicate_skipped [engine.ta.storage.repositories.candidate] extra={'symbol': 'US30X10M', 'pattern': 'SOP', 'entry_price': 48582.4}
etradie-engine  | 2026-04-15T17:20:09.714057Z [ERROR    ] snd_candidate_persistence_failed [engine.ta.orchestrator] extra={'symbol': 'US30X10M', 'pattern': 'SOP', 'error': 'This result object is closed.'}
etradie-engine  | Traceback (most recent call last):
etradie-engine  |   File "/app/src/engine/ta/orchestrator.py", line 1065, in _persist_all_results
etradie-engine  |     await uow.candidate_repo.create_snd_candidate(
etradie-engine  |   File "/app/src/engine/ta/storage/repositories/candidate.py", line 152, in create_snd_candidate
etradie-engine  |     return existing.scalar_one_or_none()
etradie-engine  |            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 1485, in scalar_one_or_none
etradie-engine  |     return self._only_one_row(
etradie-engine  |            ^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 749, in _only_one_row
etradie-engine  |     row: Optional[_InterimRowType[Any]] = onerow(hard_close=True)
etradie-engine  |                                           ^^^^^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 2255, in _fetchone_impl
etradie-engine  |     self._raise_hard_closed()
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 2241, in _raise_hard_closed
etradie-engine  |     raise exc.ResourceClosedError("This result object is closed.")
etradie-engine  | sqlalchemy.exc.ResourceClosedError: This result object is closed.
etradie-engine  | 2026-04-15T17:20:09.719679Z [DEBUG    ] snd_candidate_duplicate_skipped [engine.ta.storage.repositories.candidate] extra={'symbol': 'US30X10M', 'pattern': 'SOP', 'entry_price': 48590.2}
etradie-engine  | 2026-04-15T17:20:09.720295Z [ERROR    ] snd_candidate_persistence_failed [engine.ta.orchestrator] extra={'symbol': 'US30X10M', 'pattern': 'SOP', 'error': 'This result object is closed.'}
etradie-engine  | Traceback (most recent call last):
etradie-engine  |   File "/app/src/engine/ta/orchestrator.py", line 1065, in _persist_all_results
etradie-engine  |     await uow.candidate_repo.create_snd_candidate(
etradie-engine  |   File "/app/src/engine/ta/storage/repositories/candidate.py", line 152, in create_snd_candidate
etradie-engine  |     return existing.scalar_one_or_none()
etradie-engine  |            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 1485, in scalar_one_or_none
etradie-engine  |     return self._only_one_row(
etradie-engine  |            ^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 749, in _only_one_row
etradie-engine  |     row: Optional[_InterimRowType[Any]] = onerow(hard_close=True)
etradie-engine  |                                           ^^^^^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 2255, in _fetchone_impl
etradie-engine  |     self._raise_hard_closed()
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 2241, in _raise_hard_closed
etradie-engine  |     raise exc.ResourceClosedError("This result object is closed.")
etradie-engine  | sqlalchemy.exc.ResourceClosedError: This result object is closed.
etradie-engine  | 2026-04-15T17:20:09.737052Z [DEBUG    ] snd_candidate_created          [engine.ta.storage.repositories.candidate] extra={'symbol': 'US30X10M', 'pattern': 'SOP', 'direction': 'BEARISH'}
etradie-engine  | 2026-04-15T17:20:09.742718Z [DEBUG    ] snd_candidate_created          [engine.ta.storage.repositories.candidate] extra={'symbol': 'US30X10M', 'pattern': 'SOP', 'direction': 'BEARISH'}
etradie-engine  | 2026-04-15T17:20:09.751675Z [DEBUG    ] snd_candidate_created          [engine.ta.storage.repositories.candidate] extra={'symbol': 'US30X10M', 'pattern': 'SOP', 'direction': 'BEARISH'}
etradie-engine  | 2026-04-15T17:20:09.757799Z [DEBUG    ] snd_candidate_created          [engine.ta.storage.repositories.candidate] extra={'symbol': 'US30X10M', 'pattern': 'SOP', 'direction': 'BEARISH'}
etradie-engine  | 2026-04-15T17:20:09.763859Z [DEBUG    ] snd_candidate_created          [engine.ta.storage.repositories.candidate] extra={'symbol': 'US30X10M', 'pattern': 'SOP', 'direction': 'BEARISH'}
etradie-engine  | 2026-04-15T17:20:09.769502Z [DEBUG    ] snd_candidate_duplicate_skipped [engine.ta.storage.repositories.candidate] extra={'symbol': 'US30X10M', 'pattern': 'QML_BASELINE', 'entry_price': 48183.7}
etradie-engine  | 2026-04-15T17:20:09.769941Z [ERROR    ] snd_candidate_persistence_failed [engine.ta.orchestrator] extra={'symbol': 'US30X10M', 'pattern': 'QML_BASELINE', 'error': 'This result object is closed.'}
etradie-engine  | Traceback (most recent call last):
etradie-engine  |   File "/app/src/engine/ta/orchestrator.py", line 1065, in _persist_all_results
etradie-engine  |     await uow.candidate_repo.create_snd_candidate(
etradie-engine  |   File "/app/src/engine/ta/storage/repositories/candidate.py", line 152, in create_snd_candidate
etradie-engine  |     return existing.scalar_one_or_none()
etradie-engine  |            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 1485, in scalar_one_or_none
etradie-engine  |     return self._only_one_row(
etradie-engine  |            ^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 749, in _only_one_row
etradie-engine  |     row: Optional[_InterimRowType[Any]] = onerow(hard_close=True)
etradie-engine  |                                           ^^^^^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 2255, in _fetchone_impl
etradie-engine  |     self._raise_hard_closed()
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 2241, in _raise_hard_closed
etradie-engine  |     raise exc.ResourceClosedError("This result object is closed.")
etradie-engine  | sqlalchemy.exc.ResourceClosedError: This result object is closed.
etradie-engine  | 2026-04-15T17:20:09.775559Z [DEBUG    ] snd_candidate_duplicate_skipped [engine.ta.storage.repositories.candidate] extra={'symbol': 'US30X10M', 'pattern': 'QML_BASELINE', 'entry_price': 48198.9}
etradie-engine  | 2026-04-15T17:20:09.775995Z [ERROR    ] snd_candidate_persistence_failed [engine.ta.orchestrator] extra={'symbol': 'US30X10M', 'pattern': 'QML_BASELINE', 'error': 'This result object is closed.'}
etradie-engine  | Traceback (most recent call last):
etradie-engine  |   File "/app/src/engine/ta/orchestrator.py", line 1065, in _persist_all_results
etradie-engine  |     await uow.candidate_repo.create_snd_candidate(
etradie-engine  |   File "/app/src/engine/ta/storage/repositories/candidate.py", line 152, in create_snd_candidate
etradie-engine  |     return existing.scalar_one_or_none()
etradie-engine  |            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 1485, in scalar_one_or_none
etradie-engine  |     return self._only_one_row(
etradie-engine  |            ^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 749, in _only_one_row
etradie-engine  |     row: Optional[_InterimRowType[Any]] = onerow(hard_close=True)
etradie-engine  |                                           ^^^^^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 2255, in _fetchone_impl
etradie-engine  |     self._raise_hard_closed()
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 2241, in _raise_hard_closed
etradie-engine  |     raise exc.ResourceClosedError("This result object is closed.")
etradie-engine  | sqlalchemy.exc.ResourceClosedError: This result object is closed.
etradie-engine  | 2026-04-15T17:20:09.782213Z [DEBUG    ] snd_candidate_duplicate_skipped [engine.ta.storage.repositories.candidate] extra={'symbol': 'US30X10M', 'pattern': 'QML_BASELINE', 'entry_price': 47757.3}
etradie-engine  | 2026-04-15T17:20:09.784808Z [ERROR    ] snd_candidate_persistence_failed [engine.ta.orchestrator] extra={'symbol': 'US30X10M', 'pattern': 'QML_BASELINE', 'error': 'This result object is closed.'}
etradie-engine  | Traceback (most recent call last):
etradie-engine  |   File "/app/src/engine/ta/orchestrator.py", line 1065, in _persist_all_results
etradie-engine  |     await uow.candidate_repo.create_snd_candidate(
etradie-engine  |   File "/app/src/engine/ta/storage/repositories/candidate.py", line 152, in create_snd_candidate
etradie-engine  |     return existing.scalar_one_or_none()
etradie-engine  |            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 1485, in scalar_one_or_none
etradie-engine  |     return self._only_one_row(
etradie-engine  |            ^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 749, in _only_one_row
etradie-engine  |     row: Optional[_InterimRowType[Any]] = onerow(hard_close=True)
etradie-engine  |                                           ^^^^^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 2255, in _fetchone_impl
etradie-engine  |     self._raise_hard_closed()
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 2241, in _raise_hard_closed
etradie-engine  |     raise exc.ResourceClosedError("This result object is closed.")
etradie-engine  | sqlalchemy.exc.ResourceClosedError: This result object is closed.
etradie-engine  | 2026-04-15T17:20:09.792267Z [DEBUG    ] snd_candidate_duplicate_skipped [engine.ta.storage.repositories.candidate] extra={'symbol': 'US30X10M', 'pattern': 'QML_BASELINE', 'entry_price': 48263.6}
etradie-engine  | 2026-04-15T17:20:09.792880Z [ERROR    ] snd_candidate_persistence_failed [engine.ta.orchestrator] extra={'symbol': 'US30X10M', 'pattern': 'QML_BASELINE', 'error': 'This result object is closed.'}
etradie-engine  | Traceback (most recent call last):
etradie-engine  |   File "/app/src/engine/ta/orchestrator.py", line 1065, in _persist_all_results
etradie-engine  |     await uow.candidate_repo.create_snd_candidate(
etradie-engine  |   File "/app/src/engine/ta/storage/repositories/candidate.py", line 152, in create_snd_candidate
etradie-engine  |     return existing.scalar_one_or_none()
etradie-engine  |            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 1485, in scalar_one_or_none
etradie-engine  |     return self._only_one_row(
etradie-engine  |            ^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 749, in _only_one_row
etradie-engine  |     row: Optional[_InterimRowType[Any]] = onerow(hard_close=True)
etradie-engine  |                                           ^^^^^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 2255, in _fetchone_impl
etradie-engine  |     self._raise_hard_closed()
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 2241, in _raise_hard_closed
etradie-engine  |     raise exc.ResourceClosedError("This result object is closed.")
etradie-engine  | sqlalchemy.exc.ResourceClosedError: This result object is closed.
etradie-engine  | 2026-04-15T17:20:09.803450Z [DEBUG    ] snd_candidate_created          [engine.ta.storage.repositories.candidate] extra={'symbol': 'US30X10M', 'pattern': 'QML_BASELINE', 'direction': 'BEARISH'}
etradie-engine  | 2026-04-15T17:20:09.807517Z [DEBUG    ] snd_candidate_duplicate_skipped [engine.ta.storage.repositories.candidate] extra={'symbol': 'US30X10M', 'pattern': 'QMH_BASELINE', 'entry_price': 47748.2}
etradie-engine  | 2026-04-15T17:20:09.807867Z [ERROR    ] snd_candidate_persistence_failed [engine.ta.orchestrator] extra={'symbol': 'US30X10M', 'pattern': 'QMH_BASELINE', 'error': 'This result object is closed.'}
etradie-engine  | Traceback (most recent call last):
etradie-engine  |   File "/app/src/engine/ta/orchestrator.py", line 1065, in _persist_all_results
etradie-engine  |     await uow.candidate_repo.create_snd_candidate(
etradie-engine  |   File "/app/src/engine/ta/storage/repositories/candidate.py", line 152, in create_snd_candidate
etradie-engine  |     return existing.scalar_one_or_none()
etradie-engine  |            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 1485, in scalar_one_or_none
etradie-engine  |     return self._only_one_row(
etradie-engine  |            ^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 749, in _only_one_row
etradie-engine  |     row: Optional[_InterimRowType[Any]] = onerow(hard_close=True)
etradie-engine  |                                           ^^^^^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 2255, in _fetchone_impl
etradie-engine  |     self._raise_hard_closed()
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 2241, in _raise_hard_closed
etradie-engine  |     raise exc.ResourceClosedError("This result object is closed.")
etradie-engine  | sqlalchemy.exc.ResourceClosedError: This result object is closed.
etradie-engine  | 2026-04-15T17:20:09.812807Z [DEBUG    ] snd_candidate_duplicate_skipped [engine.ta.storage.repositories.candidate] extra={'symbol': 'US30X10M', 'pattern': 'QMH_BASELINE', 'entry_price': 47844.3}
etradie-engine  | 2026-04-15T17:20:09.813358Z [ERROR    ] snd_candidate_persistence_failed [engine.ta.orchestrator] extra={'symbol': 'US30X10M', 'pattern': 'QMH_BASELINE', 'error': 'This result object is closed.'}
etradie-engine  | Traceback (most recent call last):
etradie-engine  |   File "/app/src/engine/ta/orchestrator.py", line 1065, in _persist_all_results
etradie-engine  |     await uow.candidate_repo.create_snd_candidate(
etradie-engine  |   File "/app/src/engine/ta/storage/repositories/candidate.py", line 152, in create_snd_candidate
etradie-engine  |     return existing.scalar_one_or_none()
etradie-engine  |            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 1485, in scalar_one_or_none
etradie-engine  |     return self._only_one_row(
etradie-engine  |            ^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 749, in _only_one_row
etradie-engine  |     row: Optional[_InterimRowType[Any]] = onerow(hard_close=True)
etradie-engine  |                                           ^^^^^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 2255, in _fetchone_impl
etradie-engine  |     self._raise_hard_closed()
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 2241, in _raise_hard_closed
etradie-engine  |     raise exc.ResourceClosedError("This result object is closed.")
etradie-engine  | sqlalchemy.exc.ResourceClosedError: This result object is closed.
etradie-engine  | 2026-04-15T17:20:09.818707Z [DEBUG    ] snd_candidate_duplicate_skipped [engine.ta.storage.repositories.candidate] extra={'symbol': 'US30X10M', 'pattern': 'QMH_BASELINE', 'entry_price': 47733.6}
etradie-engine  | 2026-04-15T17:20:09.821549Z [ERROR    ] snd_candidate_persistence_failed [engine.ta.orchestrator] extra={'symbol': 'US30X10M', 'pattern': 'QMH_BASELINE', 'error': 'This result object is closed.'}
etradie-engine  | Traceback (most recent call last):
etradie-engine  |   File "/app/src/engine/ta/orchestrator.py", line 1065, in _persist_all_results
etradie-engine  |     await uow.candidate_repo.create_snd_candidate(
etradie-engine  |   File "/app/src/engine/ta/storage/repositories/candidate.py", line 152, in create_snd_candidate
etradie-engine  |     return existing.scalar_one_or_none()
etradie-engine  |            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 1485, in scalar_one_or_none
etradie-engine  |     return self._only_one_row(
etradie-engine  |            ^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 749, in _only_one_row
etradie-engine  |     row: Optional[_InterimRowType[Any]] = onerow(hard_close=True)
etradie-engine  |                                           ^^^^^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 2255, in _fetchone_impl
etradie-engine  |     self._raise_hard_closed()
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 2241, in _raise_hard_closed
etradie-engine  |     raise exc.ResourceClosedError("This result object is closed.")
etradie-engine  | sqlalchemy.exc.ResourceClosedError: This result object is closed.
etradie-engine  | 2026-04-15T17:20:09.827788Z [DEBUG    ] snd_candidate_duplicate_skipped [engine.ta.storage.repositories.candidate] extra={'symbol': 'US30X10M', 'pattern': 'QMH_BASELINE', 'entry_price': 48196.4}
etradie-engine  | 2026-04-15T17:20:09.828402Z [ERROR    ] snd_candidate_persistence_failed [engine.ta.orchestrator] extra={'symbol': 'US30X10M', 'pattern': 'QMH_BASELINE', 'error': 'This result object is closed.'}
etradie-engine  | Traceback (most recent call last):
etradie-engine  |   File "/app/src/engine/ta/orchestrator.py", line 1065, in _persist_all_results
etradie-engine  |     await uow.candidate_repo.create_snd_candidate(
etradie-engine  |   File "/app/src/engine/ta/storage/repositories/candidate.py", line 152, in create_snd_candidate
etradie-engine  |     return existing.scalar_one_or_none()
etradie-engine  |            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 1485, in scalar_one_or_none
etradie-engine  |     return self._only_one_row(
etradie-engine  |            ^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 749, in _only_one_row
etradie-engine  |     row: Optional[_InterimRowType[Any]] = onerow(hard_close=True)
etradie-engine  |                                           ^^^^^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 2255, in _fetchone_impl
etradie-engine  |     self._raise_hard_closed()
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 2241, in _raise_hard_closed
etradie-engine  |     raise exc.ResourceClosedError("This result object is closed.")
etradie-engine  | sqlalchemy.exc.ResourceClosedError: This result object is closed.
etradie-engine  | 2026-04-15T17:20:09.834964Z [DEBUG    ] snd_candidate_duplicate_skipped [engine.ta.storage.repositories.candidate] extra={'symbol': 'US30X10M', 'pattern': 'QMH_BASELINE', 'entry_price': 48158.2}
etradie-engine  | 2026-04-15T17:20:09.836369Z [ERROR    ] snd_candidate_persistence_failed [engine.ta.orchestrator] extra={'symbol': 'US30X10M', 'pattern': 'QMH_BASELINE', 'error': 'This result object is closed.'}
etradie-engine  | Traceback (most recent call last):
etradie-engine  |   File "/app/src/engine/ta/orchestrator.py", line 1065, in _persist_all_results
etradie-engine  |     await uow.candidate_repo.create_snd_candidate(
etradie-engine  |   File "/app/src/engine/ta/storage/repositories/candidate.py", line 152, in create_snd_candidate
etradie-engine  |     return existing.scalar_one_or_none()
etradie-engine  |            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 1485, in scalar_one_or_none
etradie-engine  |     return self._only_one_row(
etradie-engine  |            ^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 749, in _only_one_row
etradie-engine  |     row: Optional[_InterimRowType[Any]] = onerow(hard_close=True)
etradie-engine  |                                           ^^^^^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 2255, in _fetchone_impl
etradie-engine  |     self._raise_hard_closed()
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 2241, in _raise_hard_closed
etradie-engine  |     raise exc.ResourceClosedError("This result object is closed.")
etradie-engine  | sqlalchemy.exc.ResourceClosedError: This result object is closed.
etradie-engine  | 2026-04-15T17:20:09.843036Z [DEBUG    ] snd_candidate_duplicate_skipped [engine.ta.storage.repositories.candidate] extra={'symbol': 'US30X10M', 'pattern': 'QMH_KILLER_TYPE2', 'entry_price': 48158.2}
etradie-engine  | 2026-04-15T17:20:09.843619Z [ERROR    ] snd_candidate_persistence_failed [engine.ta.orchestrator] extra={'symbol': 'US30X10M', 'pattern': 'QMH_KILLER_TYPE2', 'error': 'This result object is closed.'}
etradie-engine  | Traceback (most recent call last):
etradie-engine  |   File "/app/src/engine/ta/orchestrator.py", line 1065, in _persist_all_results
etradie-engine  |     await uow.candidate_repo.create_snd_candidate(
etradie-engine  |   File "/app/src/engine/ta/storage/repositories/candidate.py", line 152, in create_snd_candidate
etradie-engine  |     return existing.scalar_one_or_none()
etradie-engine  |            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 1485, in scalar_one_or_none
etradie-engine  |     return self._only_one_row(
etradie-engine  |            ^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 749, in _only_one_row
etradie-engine  |     row: Optional[_InterimRowType[Any]] = onerow(hard_close=True)
etradie-engine  |                                           ^^^^^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 2255, in _fetchone_impl
etradie-engine  |     self._raise_hard_closed()
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 2241, in _raise_hard_closed
etradie-engine  |     raise exc.ResourceClosedError("This result object is closed.")
etradie-engine  | sqlalchemy.exc.ResourceClosedError: This result object is closed.
etradie-engine  | 2026-04-15T17:20:09.848527Z [DEBUG    ] snd_candidate_duplicate_skipped [engine.ta.storage.repositories.candidate] extra={'symbol': 'US30X10M', 'pattern': 'SOP', 'entry_price': 47707.7}
etradie-engine  | 2026-04-15T17:20:09.848922Z [ERROR    ] snd_candidate_persistence_failed [engine.ta.orchestrator] extra={'symbol': 'US30X10M', 'pattern': 'SOP', 'error': 'This result object is closed.'}
etradie-engine  | Traceback (most recent call last):
etradie-engine  |   File "/app/src/engine/ta/orchestrator.py", line 1065, in _persist_all_results
etradie-engine  |     await uow.candidate_repo.create_snd_candidate(
etradie-engine  |   File "/app/src/engine/ta/storage/repositories/candidate.py", line 152, in create_snd_candidate
etradie-engine  |     return existing.scalar_one_or_none()
etradie-engine  |            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 1485, in scalar_one_or_none
etradie-engine  |     return self._only_one_row(
etradie-engine  |            ^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 749, in _only_one_row
etradie-engine  |     row: Optional[_InterimRowType[Any]] = onerow(hard_close=True)
etradie-engine  |                                           ^^^^^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 2255, in _fetchone_impl
etradie-engine  |     self._raise_hard_closed()
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 2241, in _raise_hard_closed
etradie-engine  |     raise exc.ResourceClosedError("This result object is closed.")
etradie-engine  | sqlalchemy.exc.ResourceClosedError: This result object is closed.
etradie-engine  | 2026-04-15T17:20:09.854068Z [DEBUG    ] snd_candidate_duplicate_skipped [engine.ta.storage.repositories.candidate] extra={'symbol': 'US30X10M', 'pattern': 'SOP', 'entry_price': 48282.7}
etradie-engine  | 2026-04-15T17:20:09.855391Z [ERROR    ] snd_candidate_persistence_failed [engine.ta.orchestrator] extra={'symbol': 'US30X10M', 'pattern': 'SOP', 'error': 'This result object is closed.'}
etradie-engine  | Traceback (most recent call last):
etradie-engine  |   File "/app/src/engine/ta/orchestrator.py", line 1065, in _persist_all_results
etradie-engine  |     await uow.candidate_repo.create_snd_candidate(
etradie-engine  |   File "/app/src/engine/ta/storage/repositories/candidate.py", line 152, in create_snd_candidate
etradie-engine  |     return existing.scalar_one_or_none()
etradie-engine  |            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 1485, in scalar_one_or_none
etradie-engine  |     return self._only_one_row(
etradie-engine  |            ^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 749, in _only_one_row
etradie-engine  |     row: Optional[_InterimRowType[Any]] = onerow(hard_close=True)
etradie-engine  |                                           ^^^^^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 2255, in _fetchone_impl
etradie-engine  |     self._raise_hard_closed()
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 2241, in _raise_hard_closed
etradie-engine  |     raise exc.ResourceClosedError("This result object is closed.")
etradie-engine  | sqlalchemy.exc.ResourceClosedError: This result object is closed.
etradie-engine  | 2026-04-15T17:20:09.866502Z [DEBUG    ] snd_candidate_created          [engine.ta.storage.repositories.candidate] extra={'symbol': 'US30X10M', 'pattern': 'SND_CONTINUATION', 'direction': 'BULLISH'}
etradie-engine  | 2026-04-15T17:20:09.869341Z [DEBUG    ] snd_candidate_duplicate_skipped [engine.ta.storage.repositories.candidate] extra={'symbol': 'US30X10M', 'pattern': 'SOP', 'entry_price': 48287.4}
etradie-engine  | 2026-04-15T17:20:09.869651Z [ERROR    ] snd_candidate_persistence_failed [engine.ta.orchestrator] extra={'symbol': 'US30X10M', 'pattern': 'SOP', 'error': 'This result object is closed.'}
etradie-engine  | Traceback (most recent call last):
etradie-engine  |   File "/app/src/engine/ta/orchestrator.py", line 1065, in _persist_all_results
etradie-engine  |     await uow.candidate_repo.create_snd_candidate(
etradie-engine  |   File "/app/src/engine/ta/storage/repositories/candidate.py", line 152, in create_snd_candidate
etradie-engine  |     return existing.scalar_one_or_none()
etradie-engine  |            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 1485, in scalar_one_or_none
etradie-engine  |     return self._only_one_row(
etradie-engine  |            ^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 749, in _only_one_row
etradie-engine  |     row: Optional[_InterimRowType[Any]] = onerow(hard_close=True)
etradie-engine  |                                           ^^^^^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 2255, in _fetchone_impl
etradie-engine  |     self._raise_hard_closed()
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 2241, in _raise_hard_closed
etradie-engine  |     raise exc.ResourceClosedError("This result object is closed.")
etradie-engine  | sqlalchemy.exc.ResourceClosedError: This result object is closed.
etradie-engine  | 2026-04-15T17:20:09.875675Z [DEBUG    ] snd_candidate_duplicate_skipped [engine.ta.storage.repositories.candidate] extra={'symbol': 'US30X10M', 'pattern': 'FAKEOUT_KING', 'entry_price': 48279.7}
etradie-engine  | 2026-04-15T17:20:09.876069Z [ERROR    ] snd_candidate_persistence_failed [engine.ta.orchestrator] extra={'symbol': 'US30X10M', 'pattern': 'FAKEOUT_KING', 'error': 'This result object is closed.'}
etradie-engine  | Traceback (most recent call last):
etradie-engine  |   File "/app/src/engine/ta/orchestrator.py", line 1065, in _persist_all_results
etradie-engine  |     await uow.candidate_repo.create_snd_candidate(
etradie-engine  |   File "/app/src/engine/ta/storage/repositories/candidate.py", line 152, in create_snd_candidate
etradie-engine  |     return existing.scalar_one_or_none()
etradie-engine  |            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 1485, in scalar_one_or_none
etradie-engine  |     return self._only_one_row(
etradie-engine  |            ^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 749, in _only_one_row
etradie-engine  |     row: Optional[_InterimRowType[Any]] = onerow(hard_close=True)
etradie-engine  |                                           ^^^^^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 2255, in _fetchone_impl
etradie-engine  |     self._raise_hard_closed()
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 2241, in _raise_hard_closed
etradie-engine  |     raise exc.ResourceClosedError("This result object is closed.")
etradie-engine  | sqlalchemy.exc.ResourceClosedError: This result object is closed.
etradie-engine  | 2026-04-15T17:20:09.884649Z [DEBUG    ] snd_candidate_created          [engine.ta.storage.repositories.candidate] extra={'symbol': 'US30X10M', 'pattern': 'SND_CONTINUATION', 'direction': 'BULLISH'}
etradie-engine  | 2026-04-15T17:20:09.888024Z [DEBUG    ] snd_candidate_duplicate_skipped [engine.ta.storage.repositories.candidate] extra={'symbol': 'US30X10M', 'pattern': 'SOP', 'entry_price': 48263.6}
etradie-engine  | 2026-04-15T17:20:09.888684Z [ERROR    ] snd_candidate_persistence_failed [engine.ta.orchestrator] extra={'symbol': 'US30X10M', 'pattern': 'SOP', 'error': 'This result object is closed.'}
etradie-engine  | Traceback (most recent call last):
etradie-engine  |   File "/app/src/engine/ta/orchestrator.py", line 1065, in _persist_all_results
etradie-engine  |     await uow.candidate_repo.create_snd_candidate(
etradie-engine  |   File "/app/src/engine/ta/storage/repositories/candidate.py", line 152, in create_snd_candidate
etradie-engine  |     return existing.scalar_one_or_none()
etradie-engine  |            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 1485, in scalar_one_or_none
etradie-engine  |     return self._only_one_row(
etradie-engine  |            ^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 749, in _only_one_row
etradie-engine  |     row: Optional[_InterimRowType[Any]] = onerow(hard_close=True)
etradie-engine  |                                           ^^^^^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 2255, in _fetchone_impl
etradie-engine  |     self._raise_hard_closed()
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 2241, in _raise_hard_closed
etradie-engine  |     raise exc.ResourceClosedError("This result object is closed.")
etradie-engine  | sqlalchemy.exc.ResourceClosedError: This result object is closed.
etradie-engine  | 2026-04-15T17:20:09.895740Z [DEBUG    ] snd_candidate_created          [engine.ta.storage.repositories.candidate] extra={'symbol': 'US30X10M', 'pattern': 'SOP', 'direction': 'BULLISH'}
etradie-engine  | 2026-04-15T17:20:09.900326Z [DEBUG    ] snd_candidate_created          [engine.ta.storage.repositories.candidate] extra={'symbol': 'US30X10M', 'pattern': 'FAKEOUT_KING', 'direction': 'BULLISH'}
etradie-engine  | 2026-04-15T17:20:09.905905Z [DEBUG    ] snd_candidate_created          [engine.ta.storage.repositories.candidate] extra={'symbol': 'US30X10M', 'pattern': 'SND_CONTINUATION', 'direction': 'BULLISH'}
etradie-engine  | 2026-04-15T17:20:09.910546Z [DEBUG    ] snd_candidate_created          [engine.ta.storage.repositories.candidate] extra={'symbol': 'US30X10M', 'pattern': 'SOP', 'direction': 'BULLISH'}
etradie-engine  | 2026-04-15T17:20:09.914823Z [DEBUG    ] snd_candidate_created          [engine.ta.storage.repositories.candidate] extra={'symbol': 'US30X10M', 'pattern': 'SND_CONTINUATION', 'direction': 'BULLISH'}
etradie-engine  | 2026-04-15T17:20:09.921088Z [DEBUG    ] snd_candidate_created          [engine.ta.storage.repositories.candidate] extra={'symbol': 'US30X10M', 'pattern': 'SOP', 'direction': 'BULLISH'}
etradie-engine  | 2026-04-15T17:20:09.926154Z [DEBUG    ] snd_candidate_created          [engine.ta.storage.repositories.candidate] extra={'symbol': 'US30X10M', 'pattern': 'SOP', 'direction': 'BULLISH'}
etradie-engine  | 2026-04-15T17:20:09.930877Z [DEBUG    ] snd_candidate_created          [engine.ta.storage.repositories.candidate] extra={'symbol': 'US30X10M', 'pattern': 'SOP', 'direction': 'BULLISH'}
etradie-engine  | 2026-04-15T17:20:09.937593Z [DEBUG    ] snd_candidate_created          [engine.ta.storage.repositories.candidate] extra={'symbol': 'US30X10M', 'pattern': 'SND_CONTINUATION', 'direction': 'BULLISH'}
etradie-engine  | 2026-04-15T17:20:09.941473Z [DEBUG    ] snd_candidate_created          [engine.ta.storage.repositories.candidate] extra={'symbol': 'US30X10M', 'pattern': 'SOP', 'direction': 'BULLISH'}
etradie-engine  | 2026-04-15T17:20:09.945745Z [DEBUG    ] snd_candidate_created          [engine.ta.storage.repositories.candidate] extra={'symbol': 'US30X10M', 'pattern': 'SND_CONTINUATION', 'direction': 'BULLISH'}
etradie-engine  | 2026-04-15T17:20:09.949662Z [DEBUG    ] snd_candidate_duplicate_skipped [engine.ta.storage.repositories.candidate] extra={'symbol': 'US30X10M', 'pattern': 'SOP', 'entry_price': 48599.4}
etradie-engine  | 2026-04-15T17:20:09.950053Z [ERROR    ] snd_candidate_persistence_failed [engine.ta.orchestrator] extra={'symbol': 'US30X10M', 'pattern': 'SOP', 'error': 'This result object is closed.'}
etradie-engine  | Traceback (most recent call last):
etradie-engine  |   File "/app/src/engine/ta/orchestrator.py", line 1065, in _persist_all_results
etradie-engine  |     await uow.candidate_repo.create_snd_candidate(
etradie-engine  |   File "/app/src/engine/ta/storage/repositories/candidate.py", line 152, in create_snd_candidate
etradie-engine  |     return existing.scalar_one_or_none()
etradie-engine  |            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 1485, in scalar_one_or_none
etradie-engine  |     return self._only_one_row(
etradie-engine  |            ^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 749, in _only_one_row
etradie-engine  |     row: Optional[_InterimRowType[Any]] = onerow(hard_close=True)
etradie-engine  |                                           ^^^^^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 2255, in _fetchone_impl
etradie-engine  |     self._raise_hard_closed()
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 2241, in _raise_hard_closed
etradie-engine  |     raise exc.ResourceClosedError("This result object is closed.")
etradie-engine  | sqlalchemy.exc.ResourceClosedError: This result object is closed.
etradie-engine  | 2026-04-15T17:20:09.956649Z [DEBUG    ] snd_candidate_created          [engine.ta.storage.repositories.candidate] extra={'symbol': 'US30X10M', 'pattern': 'SOP', 'direction': 'BULLISH'}
etradie-engine  | 2026-04-15T17:20:09.960698Z [DEBUG    ] snd_candidate_created
istence_failed [engine.ta.orchestrator] extra={'symbol': 'US30X10M', 'pattern': 'QMH_BASELINE', 'error': 'This result object is closed.'}
etradie-engine  | Traceback (most recent call last):
etradie-engine  |   File "/app/src/engine/ta/orchestrator.py", line 1065, in _persist_all_results
etradie-engine  |     await uow.candidate_repo.create_snd_candidate(
etradie-engine  |   File "/app/src/engine/ta/storage/repositories/candidate.py", line 152, in create_snd_candidate
etradie-engine  |     return existing.scalar_one_or_none()
etradie-engine  |            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 1485, in scalar_one_or_none
etradie-engine  |     return self._only_one_row(
etradie-engine  |            ^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 749, in _only_one_row
etradie-engine  |     row: Optional[_InterimRowType[Any]] = onerow(hard_close=True)
etradie-engine  |                                           ^^^^^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 2255, in _fetchone_impl
etradie-engine  |     self._raise_hard_closed()
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 2241, in _raise_hard_closed
etradie-engine  |     raise exc.ResourceClosedError("This result object is closed.")
etradie-engine  | sqlalchemy.exc.ResourceClosedError: This result object is closed.
etradie-engine  | 2026-04-15T17:20:10.014189Z [DEBUG    ] snd_candidate_duplicate_skipped [engine.ta.storage.repositories.candidate] extra={'symbol': 'US30X10M', 'pattern': 'QMH_BASELINE', 'entry_price': 47675.2}
etradie-engine  | 2026-04-15T17:20:10.014531Z [ERROR    ] snd_candidate_persistence_failed [engine.ta.orchestrator] extra={'symbol': 'US30X10M', 'pattern': 'QMH_BASELINE', 'error': 'This result object is closed.'}
etradie-engine  | Traceback (most recent call last):
etradie-engine  |   File "/app/src/engine/ta/orchestrator.py", line 1065, in _persist_all_results
etradie-engine  |     await uow.candidate_repo.create_snd_candidate(
etradie-engine  |   File "/app/src/engine/ta/storage/repositories/candidate.py", line 152, in create_snd_candidate
etradie-engine  |     return existing.scalar_one_or_none()
etradie-engine  |            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 1485, in scalar_one_or_none
etradie-engine  |     return self._only_one_row(
etradie-engine  |            ^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 749, in _only_one_row
etradie-engine  |     row: Optional[_InterimRowType[Any]] = onerow(hard_close=True)
etradie-engine  |                                           ^^^^^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 2255, in _fetchone_impl
etradie-engine  |     self._raise_hard_closed()
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 2241, in _raise_hard_closed
etradie-engine  |     raise exc.ResourceClosedError("This result object is closed.")
etradie-engine  | sqlalchemy.exc.ResourceClosedError: This result object is closed.
etradie-engine  | 2026-04-15T17:20:10.019578Z [DEBUG    ] snd_candidate_created          [engine.ta.storage.repositories.candidate] extra={'symbol': 'US30X10M', 'pattern': 'QMH_BASELINE', 'direction': 'BULLISH'}
etradie-engine  | 2026-04-15T17:20:10.024093Z [DEBUG    ] snd_candidate_created          [engine.ta.storage.repositories.candidate] extra={'symbol': 'US30X10M', 'pattern': 'QMH_KILLER_TYPE1', 'direction': 'BULLISH'}
etradie-engine  | 2026-04-15T17:20:10.031069Z [DEBUG    ] snd_candidate_created          [engine.ta.storage.repositories.candidate] extra={'symbol': 'US30X10M', 'pattern': 'QMH_KILLER_TYPE2', 'direction': 'BULLISH'}
etradie-engine  | 2026-04-15T17:20:10.035347Z [DEBUG    ] snd_candidate_created          [engine.ta.storage.repositories.candidate] extra={'symbol': 'US30X10M', 'pattern': 'QMH_BASELINE', 'direction': 'BULLISH'}
etradie-engine  | 2026-04-15T17:20:10.037801Z [DEBUG    ] snd_candidate_duplicate_skipped [engine.ta.storage.repositories.candidate] extra={'symbol': 'US30X10M', 'pattern': 'QML_BASELINE', 'entry_price': 47585.7}
etradie-engine  | 2026-04-15T17:20:10.038110Z [ERROR    ] snd_candidate_persistence_failed [engine.ta.orchestrator] extra={'symbol': 'US30X10M', 'pattern': 'QML_BASELINE', 'error': 'This result object is closed.'}
etradie-engine  | Traceback (most recent call last):
etradie-engine  |   File "/app/src/engine/ta/orchestrator.py", line 1065, in _persist_all_results
etradie-engine  |     await uow.candidate_repo.create_snd_candidate(
etradie-engine  |   File "/app/src/engine/ta/storage/repositories/candidate.py", line 152, in create_snd_candidate
etradie-engine  |     return existing.scalar_one_or_none()
etradie-engine  |            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 1485, in scalar_one_or_none
etradie-engine  |     return self._only_one_row(
etradie-engine  |            ^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 749, in _only_one_row
etradie-engine  |     row: Optional[_InterimRowType[Any]] = onerow(hard_close=True)
etradie-engine  |                                           ^^^^^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 2255, in _fetchone_impl
etradie-engine  |     self._raise_hard_closed()
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 2241, in _raise_hard_closed
etradie-engine  |     raise exc.ResourceClosedError("This result object is closed.")
etradie-engine  | sqlalchemy.exc.ResourceClosedError: This result object is closed.
etradie-engine  | 2026-04-15T17:20:10.044014Z [DEBUG    ] snd_candidate_duplicate_skipped [engine.ta.storage.repositories.candidate] extra={'symbol': 'US30X10M', 'pattern': 'QML_BASELINE', 'entry_price': 47707.7}
etradie-engine  | 2026-04-15T17:20:10.044345Z [ERROR    ] snd_candidate_persistence_failed [engine.ta.orchestrator] extra={'symbol': 'US30X10M', 'pattern': 'QML_BASELINE', 'error': 'This result object is closed.'}
etradie-engine  | Traceback (most recent call last):
etradie-engine  |   File "/app/src/engine/ta/orchestrator.py", line 1065, in _persist_all_results
etradie-engine  |     await uow.candidate_repo.create_snd_candidate(
etradie-engine  |   File "/app/src/engine/ta/storage/repositories/candidate.py", line 152, in create_snd_candidate
etradie-engine  |     return existing.scalar_one_or_none()
etradie-engine  |            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 1485, in scalar_one_or_none
etradie-engine  |     return self._only_one_row(
etradie-engine  |            ^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 749, in _only_one_row
etradie-engine  |     row: Optional[_InterimRowType[Any]] = onerow(hard_close=True)
etradie-engine  |                                           ^^^^^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 2255, in _fetchone_impl
etradie-engine  |     self._raise_hard_closed()
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 2241, in _raise_hard_closed
etradie-engine  |     raise exc.ResourceClosedError("This result object is closed.")
etradie-engine  | sqlalchemy.exc.ResourceClosedError: This result object is closed.
etradie-engine  | 2026-04-15T17:20:10.048787Z [DEBUG    ] snd_candidate_duplicate_skipped [engine.ta.storage.repositories.candidate] extra={'symbol': 'US30X10M', 'pattern': 'QML_BASELINE', 'entry_price': 47727.6}
etradie-engine  | 2026-04-15T17:20:10.049164Z [ERROR    ] snd_candidate_persistence_failed [engine.ta.orchestrator] extra={'symbol': 'US30X10M', 'pattern': 'QML_BASELINE', 'error': 'This result object is closed.'}
etradie-engine  | Traceback (most recent call last):
etradie-engine  |   File "/app/src/engine/ta/orchestrator.py", line 1065, in _persist_all_results
etradie-engine  |     await uow.candidate_repo.create_snd_candidate(
etradie-engine  |   File "/app/src/engine/ta/storage/repositories/candidate.py", line 152, in create_snd_candidate
etradie-engine  |     return existing.scalar_one_or_none()
etradie-engine  |            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 1485, in scalar_one_or_none
etradie-engine  |     return self._only_one_row(
etradie-engine  |            ^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 749, in _only_one_row
etradie-engine  |     row: Optional[_InterimRowType[Any]] = onerow(hard_close=True)
etradie-engine  |                                           ^^^^^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 2255, in _fetchone_impl
etradie-engine  |     self._raise_hard_closed()
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 2241, in _raise_hard_closed
etradie-engine  |     raise exc.ResourceClosedError("This result object is closed.")
etradie-engine  | sqlalchemy.exc.ResourceClosedError: This result object is closed.
etradie-engine  | 2026-04-15T17:20:10.053099Z [DEBUG    ] snd_candidate_duplicate_skipped [engine.ta.storage.repositories.candidate] extra={'symbol': 'US30X10M', 'pattern': 'QML_BASELINE', 'entry_price': 47751.0}
etradie-engine  | 2026-04-15T17:20:10.053713Z [ERROR    ] snd_candidate_persistence_failed [engine.ta.orchestrator] extra={'symbol': 'US30X10M', 'pattern': 'QML_BASELINE', 'error': 'This result object is closed.'}
etradie-engine  | Traceback (most recent call last):
etradie-engine  |   File "/app/src/engine/ta/orchestrator.py", line 1065, in _persist_all_results
etradie-engine  |     await uow.candidate_repo.create_snd_candidate(
etradie-engine  |   File "/app/src/engine/ta/storage/repositories/candidate.py", line 152, in create_snd_candidate
etradie-engine  |     return existing.scalar_one_or_none()
etradie-engine  |            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 1485, in scalar_one_or_none
etradie-engine  |     return self._only_one_row(
etradie-engine  |            ^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 749, in _only_one_row
etradie-engine  |     row: Optional[_InterimRowType[Any]] = onerow(hard_close=True)
etradie-engine  |                                           ^^^^^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 2255, in _fetchone_impl
etradie-engine  |     self._raise_hard_closed()
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 2241, in _raise_hard_closed
etradie-engine  |     raise exc.ResourceClosedError("This result object is closed.")
etradie-engine  | sqlalchemy.exc.ResourceClosedError: This result object is closed.
etradie-engine  | 2026-04-15T17:20:10.059610Z [DEBUG    ] snd_candidate_duplicate_skipped [engine.ta.storage.repositories.candidate] extra={'symbol': 'US30X10M', 'pattern': 'QML_BASELINE', 'entry_price': 48282.7}
etradie-engine  | 2026-04-15T17:20:10.060138Z [ERROR    ] snd_candidate_persistence_failed [engine.ta.orchestrator] extra={'symbol': 'US30X10M', 'pattern': 'QML_BASELINE', 'error': 'This result object is closed.'}
etradie-engine  | Traceback (most recent call last):
etradie-engine  |   File "/app/src/engine/ta/orchestrator.py", line 1065, in _persist_all_results
etradie-engine  |     await uow.candidate_repo.create_snd_candidate(
etradie-engine  |   File "/app/src/engine/ta/storage/repositories/candidate.py", line 152, in create_snd_candidate
etradie-engine  |     return existing.scalar_one_or_none()
etradie-engine  |            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 1485, in scalar_one_or_none
etradie-engine  |     return self._only_one_row(
etradie-engine  |            ^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 749, in _only_one_row
etradie-engine  |     row: Optional[_InterimRowType[Any]] = onerow(hard_close=True)
etradie-engine  |                                           ^^^^^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 2255, in _fetchone_impl
etradie-engine  |     self._raise_hard_closed()
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 2241, in _raise_hard_closed
etradie-engine  |     raise exc.ResourceClosedError("This result object is closed.")
etradie-engine  | sqlalchemy.exc.ResourceClosedError: This result object is closed.
etradie-engine  | 2026-04-15T17:20:10.065084Z [DEBUG    ] snd_candidate_duplicate_skipped [engine.ta.storage.repositories.candidate] extra={'symbol': 'US30X10M', 'pattern': 'QML_KILLER_TYPE2', 'entry_price': 48282.7}
etradie-engine  | 2026-04-15T17:20:10.065428Z [ERROR    ] snd_candidate_persistence_failed [engine.ta.orchestrator] extra={'symbol': 'US30X10M', 'pattern': 'QML_KILLER_TYPE2', 'error': 'This result object is closed.'}
etradie-engine  | Traceback (most recent call last):
etradie-engine  |   File "/app/src/engine/ta/orchestrator.py", line 1065, in _persist_all_results
etradie-engine  |     await uow.candidate_repo.create_snd_candidate(
etradie-engine  |   File "/app/src/engine/ta/storage/repositories/candidate.py", line 152, in create_snd_candidate
etradie-engine  |     return existing.scalar_one_or_none()
etradie-engine  |            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 1485, in scalar_one_or_none
etradie-engine  |     return self._only_one_row(
etradie-engine  |            ^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 749, in _only_one_row
etradie-engine  |     row: Optional[_InterimRowType[Any]] = onerow(hard_close=True)
etradie-engine  |                                           ^^^^^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 2255, in _fetchone_impl
etradie-engine  |     self._raise_hard_closed()
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 2241, in _raise_hard_closed
etradie-engine  |     raise exc.ResourceClosedError("This result object is closed.")
etradie-engine  | sqlalchemy.exc.ResourceClosedError: This result object is closed.
etradie-engine  | 2026-04-15T17:20:10.072100Z [DEBUG    ] snd_candidate_duplicate_skipped [engine.ta.storage.repositories.candidate] extra={'symbol': 'US30X10M', 'pattern': 'SOP', 'entry_price': 48533.2}
etradie-engine  | 2026-04-15T17:20:10.072681Z [ERROR    ] snd_candidate_persistence_failed [engine.ta.orchestrator] extra={'symbol': 'US30X10M', 'pattern': 'SOP', 'error': 'This result object is closed.'}
etradie-engine  | Traceback (most recent call last):
etradie-engine  |   File "/app/src/engine/ta/orchestrator.py", line 1065, in _persist_all_results
etradie-engine  |     await uow.candidate_repo.create_snd_candidate(
etradie-engine  |   File "/app/src/engine/ta/storage/repositories/candidate.py", line 152, in create_snd_candidate
etradie-engine  |     return existing.scalar_one_or_none()
etradie-engine  |            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 1485, in scalar_one_or_none
etradie-engine  |     return self._only_one_row(
etradie-engine  |            ^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 749, in _only_one_row
etradie-engine  |     row: Optional[_InterimRowType[Any]] = onerow(hard_close=True)
etradie-engine  |                                           ^^^^^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 2255, in _fetchone_impl
etradie-engine  |     self._raise_hard_closed()
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 2241, in _raise_hard_closed
etradie-engine  |     raise exc.ResourceClosedError("This result object is closed.")
etradie-engine  | sqlalchemy.exc.ResourceClosedError: This result object is closed.
etradie-engine  | 2026-04-15T17:20:10.078743Z [DEBUG    ] snd_candidate_created          [engine.ta.storage.repositories.candidate] extra={'symbol': 'US30X10M', 'pattern': 'SOP', 'direction': 'BEARISH'}
etradie-engine  | 2026-04-15T17:20:10.081736Z [DEBUG    ] snd_candidate_duplicate_skipped [engine.ta.storage.repositories.candidate] extra={'symbol': 'US30X10M', 'pattern': 'SOP', 'entry_price': 48565.2}
etradie-engine  | 2026-04-15T17:20:10.082169Z [ERROR    ] snd_candidate_persistence_failed [engine.ta.orchestrator] extra={'symbol': 'US30X10M', 'pattern': 'SOP', 'error': 'This result object is closed.'}
etradie-engine  | Traceback (most recent call last):
etradie-engine  |   File "/app/src/engine/ta/orchestrator.py", line 1065, in _persist_all_results
etradie-engine  |     await uow.candidate_repo.create_snd_candidate(
etradie-engine  |   File "/app/src/engine/ta/storage/repositories/candidate.py", line 152, in create_snd_candidate
etradie-engine  |     return existing.scalar_one_or_none()
etradie-engine  |            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 1485, in scalar_one_or_none
etradie-engine  |     return self._only_one_row(
etradie-engine  |            ^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 749, in _only_one_row
etradie-engine  |     row: Optional[_InterimRowType[Any]] = onerow(hard_close=True)
etradie-engine  |                                           ^^^^^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 2255, in _fetchone_impl
etradie-engine  |     self._raise_hard_closed()
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 2241, in _raise_hard_closed
etradie-engine  |     raise exc.ResourceClosedError("This result object is closed.")
etradie-engine  | sqlalchemy.exc.ResourceClosedError: This result object is closed.
etradie-engine  | 2026-04-15T17:20:10.087876Z [DEBUG    ] snd_candidate_duplicate_skipped [engine.ta.storage.repositories.candidate] extra={'symbol': 'US30X10M', 'pattern': 'SOP', 'entry_price': 48590.3}
etradie-engine  | 2026-04-15T17:20:10.088311Z [ERROR    ] snd_candidate_persistence_failed [engine.ta.orchestrator] extra={'symbol': 'US30X10M', 'pattern': 'SOP', 'error': 'This result object is closed.'}
etradie-engine  | Traceback (most recent call last):
etradie-engine  |   File "/app/src/engine/ta/orchestrator.py", line 1065, in _persist_all_results
etradie-engine  |     await uow.candidate_repo.create_snd_candidate(
etradie-engine  |   File "/app/src/engine/ta/storage/repositories/candidate.py", line 152, in create_snd_candidate
etradie-engine  |     return existing.scalar_one_or_none()
etradie-engine  |            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 1485, in scalar_one_or_none
etradie-engine  |     return self._only_one_row(
etradie-engine  |            ^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 749, in _only_one_row
etradie-engine  |     row: Optional[_InterimRowType[Any]] = onerow(hard_close=True)
etradie-engine  |                                           ^^^^^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 2255, in _fetchone_impl
etradie-engine  |     self._raise_hard_closed()
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 2241, in _raise_hard_closed
etradie-engine  |     raise exc.ResourceClosedError("This result object is closed.")
etradie-engine  | sqlalchemy.exc.ResourceClosedError: This result object is closed.
etradie-engine  | 2026-04-15T17:20:10.092956Z [DEBUG    ] snd_candidate_duplicate_skipped [engine.ta.storage.repositories.candidate] extra={'symbol': 'US30X10M', 'pattern': 'FAKEOUT_KING', 'entry_price': 48591.5}
etradie-engine  | 2026-04-15T17:20:10.093268Z [ERROR    ] snd_candidate_persistence_failed [engine.ta.orchestrator] extra={'symbol': 'US30X10M', 'pattern': 'FAKEOUT_KING', 'error': 'This result object is closed.'}
etradie-engine  | Traceback (most recent call last):
etradie-engine  |   File "/app/src/engine/ta/orchestrator.py", line 1065, in _persist_all_results
etradie-engine  |     await uow.candidate_repo.create_snd_candidate(
etradie-engine  |   File "/app/src/engine/ta/storage/repositories/candidate.py", line 152, in create_snd_candidate
etradie-engine  |     return existing.scalar_one_or_none()
etradie-engine  |            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 1485, in scalar_one_or_none
etradie-engine  |     return self._only_one_row(
etradie-engine  |            ^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 749, in _only_one_row
etradie-engine  |     row: Optional[_InterimRowType[Any]] = onerow(hard_close=True)
etradie-engine  |                                           ^^^^^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 2255, in _fetchone_impl
etradie-engine  |     self._raise_hard_closed()
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 2241, in _raise_hard_closed
etradie-engine  |     raise exc.ResourceClosedError("This result object is closed.")
etradie-engine  | sqlalchemy.exc.ResourceClosedError: This result object is closed.
etradie-engine  | 2026-04-15T17:20:10.098929Z [DEBUG    ] snd_candidate_created          [engine.ta.storage.repositories.candidate] extra={'symbol': 'US30X10M', 'pattern': 'SND_CONTINUATION', 'direction': 'BEARISH'}
etradie-engine  | 2026-04-15T17:20:10.103270Z [DEBUG    ] snd_candidate_duplicate_skipped [engine.ta.storage.repositories.candidate] extra={'symbol': 'US30X10M', 'pattern': 'SOP', 'entry_price': 48583.3}
etradie-engine  | 2026-04-15T17:20:10.104369Z [ERROR    ] snd_candidate_persistence_failed [engine.ta.orchestrator] extra={'symbol': 'US30X10M', 'pattern': 'SOP', 'error': 'This result object is closed.'}
etradie-engine  | Traceback (most recent call last):
etradie-engine  |   File "/app/src/engine/ta/orchestrator.py", line 1065, in _persist_all_results
etradie-engine  |     await uow.candidate_repo.create_snd_candidate(
etradie-engine  |   File "/app/src/engine/ta/storage/repositories/candidate.py", line 152, in create_snd_candidate
etradie-engine  |     return existing.scalar_one_or_none()
etradie-engine  |            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 1485, in scalar_one_or_none
etradie-engine  |     return self._only_one_row(
etradie-engine  |            ^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 749, in _only_one_row
etradie-engine  |     row: Optional[_InterimRowType[Any]] = onerow(hard_close=True)
etradie-engine  |                                           ^^^^^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 2255, in _fetchone_impl
etradie-engine  |     self._raise_hard_closed()
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 2241, in _raise_hard_closed
etradie-engine  |     raise exc.ResourceClosedError("This result object is closed.")
etradie-engine  | sqlalchemy.exc.ResourceClosedError: This result object is closed.
etradie-engine  | 2026-04-15T17:20:10.109951Z [DEBUG    ] snd_candidate_created          [engine.ta.storage.repositories.candidate] extra={'symbol': 'US30X10M', 'pattern': 'SND_CONTINUATION', 'direction': 'BEARISH'}
etradie-engine  | 2026-04-15T17:20:10.112970Z [DEBUG    ] snd_candidate_duplicate_skipped [engine.ta.storage.repositories.candidate] extra={'symbol': 'US30X10M', 'pattern': 'FAKEOUT_KING', 'entry_price': 48582.4}
etradie-engine  | 2026-04-15T17:20:10.113445Z [ERROR    ] snd_candidate_persistence_failed [engine.ta.orchestrator] extra={'symbol': 'US30X10M', 'pattern': 'FAKEOUT_KING', 'error': 'This result object is closed.'}
etradie-engine  | Traceback (most recent call last):
etradie-engine  |   File "/app/src/engine/ta/orchestrator.py", line 1065, in _persist_all_results
etradie-engine  |     await uow.candidate_repo.create_snd_candidate(
etradie-engine  |   File "/app/src/engine/ta/storage/repositories/candidate.py", line 152, in create_snd_candidate
etradie-engine  |     return existing.scalar_one_or_none()
etradie-engine  |            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 1485, in scalar_one_or_none
etradie-engine  |     return self._only_one_row(
etradie-engine  |            ^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 749, in _only_one_row
etradie-engine  |     row: Optional[_InterimRowType[Any]] = onerow(hard_close=True)
etradie-engine  |                                           ^^^^^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 2255, in _fetchone_impl
etradie-engine  |     self._raise_hard_closed()
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 2241, in _raise_hard_closed
etradie-engine  |     raise exc.ResourceClosedError("This result object is closed.")
etradie-engine  | sqlalchemy.exc.ResourceClosedError: This result object is closed.
etradie-engine  | 2026-04-15T17:20:10.121022Z [DEBUG    ] snd_candidate_created          [engine.ta.storage.repositories.candidate] extra={'symbol': 'US30X10M', 'pattern': 'SND_CONTINUATION', 'direction': 'BEARISH'}
etradie-engine  | 2026-04-15T17:20:10.123719Z [DEBUG    ] snd_candidate_duplicate_skipped [engine.ta.storage.repositories.candidate] extra={'symbol': 'US30X10M', 'pattern': 'SOP', 'entry_price': 48580.1}
etradie-engine  | 2026-04-15T17:20:10.124032Z [ERROR    ] snd_candidate_persistence_failed [engine.ta.orchestrator] extra={'symbol': 'US30X10M', 'pattern': 'SOP', 'error': 'This result object is closed.'}
etradie-engine  | Traceback (most recent call last):
etradie-engine  |   File "/app/src/engine/ta/orchestrator.py", line 1065, in _persist_all_results
etradie-engine  |     await uow.candidate_repo.create_snd_candidate(
etradie-engine  |   File "/app/src/engine/ta/storage/repositories/candidate.py", line 152, in create_snd_candidate
etradie-engine  |     return existing.scalar_one_or_none()
etradie-engine  |            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 1485, in scalar_one_or_none
etradie-engine  |     return self._only_one_row(
etradie-engine  |            ^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 749, in _only_one_row
etradie-engine  |     row: Optional[_InterimRowType[Any]] = onerow(hard_close=True)
etradie-engine  |                                           ^^^^^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 2255, in _fetchone_impl
etradie-engine  |     self._raise_hard_closed()
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 2241, in _raise_hard_closed
etradie-engine  |     raise exc.ResourceClosedError("This result object is closed.")
etradie-engine  | sqlalchemy.exc.ResourceClosedError: This result object is closed.
etradie-engine  | 2026-04-15T17:20:10.130548Z [DEBUG    ] snd_candidate_created          [engine.ta.storage.repositories.candidate] extra={'symbol': 'US30X10M', 'pattern': 'SND_CONTINUATION', 'direction': 'BEARISH'}
etradie-engine  | 2026-04-15T17:20:10.134275Z [DEBUG    ] snd_candidate_duplicate_skipped [engine.ta.storage.repositories.candidate] extra={'symbol': 'US30X10M', 'pattern': 'SOP', 'entry_price': 48585.3}
etradie-engine  | 2026-04-15T17:20:10.134759Z [ERROR    ] snd_candidate_persistence_failed [engine.ta.orchestrator] extra={'symbol': 'US30X10M', 'pattern': 'SOP', 'error': 'This result object is closed.'}
etradie-engine  | Traceback (most recent call last):
etradie-engine  |   File "/app/src/engine/ta/orchestrator.py", line 1065, in _persist_all_results
etradie-engine  |     await uow.candidate_repo.create_snd_candidate(
etradie-engine  |   File "/app/src/engine/ta/storage/repositories/candidate.py", line 152, in create_snd_candidate
etradie-engine  |     return existing.scalar_one_or_none()
etradie-engine  |            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 1485, in scalar_one_or_none
etradie-engine  |     return self._only_one_row(
etradie-engine  |            ^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 749, in _only_one_row
etradie-engine  |     row: Optional[_InterimRowType[Any]] = onerow(hard_close=True)
etradie-engine  |                                           ^^^^^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 2255, in _fetchone_impl
etradie-engine  |     self._raise_hard_closed()
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 2241, in _raise_hard_closed
etradie-engine  |     raise exc.ResourceClosedError("This result object is closed.")
etradie-engine  | sqlalchemy.exc.ResourceClosedError: This result object is closed.
etradie-engine  | 2026-04-15T17:20:10.141041Z [DEBUG    ] snd_candidate_created          [engine.ta.storage.repositories.candidate] extra={'symbol': 'US30X10M', 'pattern': 'SOP', 'direction': 'BEARISH'}
etradie-engine  | 2026-04-15T17:20:10.144439Z [DEBUG    ] snd_candidate_duplicate_skipped [engine.ta.storage.repositories.candidate] extra={'symbol': 'US30X10M', 'pattern': 'SOP', 'entry_price': 48591.2}
etradie-engine  | 2026-04-15T17:20:10.144782Z [ERROR    ] snd_candidate_persistence_failed [engine.ta.orchestrator] extra={'symbol': 'US30X10M', 'pattern': 'SOP', 'error': 'This result object is closed.'}
etradie-engine  | Traceback (most recent call last):
etradie-engine  |   File "/app/src/engine/ta/orchestrator.py", line 1065, in _persist_all_results
etradie-engine  |     await uow.candidate_repo.create_snd_candidate(
etradie-engine  |   File "/app/src/engine/ta/storage/repositories/candidate.py", line 152, in create_snd_candidate
etradie-engine  |     return existing.scalar_one_or_none()
etradie-engine  |            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 1485, in scalar_one_or_none
etradie-engine  |     return self._only_one_row(
etradie-engine  |            ^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 749, in _only_one_row
etradie-engine  |     row: Optional[_InterimRowType[Any]] = onerow(hard_close=True)
etradie-engine  |                                           ^^^^^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 2255, in _fetchone_impl
etradie-engine  |     self._raise_hard_closed()
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 2241, in _raise_hard_closed
etradie-engine  |     raise exc.ResourceClosedError("This result object is closed.")
etradie-engine  | sqlalchemy.exc.ResourceClosedError: This result object is closed.
etradie-engine  | 2026-04-15T17:20:10.153203Z [DEBUG    ] snd_candidate_created          [engine.ta.storage.repositories.candidate] extra={'symbol': 'US30X10M', 'pattern': 'FAKEOUT_KING', 'direction': 'BEARISH'}
d          [engine.ta.storage.repositories.candidate] extra={'symbol': 'US30X10M', 'pattern': 'SND_CONTINUATION', 'direction': 'BEARISH'}
etradie-engine  | 2026-04-15T17:20:10.225399Z [DEBUG    ] snd_candidate_created          [engine.ta.storage.repositories.candidate] extra={'symbol': 'US30X10M', 'pattern': 'SOP', 'direction': 'BEARISH'}
etradie-engine  | 2026-04-15T17:20:10.229231Z [DEBUG    ] snd_candidate_duplicate_skipped [engine.ta.storage.repositories.candidate] extra={'symbol': 'US30X10M', 'pattern': 'QML_BASELINE', 'entry_price': 48275.7}
etradie-engine  | 2026-04-15T17:20:10.229594Z [ERROR    ] snd_candidate_persistence_failed [engine.ta.orchestrator] extra={'symbol': 'US30X10M', 'pattern': 'QML_BASELINE', 'error': 'This result object is closed.'}
etradie-engine  | Traceback (most recent call last):
etradie-engine  |   File "/app/src/engine/ta/orchestrator.py", line 1065, in _persist_all_results
etradie-engine  |     await uow.candidate_repo.create_snd_candidate(
etradie-engine  |   File "/app/src/engine/ta/storage/repositories/candidate.py", line 152, in create_snd_candidate
etradie-engine  |     return existing.scalar_one_or_none()
etradie-engine  |            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 1485, in scalar_one_or_none
etradie-engine  |     return self._only_one_row(
etradie-engine  |            ^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 749, in _only_one_row
etradie-engine  |     row: Optional[_InterimRowType[Any]] = onerow(hard_close=True)
etradie-engine  |                                           ^^^^^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 2255, in _fetchone_impl
etradie-engine  |     self._raise_hard_closed()
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 2241, in _raise_hard_closed
etradie-engine  |     raise exc.ResourceClosedError("This result object is closed.")
etradie-engine  | sqlalchemy.exc.ResourceClosedError: This result object is closed.
etradie-engine  | 2026-04-15T17:20:10.233662Z [DEBUG    ] snd_candidate_duplicate_skipped [engine.ta.storage.repositories.candidate] extra={'symbol': 'US30X10M', 'pattern': 'QML_KILLER_TYPE2', 'entry_price': 48275.7}
etradie-engine  | 2026-04-15T17:20:10.234109Z [ERROR    ] snd_candidate_persistence_failed [engine.ta.orchestrator] extra={'symbol': 'US30X10M', 'pattern': 'QML_KILLER_TYPE2', 'error': 'This result object is closed.'}
etradie-engine  | Traceback (most recent call last):
etradie-engine  |   File "/app/src/engine/ta/orchestrator.py", line 1065, in _persist_all_results
etradie-engine  |     await uow.candidate_repo.create_snd_candidate(
etradie-engine  |   File "/app/src/engine/ta/storage/repositories/candidate.py", line 152, in create_snd_candidate
etradie-engine  |     return existing.scalar_one_or_none()
etradie-engine  |            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 1485, in scalar_one_or_none
etradie-engine  |     return self._only_one_row(
etradie-engine  |            ^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 749, in _only_one_row
etradie-engine  |     row: Optional[_InterimRowType[Any]] = onerow(hard_close=True)
etradie-engine  |                                           ^^^^^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 2255, in _fetchone_impl
etradie-engine  |     self._raise_hard_closed()
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 2241, in _raise_hard_closed
etradie-engine  |     raise exc.ResourceClosedError("This result object is closed.")
etradie-engine  | sqlalchemy.exc.ResourceClosedError: This result object is closed.
etradie-engine  | 2026-04-15T17:20:10.241111Z [DEBUG    ] snd_candidate_duplicate_skipped [engine.ta.storage.repositories.candidate] extra={'symbol': 'US30X10M', 'pattern': 'QML_BASELINE', 'entry_price': 48276.5}
etradie-engine  | 2026-04-15T17:20:10.241948Z [ERROR    ] snd_candidate_persistence_failed [engine.ta.orchestrator] extra={'symbol': 'US30X10M', 'pattern': 'QML_BASELINE', 'error': 'This result object is closed.'}
etradie-engine  | Traceback (most recent call last):
etradie-engine  |   File "/app/src/engine/ta/orchestrator.py", line 1065, in _persist_all_results
etradie-engine  |     await uow.candidate_repo.create_snd_candidate(
etradie-engine  |   File "/app/src/engine/ta/storage/repositories/candidate.py", line 152, in create_snd_candidate
etradie-engine  |     return existing.scalar_one_or_none()
etradie-engine  |            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 1485, in scalar_one_or_none
etradie-engine  |     return self._only_one_row(
etradie-engine  |            ^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 749, in _only_one_row
etradie-engine  |     row: Optional[_InterimRowType[Any]] = onerow(hard_close=True)
etradie-engine  |                                           ^^^^^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 2255, in _fetchone_impl
etradie-engine  |     self._raise_hard_closed()
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 2241, in _raise_hard_closed
etradie-engine  |     raise exc.ResourceClosedError("This result object is closed.")
etradie-engine  | sqlalchemy.exc.ResourceClosedError: This result object is closed.
etradie-engine  | 2026-04-15T17:20:10.246768Z [DEBUG    ] snd_candidate_duplicate_skipped [engine.ta.storage.repositories.candidate] extra={'symbol': 'US30X10M', 'pattern': 'QML_KILLER_TYPE2', 'entry_price': 48276.5}
etradie-engine  | 2026-04-15T17:20:10.247084Z [ERROR    ] snd_candidate_persistence_failed [engine.ta.orchestrator] extra={'symbol': 'US30X10M', 'pattern': 'QML_KILLER_TYPE2', 'error': 'This result object is closed.'}
etradie-engine  | Traceback (most recent call last):
etradie-engine  |   File "/app/src/engine/ta/orchestrator.py", line 1065, in _persist_all_results
etradie-engine  |     await uow.candidate_repo.create_snd_candidate(
etradie-engine  |   File "/app/src/engine/ta/storage/repositories/candidate.py", line 152, in create_snd_candidate
etradie-engine  |     return existing.scalar_one_or_none()
etradie-engine  |            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 1485, in scalar_one_or_none
etradie-engine  |     return self._only_one_row(
etradie-engine  |            ^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 749, in _only_one_row
etradie-engine  |     row: Optional[_InterimRowType[Any]] = onerow(hard_close=True)
etradie-engine  |                                           ^^^^^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 2255, in _fetchone_impl
etradie-engine  |     self._raise_hard_closed()
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 2241, in _raise_hard_closed
etradie-engine  |     raise exc.ResourceClosedError("This result object is closed.")
etradie-engine  | sqlalchemy.exc.ResourceClosedError: This result object is closed.
etradie-engine  | 2026-04-15T17:20:10.251331Z [DEBUG    ] snd_candidate_duplicate_skipped [engine.ta.storage.repositories.candidate] extra={'symbol': 'US30X10M', 'pattern': 'QML_BASELINE', 'entry_price': 48279.7}
etradie-engine  | 2026-04-15T17:20:10.251642Z [ERROR    ] snd_candidate_persistence_failed [engine.ta.orchestrator] extra={'symbol': 'US30X10M', 'pattern': 'QML_BASELINE', 'error': 'This result object is closed.'}
etradie-engine  | Traceback (most recent call last):
etradie-engine  |   File "/app/src/engine/ta/orchestrator.py", line 1065, in _persist_all_results
etradie-engine  |     await uow.candidate_repo.create_snd_candidate(
etradie-engine  |   File "/app/src/engine/ta/storage/repositories/candidate.py", line 152, in create_snd_candidate
etradie-engine  |     return existing.scalar_one_or_none()
etradie-engine  |            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 1485, in scalar_one_or_none
etradie-engine  |     return self._only_one_row(
etradie-engine  |            ^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 749, in _only_one_row
etradie-engine  |     row: Optional[_InterimRowType[Any]] = onerow(hard_close=True)
etradie-engine  |                                           ^^^^^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 2255, in _fetchone_impl
etradie-engine  |     self._raise_hard_closed()
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 2241, in _raise_hard_closed
etradie-engine  |     raise exc.ResourceClosedError("This result object is closed.")
etradie-engine  | sqlalchemy.exc.ResourceClosedError: This result object is closed.
etradie-engine  | 2026-04-15T17:20:10.257955Z [DEBUG    ] snd_candidate_duplicate_skipped [engine.ta.storage.repositories.candidate] extra={'symbol': 'US30X10M', 'pattern': 'QML_KILLER_TYPE2', 'entry_price': 48279.7}
etradie-engine  | 2026-04-15T17:20:10.258386Z [ERROR    ] snd_candidate_persistence_failed [engine.ta.orchestrator] extra={'symbol': 'US30X10M', 'pattern': 'QML_KILLER_TYPE2', 'error': 'This result object is closed.'}
etradie-engine  | Traceback (most recent call last):
etradie-engine  |   File "/app/src/engine/ta/orchestrator.py", line 1065, in _persist_all_results
etradie-engine  |     await uow.candidate_repo.create_snd_candidate(
etradie-engine  |   File "/app/src/engine/ta/storage/repositories/candidate.py", line 152, in create_snd_candidate
etradie-engine  |     return existing.scalar_one_or_none()
etradie-engine  |            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 1485, in scalar_one_or_none
etradie-engine  |     return self._only_one_row(
etradie-engine  |            ^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 749, in _only_one_row
etradie-engine  |     row: Optional[_InterimRowType[Any]] = onerow(hard_close=True)
etradie-engine  |                                           ^^^^^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 2255, in _fetchone_impl
etradie-engine  |     self._raise_hard_closed()
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 2241, in _raise_hard_closed
etradie-engine  |     raise exc.ResourceClosedError("This result object is closed.")
etradie-engine  | sqlalchemy.exc.ResourceClosedError: This result object is closed.
etradie-engine  | 2026-04-15T17:20:10.262226Z [DEBUG    ] snd_candidate_duplicate_skipped [engine.ta.storage.repositories.candidate] extra={'symbol': 'US30X10M', 'pattern': 'QML_KILLER_TYPE2', 'entry_price': 48263.6}
etradie-engine  | 2026-04-15T17:20:10.262649Z [ERROR    ] snd_candidate_persistence_failed [engine.ta.orchestrator] extra={'symbol': 'US30X10M', 'pattern': 'QML_KILLER_TYPE2', 'error': 'This result object is closed.'}
etradie-engine  | Traceback (most recent call last):
etradie-engine  |   File "/app/src/engine/ta/orchestrator.py", line 1065, in _persist_all_results
etradie-engine  |     await uow.candidate_repo.create_snd_candidate(
etradie-engine  |   File "/app/src/engine/ta/storage/repositories/candidate.py", line 152, in create_snd_candidate
etradie-engine  |     return existing.scalar_one_or_none()
etradie-engine  |            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 1485, in scalar_one_or_none
etradie-engine  |     return self._only_one_row(
etradie-engine  |            ^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 749, in _only_one_row
etradie-engine  |     row: Optional[_InterimRowType[Any]] = onerow(hard_close=True)
etradie-engine  |                                           ^^^^^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 2255, in _fetchone_impl
etradie-engine  |     self._raise_hard_closed()
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 2241, in _raise_hard_closed
etradie-engine  |     raise exc.ResourceClosedError("This result object is closed.")
etradie-engine  | sqlalchemy.exc.ResourceClosedError: This result object is closed.
etradie-engine  | 2026-04-15T17:20:10.266300Z [DEBUG    ] snd_candidate_duplicate_skipped [engine.ta.storage.repositories.candidate] extra={'symbol': 'US30X10M', 'pattern': 'QML_BASELINE', 'entry_price': 48335.7}
etradie-engine  | 2026-04-15T17:20:10.266740Z [ERROR    ] snd_candidate_persistence_failed [engine.ta.orchestrator] extra={'symbol': 'US30X10M', 'pattern': 'QML_BASELINE', 'error': 'This result object is closed.'}
etradie-engine  | Traceback (most recent call last):
etradie-engine  |   File "/app/src/engine/ta/orchestrator.py", line 1065, in _persist_all_results
etradie-engine  |     await uow.candidate_repo.create_snd_candidate(
etradie-engine  |   File "/app/src/engine/ta/storage/repositories/candidate.py", line 152, in create_snd_candidate
etradie-engine  |     return existing.scalar_one_or_none()
etradie-engine  |            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 1485, in scalar_one_or_none
etradie-engine  |     return self._only_one_row(
etradie-engine  |            ^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 749, in _only_one_row
etradie-engine  |     row: Optional[_InterimRowType[Any]] = onerow(hard_close=True)
etradie-engine  |                                           ^^^^^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 2255, in _fetchone_impl
etradie-engine  |     self._raise_hard_closed()
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 2241, in _raise_hard_closed
etradie-engine  |     raise exc.ResourceClosedError("This result object is closed.")
etradie-engine  | sqlalchemy.exc.ResourceClosedError: This result object is closed.
etradie-engine  | 2026-04-15T17:20:10.274094Z [DEBUG    ] snd_candidate_duplicate_skipped [engine.ta.storage.repositories.candidate] extra={'symbol': 'US30X10M', 'pattern': 'QML_KILLER_TYPE2', 'entry_price': 48335.7}
etradie-engine  | 2026-04-15T17:20:10.274423Z [ERROR    ] snd_candidate_persistence_failed [engine.ta.orchestrator] extra={'symbol': 'US30X10M', 'pattern': 'QML_KILLER_TYPE2', 'error': 'This result object is closed.'}
etradie-engine  | Traceback (most recent call last):
etradie-engine  |   File "/app/src/engine/ta/orchestrator.py", line 1065, in _persist_all_results
etradie-engine  |     await uow.candidate_repo.create_snd_candidate(
etradie-engine  |   File "/app/src/engine/ta/storage/repositories/candidate.py", line 152, in create_snd_candidate
etradie-engine  |     return existing.scalar_one_or_none()
etradie-engine  |            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 1485, in scalar_one_or_none
etradie-engine  |     return self._only_one_row(
etradie-engine  |            ^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 749, in _only_one_row
etradie-engine  |     row: Optional[_InterimRowType[Any]] = onerow(hard_close=True)
etradie-engine  |                                           ^^^^^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 2255, in _fetchone_impl
etradie-engine  |     self._raise_hard_closed()
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 2241, in _raise_hard_closed
etradie-engine  |     raise exc.ResourceClosedError("This result object is closed.")
etradie-engine  | sqlalchemy.exc.ResourceClosedError: This result object is closed.
etradie-engine  | 2026-04-15T17:20:10.280605Z [DEBUG    ] snd_candidate_created          [engine.ta.storage.repositories.candidate] extra={'symbol': 'US30X10M', 'pattern': 'QML_BASELINE', 'direction': 'BEARISH'}
etradie-engine  | 2026-04-15T17:20:10.289014Z [DEBUG    ] snd_candidate_created          [engine.ta.storage.repositories.candidate] extra={'symbol': 'US30X10M', 'pattern': 'QML_BASELINE', 'direction': 'BEARISH'}
etradie-engine  | 2026-04-15T17:20:10.293439Z [DEBUG    ] snd_candidate_created          [engine.ta.storage.repositories.candidate] extra={'symbol': 'US30X10M', 'pattern': 'QML_KILLER_TYPE2', 'direction': 'BEARISH'}
etradie-engine  | 2026-04-15T17:20:10.296120Z [DEBUG    ] snd_candidate_duplicate_skipped [engine.ta.storage.repositories.candidate] extra={'symbol': 'US30X10M', 'pattern': 'QML_BASELINE', 'entry_price': 48599.4}
etradie-engine  | 2026-04-15T17:20:10.296438Z [ERROR    ] snd_candidate_persistence_failed [engine.ta.orchestrator] extra={'symbol': 'US30X10M', 'pattern': 'QML_BASELINE', 'error': 'This result object is closed.'}
etradie-engine  | Traceback (most recent call last):
etradie-engine  |   File "/app/src/engine/ta/orchestrator.py", line 1065, in _persist_all_results
etradie-engine  |     await uow.candidate_repo.create_snd_candidate(
etradie-engine  |   File "/app/src/engine/ta/storage/repositories/candidate.py", line 152, in create_snd_candidate
etradie-engine  |     return existing.scalar_one_or_none()
etradie-engine  |            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 1485, in scalar_one_or_none
etradie-engine  |     return self._only_one_row(
etradie-engine  |            ^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 749, in _only_one_row
etradie-engine  |     row: Optional[_InterimRowType[Any]] = onerow(hard_close=True)
etradie-engine  |                                           ^^^^^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 2255, in _fetchone_impl
etradie-engine  |     self._raise_hard_closed()
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 2241, in _raise_hard_closed
etradie-engine  |     raise exc.ResourceClosedError("This result object is closed.")
etradie-engine  | sqlalchemy.exc.ResourceClosedError: This result object is closed.
etradie-engine  | 2026-04-15T17:20:10.301317Z [DEBUG    ] snd_candidate_duplicate_skipped [engine.ta.storage.repositories.candidate] extra={'symbol': 'US30X10M', 'pattern': 'QML_KILLER_TYPE2', 'entry_price': 48599.4}
etradie-engine  | 2026-04-15T17:20:10.302074Z [ERROR    ] snd_candidate_persistence_failed [engine.ta.orchestrator] extra={'symbol': 'US30X10M', 'pattern': 'QML_KILLER_TYPE2', 'error': 'This result object is closed.'}
etradie-engine  | Traceback (most recent call last):
etradie-engine  |   File "/app/src/engine/ta/orchestrator.py", line 1065, in _persist_all_results
etradie-engine  |     await uow.candidate_repo.create_snd_candidate(
etradie-engine  |   File "/app/src/engine/ta/storage/repositories/candidate.py", line 152, in create_snd_candidate
etradie-engine  |     return existing.scalar_one_or_none()
etradie-engine  |            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 1485, in scalar_one_or_none
etradie-engine  |     return self._only_one_row(
etradie-engine  |            ^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 749, in _only_one_row
etradie-engine  |     row: Optional[_InterimRowType[Any]] = onerow(hard_close=True)
etradie-engine  |                                           ^^^^^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 2255, in _fetchone_impl
etradie-engine  |     self._raise_hard_closed()
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 2241, in _raise_hard_closed
etradie-engine  |     raise exc.ResourceClosedError("This result object is closed.")
etradie-engine  | sqlalchemy.exc.ResourceClosedError: This result object is closed.
etradie-engine  | 2026-04-15T17:20:10.309181Z [DEBUG    ] snd_candidate_created          [engine.ta.storage.repositories.candidate] extra={'symbol': 'US30X10M', 'pattern': 'QML_BASELINE', 'direction': 'BEARISH'}
etradie-engine  | 2026-04-15T17:20:10.313486Z [DEBUG    ] snd_candidate_created          [engine.ta.storage.repositories.candidate] extra={'symbol': 'US30X10M', 'pattern': 'QML_KILLER_TYPE2', 'direction': 'BEARISH'}
etradie-engine  | 2026-04-15T17:20:10.319226Z [DEBUG    ] snd_candidate_created          [engine.ta.storage.repositories.candidate] extra={'symbol': 'US30X10M', 'pattern': 'QML_BASELINE', 'direction': 'BEARISH'}
etradie-engine  | 2026-04-15T17:20:10.323295Z [DEBUG    ] snd_candidate_created          [engine.ta.storage.repositories.candidate] extra={'symbol': 'US30X10M', 'pattern': 'QML_BASELINE', 'direction': 'BEARISH'}
etradie-engine  | 2026-04-15T17:20:10.325999Z [DEBUG    ] snd_candidate_duplicate_skipped [engine.ta.storage.repositories.candidate] extra={'symbol': 'US30X10M', 'pattern': 'QMH_BASELINE', 'entry_price': 47548.4}
etradie-engine  | 2026-04-15T17:20:10.326326Z [ERROR    ] snd_candidate_persistence_failed [engine.ta.orchestrator] extra={'symbol': 'US30X10M', 'pattern': 'QMH_BASELINE', 'error': 'This result object is closed.'}
etradie-engine  | Traceback (most recent call last):
etradie-engine  |   File "/app/src/engine/ta/orchestrator.py", line 1065, in _persist_all_results
etradie-engine  |     await uow.candidate_repo.create_snd_candidate(
etradie-engine  |   File "/app/src/engine/ta/storage/repositories/candidate.py", line 152, in create_snd_candidate
etradie-engine  |     return existing.scalar_one_or_none()
etradie-engine  |            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 1485, in scalar_one_or_none
etradie-engine  |     return self._only_one_row(
etradie-engine  |            ^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 749, in _only_one_row
etradie-engine  |     row: Optional[_InterimRowType[Any]] = onerow(hard_close=True)
etradie-engine  |                                           ^^^^^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 2255, in _fetchone_impl
etradie-engine  |     self._raise_hard_closed()
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 2241, in _raise_hard_closed
etradie-engine  |     raise exc.ResourceClosedError("This result object is closed.")
etradie-engine  | sqlalchemy.exc.ResourceClosedError: This result object is closed.
etradie-engine  | 2026-04-15T17:20:10.331514Z [DEBUG    ] snd_candidate_duplicate_skipped [engine.ta.storage.repositories.candidate] extra={'symbol': 'US30X10M', 'pattern': 'QMH_KILLER_TYPE1', 'entry_price': 47548.4}
etradie-engine  | 2026-04-15T17:20:10.332219Z [ERROR    ] snd_candidate_persistence_failed [engine.ta.orchestrator] extra={'symbol': 'US30X10M', 'pattern': 'QMH_KILLER_TYPE1', 'error': 'This result object is closed.'}
etradie-engine  | Traceback (most recent call last):
etradie-engine  |   File "/app/src/engine/ta/orchestrator.py", line 1065, in _persist_all_results
etradie-engine  |     await uow.candidate_repo.create_snd_candidate(
etradie-engine  |   File "/app/src/engine/ta/storage/repositories/candidate.py", line 152, in create_snd_candidate
etradie-engine  |     return existing.scalar_one_or_none()
etradie-engine  |            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 1485, in scalar_one_or_none
etradie-engine  |     return self._only_one_row(
etradie-engine  |            ^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 749, in _only_one_row
etradie-engine  |     row: Optional[_InterimRowType[Any]] = onerow(hard_close=True)
etradie-engine  |                                           ^^^^^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 2255, in _fetchone_impl
etradie-engine  |     self._raise_hard_closed()
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 2241, in _raise_hard_closed
etradie-engine  |     raise exc.ResourceClosedError("This result object is closed.")
etradie-engine  | sqlalchemy.exc.ResourceClosedError: This result object is closed.
etradie-engine  | 2026-04-15T17:20:10.336506Z [DEBUG    ] snd_candidate_duplicate_skipped [engine.ta.storage.repositories.candidate] extra={'symbol': 'US30X10M', 'pattern': 'SOP', 'entry_price': 48567.8}
etradie-engine  | 2026-04-15T17:20:10.336889Z [ERROR    ] snd_candidate_persistence_failed [engine.ta.orchestrator] extra={'symbol': 'US30X10M', 'pattern': 'SOP', 'error': 'This result object is closed.'}
etradie-engine  | Traceback (most recent call last):
etradie-engine  |   File "/app/src/engine/ta/orchestrator.py", line 1065, in _persist_all_results
etradie-engine  |     await uow.candidate_repo.create_snd_candidate(
etradie-engine  |   File "/app/src/engine/ta/storage/repositories/candidate.py", line 152, in create_snd_candidate
etradie-engine  |     return existing.scalar_one_or_none()
etradie-engine  |            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 1485, in scalar_one_or_none
etradie-engine  |     return self._only_one_row(
etradie-engine  |            ^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 749, in _only_one_row
etradie-engine  |     row: Optional[_InterimRowType[Any]] = onerow(hard_close=True)
etradie-engine  |                                           ^^^^^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 2255, in _fetchone_impl
etradie-engine  |     self._raise_hard_closed()
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 2241, in _raise_hard_closed
etradie-engine  |     raise exc.ResourceClosedError("This result object is closed.")
etradie-engine  | sqlalchemy.exc.ResourceClosedError: This result object is closed.
etradie-engine  | 2026-04-15T17:20:10.340974Z [DEBUG    ] snd_candidate_duplicate_skipped [engine.ta.storage.repositories.candidate] extra={'symbol': 'US30X10M', 'pattern': 'SOP', 'entry_price': 48530.8}
etradie-engine  | 2026-04-15T17:20:10.341374Z [ERROR    ] snd_candidate_persistence_failed [engine.ta.orchestrator] extra={'symbol': 'US30X10M', 'pattern': 'SOP', 'error': 'This result object is closed.'}
etradie-engine  | Traceback (most recent call last):
etradie-engine  |   File "/app/src/engine/ta/orchestrator.py", line 1065, in _persist_all_results
etradie-engine  |     await uow.candidate_repo.create_snd_candidate(
etradie-engine  |   File "/app/src/engine/ta/storage/repositories/candidate.py", line 152, in create_snd_candidate
etradie-engine  |     return existing.scalar_one_or_none()
etradie-engine  |            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 1485, in scalar_one_or_none
etradie-engine  |     return self._only_one_row(
etradie-engine  |            ^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 749, in _only_one_row
etradie-engine  |     row: Optional[_InterimRowType[Any]] = onerow(hard_close=True)
etradie-engine  |                                           ^^^^^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 2255, in _fetchone_impl
etradie-engine  |     self._raise_hard_closed()
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 2241, in _raise_hard_closed
etradie-engine  |     raise exc.ResourceClosedError("This result object is closed.")
etradie-engine  | sqlalchemy.exc.ResourceClosedError: This result object is closed.
etradie-engine  | 2026-04-15T17:20:10.347126Z [DEBUG    ] snd_candidate_duplicate_skipped [engine.ta.storage.repositories.candidate] extra={'symbol': 'US30X10M', 'pattern': 'FAKEOUT_KING', 'entry_price': 48543.6}
etradie-engine  | 2026-04-15T17:20:10.347735Z [ERROR    ] snd_candidate_persistence_failed [engine.ta.orchestrator] extra={'symbol': 'US30X10M', 'pattern': 'FAKEOUT_KING', 'error': 'This result object is closed.'}
etradie-engine  | Traceback (most recent call last):
etradie-engine  |   File "/app/src/engine/ta/orchestrator.py", line 1065, in _persist_all_results
etradie-engine  |     await uow.candidate_repo.create_snd_candidate(
etradie-engine  |   File "/app/src/engine/ta/storage/repositories/candidate.py", line 152, in create_snd_candidate
etradie-engine  |     return existing.scalar_one_or_none()
etradie-engine  |            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 1485, in scalar_one_or_none
etradie-engine  |     return self._only_one_row(
etradie-engine  |            ^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 749, in _only_one_row
etradie-engine  |     row: Optional[_InterimRowType[Any]] = onerow(hard_close=True)
etradie-engine  |                                           ^^^^^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 2255, in _fetchone_impl
etradie-engine  |     self._raise_hard_closed()
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 2241, in _raise_hard_closed
etradie-engine  |     raise exc.ResourceClosedError("This result object is closed.")
etradie-engine  | sqlalchemy.exc.ResourceClosedError: This result object is closed.
etradie-engine  | 2026-04-15T17:20:10.353643Z [DEBUG    ] snd_candidate_created          [engine.ta.storage.repositories.candidate] extra={'symbol': 'US30X10M', 'pattern': 'SND_CONTINUATION', 'direction': 'BULLISH'}
etradie-engine  | 2026-04-15T17:20:10.356231Z [DEBUG    ] snd_candidate_duplicate_skipped [engine.ta.storage.repositories.candidate] extra={'symbol': 'US30X10M', 'pattern': 'SOP', 'entry_price': 48562.3}
etradie-engine  | 2026-04-15T17:20:10.356896Z [ERROR    ] snd_candidate_persistence_failed [engine.ta.orchestrator] extra={'symbol': 'US30X10M', 'pattern': 'SOP', 'error': 'This result object is closed.'}
etradie-engine  | Traceback (most recent call last):
etradie-engine  |   File "/app/src/engine/ta/orchestrator.py", line 1065, in _persist_all_results
etradie-engine  |     await uow.candidate_repo.create_snd_candidate(
etradie-engine  |   File "/app/src/engine/ta/storage/repositories/candidate.py", line 152, in create_snd_candidate
etradie-engine  |     return existing.scalar_one_or_none()
etradie-engine  |            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 1485, in scalar_one_or_none
etradie-engine  |     return self._only_one_row(
etradie-engine  |            ^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 749, in _only_one_row
etradie-engine  |     row: Optional[_InterimRowType[Any]] = onerow(hard_close=True)
etradie-engine  |                                           ^^^^^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 2255, in _fetchone_impl
etradie-engine  |     self._raise_hard_closed()
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 2241, in _raise_hard_closed
etradie-engine  |     raise exc.ResourceClosedError("This result object is closed.")
etradie-engine  | sqlalchemy.exc.ResourceClosedError: This result object is closed.
etradie-engine  | 2026-04-15T17:20:10.364094Z [DEBUG    ] snd_candidate_duplicate_skipped [engine.ta.storage.repositories.candidate] extra={'symbol': 'US30X10M', 'pattern': 'SOP', 'entry_price': 48587.6}
etradie-engine  | 2026-04-15T17:20:10.364427Z [ERROR    ] snd_candidate_persistence_failed [engine.ta.orchestrator] extra={'symbol': 'US30X10M', 'pattern': 'SOP', 'error': 'This result object is closed.'}
etradie-engine  | Traceback (most recent call last):
etradie-engine  |   File "/app/src/engine/ta/orchestrator.py", line 1065, in _persist_all_results
etradie-engine  |     await uow.candidate_repo.create_snd_candidate(
etradie-engine  |   File "/app/src/engine/ta/storage/repositories/candidate.py", line 152, in create_snd_candidate
etradie-engine  |     return existing.scalar_one_or_none()
etradie-engine  |            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 1485, in scalar_one_or_none
etradie-engine  |     return self._only_one_row(
etradie-engine  |            ^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 749, in _only_one_row
etradie-engine  |     row: Optional[_InterimRowType[Any]] = onerow(hard_close=True)
etradie-engine  |                                           ^^^^^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 2255, in _fetchone_impl
etradie-engine  |     self._raise_hard_closed()
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 2241, in _raise_hard_closed
etradie-engine  |     raise exc.ResourceClosedError("This result object is closed.")
etradie-engine  | sqlalchemy.exc.ResourceClosedError: This result object is closed.
etradie-engine  | 2026-04-15T17:20:10.369515Z [DEBUG    ] snd_candidate_created          [engine.ta.storage.repositories.candidate] extra={'symbol': 'US30X10M', 'pattern': 'FAKEOUT_KING', 'direction': 'BULLISH'}
etradie-engine  | 2026-04-15T17:20:10.373765Z [DEBUG    ] snd_candidate_created          [engine.ta.storage.repositories.candidate] extra={'symbol': 'US30X10M', 'pattern': 'SND_CONTINUATION', 'direction': 'BULLISH'}
etradie-engine  | 2026-04-15T17:20:10.380158Z [DEBUG    ] snd_candidate_created          [engine.ta.storage.repositories.candidate] extra={'symbol': 'US30X10M', 'pattern': 'FAKEOUT_KING', 'direction': 'BULLISH'}
etradie-engine  | 2026-04-15T17:20:10.384231Z [DEBUG    ] snd_candidate_created          [engine.ta.storage.repositories.candidate] extra={'symbol': 'US30X10M', 'pattern': 'SND_CONTINUATION', 'direction': 'BULLISH'}
etradie-engine  | 2026-04-15T17:20:10.387185Z [DEBUG    ] snd_candidate_duplicate_skipped [engine.ta.storage.repositories.candidate] extra={'symbol': 'US30X10M', 'pattern': 'SOP', 'entry_price': 48598.7}
etradie-engine  | 2026-04-15T17:20:10.387509Z [ERROR    ] snd_candidate_persistence_failed [engine.ta.orchestrator] extra={'symbol': 'US30X10M', 'pattern': 'SOP', 'error': 'This result object is closed.'}
etradie-engine  | Traceback (most recent call last):
etradie-engine  |   File "/app/src/engine/ta/orchestrator.py", line 1065, in _persist_all_results
etradie-engine  |     await uow.candidate_repo.create_snd_candidate(
etradie-engine  |   File "/app/src/engine/ta/storage/repositories/candidate.py", line 152, in create_snd_candidate
etradie-engine  |     return existing.scalar_one_or_none()
etradie-engine  |            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 1485, in scalar_one_or_none
etradie-engine  |     return self._only_one_row(
etradie-engine  |            ^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 749, in _only_one_row
etradie-engine  |     row: Optional[_InterimRowType[Any]] = onerow(hard_close=True)
etradie-engine  |                                           ^^^^^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 2255, in _fetchone_impl
etradie-engine  |     self._raise_hard_closed()
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 2241, in _raise_hard_closed
etradie-engine  |     raise exc.ResourceClosedError("This result object is closed.")
etradie-engine  | sqlalchemy.exc.ResourceClosedError: This result object is closed.
etradie-engine  | 2026-04-15T17:20:10.394330Z [DEBUG    ] snd_candidate_created          [engine.ta.storage.repositories.candidate] extra={'symbol': 'US30X10M', 'pattern': 'FAKEOUT_KING', 'direction': 'BULLISH'}
etradie-engine  | 2026-04-15T17:20:10.397147Z [DEBUG    ] snd_candidate_duplicate_skipped [engine.ta.storage.repositories.candidate] extra={'symbol': 'US30X10M', 'pattern': 'SOP', 'entry_price': 48596.6}
etradie-engine  | 2026-04-15T17:20:10.397538Z [ERROR    ] snd_candidate_persistence_failed [engine.ta.orchestrator] extra={'symbol': 'US30X10M', 'pattern': 'SOP', 'error': 'This result object is closed.'}
etradie-engine  | Traceback (most recent call last):
etradie-engine  |   File "/app/src/engine/ta/orchestrator.py", line 1065, in _persist_all_results
etradie-engine  |     await uow.candidate_repo.create_snd_candidate(
etradie-engine  |   File "/app/src/engine/ta/storage/repositories/candidate.py", line 152, in create_snd_candidate
etradie-engine  |     return existing.scalar_one_or_none()
etradie-engine  |            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 1485, in scalar_one_or_none
etradie-engine  |     return self._only_one_row(
etradie-engine  |            ^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 749, in _only_one_row
etradie-engine  |     row: Optional[_InterimRowType[Any]] = onerow(hard_close=True)
etradie-engine  |                                           ^^^^^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 2255, in _fetchone_impl
etradie-engine  |     self._raise_hard_closed()
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 2241, in _raise_hard_closed
etradie-engine  |     raise exc.ResourceClosedError("This result object is closed.")
etradie-engine  | sqlalchemy.exc.ResourceClosedError: This result object is closed.
etradie-engine  | 2026-04-15T17:20:10.401648Z [DEBUG    ] snd_candidate_duplicate_skipped [engine.ta.storage.repositories.candidate] extra={'symbol': 'US30X10M', 'pattern': 'SOP', 'entry_price': 48595.6}
etradie-engine  | 2026-04-15T17:20:10.401964Z [ERROR    ] snd_candidate_persistence_failed [engine.ta.orchestrator] extra={'symbol': 'US30X10M', 'pattern': 'SOP', 'error': 'This result object is closed.'}
etradie-engine  | Traceback (most recent call last):
etradie-engine  |   File "/app/src/engine/ta/orchestrator.py", line 1065, in _persist_all_results
etradie-engine  |     await uow.candidate_repo.create_snd_candidate(
etradie-engine  |   File "/app/src/engine/ta/storage/repositories/candidate.py", line 152, in create_snd_candidate
etradie-engine  |     return existing.scalar_one_or_none()
etradie-engine  |            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 1485, in scalar_one_or_none
etradie-engine  |     return self._only_one_row(
etradie-engine  |            ^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 749, in _only_one_row
etradie-engine  |     row: Optional[_InterimRowType[Any]] = onerow(hard_close=True)
etradie-engine  |                                           ^^^^^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 2255, in _fetchone_impl
etradie-engine  |     self._raise_hard_closed()
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 2241, in _raise_hard_closed
etradie-engine  |     raise exc.ResourceClosedError("This result object is closed.")
etradie-engine  | sqlalchemy.exc.ResourceClosedError: This result object is closed.
etradie-engine  | 2026-04-15T17:20:10.409253Z [DEBUG    ] snd_candidate_created          [engine.ta.storage.repositories.candidate] extra={'symbol': 'US30X10M', 'pattern': 'SND_CONTINUATION', 'direction': 'BULLISH'}
etradie-engine  | 2026-04-15T17:20:10.413435Z [DEBUG    ] snd_candidate_duplicate_skipped [engine.ta.storage.repositories.candidate] extra={'symbol': 'US30X10M', 'pattern': 'SOP', 'entry_price': 48595.5}
etradie-engine  | 2026-04-15T17:20:10.414171Z [ERROR    ] snd_candidate_persistence_failed [engine.ta.orchestrator] extra={'symbol': 'US30X10M', 'pattern': 'SOP', 'error': 'This result object is closed.'}
etradie-engine  | Traceback (most recent call last):
etradie-engine  |   File "/app/src/engine/ta/orchestrator.py", line 1065, in _persist_all_results
etradie-engine  |     await uow.candidate_repo.create_snd_candidate(
etradie-engine  |   File "/app/src/engine/ta/storage/repositories/candidate.py", line 152, in create_snd_candidate
etradie-engine  |     return existing.scalar_one_or_none()
etradie-engine  |            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 1485, in scalar_one_or_none
etradie-engine  |     return self._only_one_row(
etradie-engine  |            ^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 749, in _only_one_row
etradie-engine  |     row: Optional[_InterimRowType[Any]] = onerow(hard_close=True)
etradie-engine  |                                           ^^^^^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 2255, in _fetchone_impl
etradie-engine  |     self._raise_hard_closed()
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 2241, in _raise_hard_closed
etradie-engine  |     raise exc.ResourceClosedError("This result object is closed.")
etradie-engine  | sqlalchemy.exc.ResourceClosedError: This result object is closed.
etradie-engine  | 2026-04-15T17:20:10.425223Z [DEBUG    ] snd_candidate_created          [engine.ta.storage.repositories.candidate] extra={'symbol': 'US30X10M', 'pattern': 'SND_CONTINUATION', 'direction': 'BULLISH'}
etradie-engine  | 2026-04-15T17:20:10.430129Z [DEBUG    ] snd_candidate_created          [engine.ta.storage.repositories.candidate] extra={'symbol': 'US30X10M', 'pattern': 'FAKEOUT_KING', 'direction': 'BULLISH'}
etradie-engine  | 2026-04-15T17:20:10.434793Z [DEBUG    ] snd_candidate_created          [engine.ta.storage.repositories.candidate] extra={'symbol': 'US30X10M', 'pattern': 'SND_CONTINUATION', 'direction': 'BULLISH'}
etradie-engine  | 2026-04-15T17:20:10.440784Z [DEBUG    ] snd_candidate_created          [engine.ta.storage.repositories.candidate] extra={'symbol': 'US30X10M', 'pattern': 'FAKEOUT_KING', 'direction': 'BULLISH'}
etradie-engine  | 2026-04-15T17:20:10.444086Z [DEBUG    ] snd_candidate_duplicate_skipped [engine.ta.storage.repositories.candidate] extra={'symbol': 'US30X10M', 'pattern': 'SOP', 'entry_price': 48602.7}
etradie-engine  | 2026-04-15T17:20:10.444409Z [ERROR    ] snd_candidate_persistence_failed [engine.ta.orchestrator] extra={'symbol': 'US30X10M', 'pattern': 'SOP', 'error': 'This result object is closed.'}
etradie-engine  | Traceback (most recent call last):
etradie-engine  |   File "/app/src/engine/ta/orchestrator.py", line 1065, in _persist_all_results
etradie-engine  |     await uow.candidate_repo.create_snd_candidate(
etradie-engine  |   File "/app/src/engine/ta/storage/repositories/candidate.py", line 152, in create_snd_candidate
etradie-engine  |     return existing.scalar_one_or_none()
etradie-engine  |            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 1485, in scalar_one_or_none
etradie-engine  |     return self._only_one_row(
etradie-engine  |            ^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 749, in _only_one_row
etradie-engine  |     row: Optional[_InterimRowType[Any]] = onerow(hard_close=True)
etradie-engine  |                                           ^^^^^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 2255, in _fetchone_impl
etradie-engine  |     self._raise_hard_closed()
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 2241, in _raise_hard_closed
etradie-engine  |     raise exc.ResourceClosedError("This result object is closed.")
etradie-engine  | sqlalchemy.exc.ResourceClosedError: This result object is closed.
etradie-engine  | 2026-04-15T17:20:10.449647Z [DEBUG    ] snd_candidate_created          [engine.ta.storage.repositories.candidate] extra={'symbol': 'US30X10M', 'pattern': 'SND_CONTINUATION', 'direction': 'BULLISH'}
etradie-engine  | 2026-04-15T17:20:10.452205Z [DEBUG    ] snd_candidate_duplicate_skipped [engine.ta.storage.repositories.candidate] extra={'symbol': 'US30X10M', 'pattern': 'SOP', 'entry_price': 48602.5}
etradie-engine  | 2026-04-15T17:20:10.455050Z [ERROR    ] snd_candidate_persistence_failed [engine.ta.orchestrator] extra={'symbol': 'US30X10M', 'pattern': 'SOP', 'error': 'This result object is closed.'}
etradie-engine  | Traceback (most recent call last):
etradie-engine  |   File "/app/src/engine/ta/orchestrator.py", line 1065, in _persist_all_results
etradie-engine  |     await uow.candidate_repo.create_snd_candidate(
etradie-engine  |   File "/app/src/engine/ta/storage/repositories/candidate.py", line 152, in create_snd_candidate
etradie-engine  |     return existing.scalar_one_or_none()
etradie-engine  |            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 1485, in scalar_one_or_none
etradie-engine  |     return self._only_one_row(
etradie-engine  |            ^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 749, in _only_one_row
etradie-engine  |     row: Optional[_InterimRowType[Any]] = onerow(hard_close=True)
etradie-engine  |                                           ^^^^^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 2255, in _fetchone_impl
etradie-engine  |     self._raise_hard_closed()
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 2241, in _raise_hard_closed
etradie-engine  |     raise exc.ResourceClosedError("This result object is closed.")
etradie-engine  | sqlalchemy.exc.ResourceClosedError: This result object is closed.
etradie-engine  | 2026-04-15T17:20:10.461918Z [DEBUG    ] snd_candidate_creat
etradie-engine  | 2026-04-15T17:20:10.558632Z [DEBUG    ] snd_candidate_created          [engine.ta.storage.repositories.candidate] extra={'symbol': 'US30X10M', 'pattern': 'SOP', 'direction': 'BULLISH'}
etradie-engine  | 2026-04-15T17:20:10.565435Z [DEBUG    ] snd_candidate_created          [engine.ta.storage.repositories.candidate] extra={'symbol': 'US30X10M', 'pattern': 'SOP', 'direction': 'BULLISH'}
etradie-engine  | 2026-04-15T17:20:10.570138Z [DEBUG    ] snd_candidate_created          [engine.ta.storage.repositories.candidate] extra={'symbol': 'US30X10M', 'pattern': 'SOP', 'direction': 'BULLISH'}
etradie-engine  | 2026-04-15T17:20:10.576052Z [DEBUG    ] snd_candidate_created          [engine.ta.storage.repositories.candidate] extra={'symbol': 'US30X10M', 'pattern': 'SOP', 'direction': 'BULLISH'}
etradie-engine  | 2026-04-15T17:20:10.582030Z [DEBUG    ] snd_candidate_created          [engine.ta.storage.repositories.candidate] extra={'symbol': 'US30X10M', 'pattern': 'SND_CONTINUATION', 'direction': 'BULLISH'}
etradie-engine  | 2026-04-15T17:20:10.586050Z [DEBUG    ] snd_candidate_created          [engine.ta.storage.repositories.candidate] extra={'symbol': 'US30X10M', 'pattern': 'FAKEOUT_KING', 'direction': 'BULLISH'}
etradie-engine  | 2026-04-15T17:20:10.592906Z [DEBUG    ] snd_candidate_created          [engine.ta.storage.repositories.candidate] extra={'symbol': 'US30X10M', 'pattern': 'SND_CONTINUATION', 'direction': 'BULLISH'}
etradie-engine  | 2026-04-15T17:20:10.598203Z [DEBUG    ] snd_candidate_created          [engine.ta.storage.repositories.candidate] extra={'symbol': 'US30X10M', 'pattern': 'SOP', 'direction': 'BULLISH'}
etradie-engine  | 2026-04-15T17:20:10.603065Z [DEBUG    ] snd_candidate_created          [engine.ta.storage.repositories.candidate] extra={'symbol': 'US30X10M', 'pattern': 'SND_CONTINUATION', 'direction': 'BULLISH'}
etradie-engine  | 2026-04-15T17:20:10.608906Z [DEBUG    ] snd_candidate_created          [engine.ta.storage.repositories.candidate] extra={'symbol': 'US30X10M', 'pattern': 'FAKEOUT_KING', 'direction': 'BULLISH'}
etradie-engine  | 2026-04-15T17:20:10.613478Z [DEBUG    ] snd_candidate_created          [engine.ta.storage.repositories.candidate] extra={'symbol': 'US30X10M', 'pattern': 'SND_CONTINUATION', 'direction': 'BULLISH'}
etradie-engine  | 2026-04-15T17:20:10.617471Z [DEBUG    ] snd_candidate_created          [engine.ta.storage.repositories.candidate] extra={'symbol': 'US30X10M', 'pattern': 'SOP', 'direction': 'BULLISH'}
etradie-engine  | 2026-04-15T17:20:10.620143Z [DEBUG    ] snd_candidate_duplicate_skipped [engine.ta.storage.repositories.candidate] extra={'symbol': 'US30X10M', 'pattern': 'QMH_BASELINE', 'entry_price': 47679.4}
etradie-engine  | 2026-04-15T17:20:10.620551Z [ERROR    ] snd_candidate_persistence_failed [engine.ta.orchestrator] extra={'symbol': 'US30X10M', 'pattern': 'QMH_BASELINE', 'error': 'This result object is closed.'}
etradie-engine  | Traceback (most recent call last):
etradie-engine  |   File "/app/src/engine/ta/orchestrator.py", line 1065, in _persist_all_results
etradie-engine  |     await uow.candidate_repo.create_snd_candidate(
etradie-engine  |   File "/app/src/engine/ta/storage/repositories/candidate.py", line 152, in create_snd_candidate
etradie-engine  |     return existing.scalar_one_or_none()
etradie-engine  |            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 1485, in scalar_one_or_none
etradie-engine  |     return self._only_one_row(
etradie-engine  |            ^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 749, in _only_one_row
etradie-engine  |     row: Optional[_InterimRowType[Any]] = onerow(hard_close=True)
etradie-engine  |                                           ^^^^^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 2255, in _fetchone_impl
etradie-engine  |     self._raise_hard_closed()
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 2241, in _raise_hard_closed
etradie-engine  |     raise exc.ResourceClosedError("This result object is closed.")
etradie-engine  | sqlalchemy.exc.ResourceClosedError: This result object is closed.
etradie-engine  | 2026-04-15T17:20:10.627079Z [DEBUG    ] snd_candidate_duplicate_skipped [engine.ta.storage.repositories.candidate] extra={'symbol': 'US30X10M', 'pattern': 'QMH_BASELINE', 'entry_price': 47687.0}
etradie-engine  | 2026-04-15T17:20:10.627456Z [ERROR    ] snd_candidate_persistence_failed [engine.ta.orchestrator] extra={'symbol': 'US30X10M', 'pattern': 'QMH_BASELINE', 'error': 'This result object is closed.'}
etradie-engine  | Traceback (most recent call last):
etradie-engine  |   File "/app/src/engine/ta/orchestrator.py", line 1065, in _persist_all_results
etradie-engine  |     await uow.candidate_repo.create_snd_candidate(
etradie-engine  |   File "/app/src/engine/ta/storage/repositories/candidate.py", line 152, in create_snd_candidate
etradie-engine  |     return existing.scalar_one_or_none()
etradie-engine  |            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 1485, in scalar_one_or_none
etradie-engine  |     return self._only_one_row(
etradie-engine  |            ^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 749, in _only_one_row
etradie-engine  |     row: Optional[_InterimRowType[Any]] = onerow(hard_close=True)
etradie-engine  |                                           ^^^^^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 2255, in _fetchone_impl
etradie-engine  |     self._raise_hard_closed()
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 2241, in _raise_hard_closed
etradie-engine  |     raise exc.ResourceClosedError("This result object is closed.")
etradie-engine  | sqlalchemy.exc.ResourceClosedError: This result object is closed.
etradie-engine  | 2026-04-15T17:20:10.632405Z [DEBUG    ] snd_candidate_duplicate_skipped [engine.ta.storage.repositories.candidate] extra={'symbol': 'US30X10M', 'pattern': 'QMH_BASELINE', 'entry_price': 48256.3}
etradie-engine  | 2026-04-15T17:20:10.632905Z [ERROR    ] snd_candidate_persistence_failed [engine.ta.orchestrator] extra={'symbol': 'US30X10M', 'pattern': 'QMH_BASELINE', 'error': 'This result object is closed.'}
etradie-engine  | Traceback (most recent call last):
etradie-engine  |   File "/app/src/engine/ta/orchestrator.py", line 1065, in _persist_all_results
etradie-engine  |     await uow.candidate_repo.create_snd_candidate(
etradie-engine  |   File "/app/src/engine/ta/storage/repositories/candidate.py", line 152, in create_snd_candidate
etradie-engine  |     return existing.scalar_one_or_none()
etradie-engine  |            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 1485, in scalar_one_or_none
etradie-engine  |     return self._only_one_row(
etradie-engine  |            ^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 749, in _only_one_row
etradie-engine  |     row: Optional[_InterimRowType[Any]] = onerow(hard_close=True)
etradie-engine  |                                           ^^^^^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 2255, in _fetchone_impl
etradie-engine  |     self._raise_hard_closed()
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 2241, in _raise_hard_closed
etradie-engine  |     raise exc.ResourceClosedError("This result object is closed.")
etradie-engine  | sqlalchemy.exc.ResourceClosedError: This result object is closed.
etradie-engine  | 2026-04-15T17:20:10.638439Z [DEBUG    ] snd_candidate_duplicate_skipped [engine.ta.storage.repositories.candidate] extra={'symbol': 'US30X10M', 'pattern': 'QMH_KILLER_TYPE2', 'entry_price': 48256.3}
etradie-engine  | 2026-04-15T17:20:10.639357Z [ERROR    ] snd_candidate_persistence_failed [engine.ta.orchestrator] extra={'symbol': 'US30X10M', 'pattern': 'QMH_KILLER_TYPE2', 'error': 'This result object is closed.'}
etradie-engine  | Traceback (most recent call last):
etradie-engine  |   File "/app/src/engine/ta/orchestrator.py", line 1065, in _persist_all_results
etradie-engine  |     await uow.candidate_repo.create_snd_candidate(
etradie-engine  |   File "/app/src/engine/ta/storage/repositories/candidate.py", line 152, in create_snd_candidate
etradie-engine  |     return existing.scalar_one_or_none()
etradie-engine  |            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 1485, in scalar_one_or_none
etradie-engine  |     return self._only_one_row(
etradie-engine  |            ^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 749, in _only_one_row
etradie-engine  |     row: Optional[_InterimRowType[Any]] = onerow(hard_close=True)
etradie-engine  |                                           ^^^^^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 2255, in _fetchone_impl
etradie-engine  |     self._raise_hard_closed()
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 2241, in _raise_hard_closed
etradie-engine  |     raise exc.ResourceClosedError("This result object is closed.")
etradie-engine  | sqlalchemy.exc.ResourceClosedError: This result object is closed.
etradie-engine  | 2026-04-15T17:20:10.643214Z [DEBUG    ] snd_candidate_duplicate_skipped [engine.ta.storage.repositories.candidate] extra={'symbol': 'US30X10M', 'pattern': 'QMH_BASELINE', 'entry_price': 48297.3}
etradie-engine  | 2026-04-15T17:20:10.643667Z [ERROR    ] snd_candidate_persistence_failed [engine.ta.orchestrator] extra={'symbol': 'US30X10M', 'pattern': 'QMH_BASELINE', 'error': 'This result object is closed.'}
etradie-engine  | Traceback (most recent call last):
etradie-engine  |   File "/app/src/engine/ta/orchestrator.py", line 1065, in _persist_all_results
etradie-engine  |     await uow.candidate_repo.create_snd_candidate(
etradie-engine  |   File "/app/src/engine/ta/storage/repositories/candidate.py", line 152, in create_snd_candidate
etradie-engine  |     return existing.scalar_one_or_none()
etradie-engine  |            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 1485, in scalar_one_or_none
etradie-engine  |     return self._only_one_row(
etradie-engine  |            ^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 749, in _only_one_row
etradie-engine  |     row: Optional[_InterimRowType[Any]] = onerow(hard_close=True)
etradie-engine  |                                           ^^^^^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 2255, in _fetchone_impl
etradie-engine  |     self._raise_hard_closed()
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 2241, in _raise_hard_closed
etradie-engine  |     raise exc.ResourceClosedError("This result object is closed.")
etradie-engine  | sqlalchemy.exc.ResourceClosedError: This result object is closed.
etradie-engine  | 2026-04-15T17:20:10.649283Z [DEBUG    ] snd_candidate_duplicate_skipped [engine.ta.storage.repositories.candidate] extra={'symbol': 'US30X10M', 'pattern': 'QMH_BASELINE', 'entry_price': 48261.0}
etradie-engine  | 2026-04-15T17:20:10.649664Z [ERROR    ] snd_candidate_persistence_failed [engine.ta.orchestrator] extra={'symbol': 'US30X10M', 'pattern': 'QMH_BASELINE', 'error': 'This result object is closed.'}
etradie-engine  | Traceback (most recent call last):
etradie-engine  |   File "/app/src/engine/ta/orchestrator.py", line 1065, in _persist_all_results
etradie-engine  |     await uow.candidate_repo.create_snd_candidate(
etradie-engine  |   File "/app/src/engine/ta/storage/repositories/candidate.py", line 152, in create_snd_candidate
etradie-engine  |     return existing.scalar_one_or_none()
etradie-engine  |            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 1485, in scalar_one_or_none
etradie-engine  |     return self._only_one_row(
etradie-engine  |            ^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 749, in _only_one_row
etradie-engine  |     row: Optional[_InterimRowType[Any]] = onerow(hard_close=True)
etradie-engine  |                                           ^^^^^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 2255, in _fetchone_impl
etradie-engine  |     self._raise_hard_closed()
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 2241, in _raise_hard_closed
etradie-engine  |     raise exc.ResourceClosedError("This result object is closed.")
etradie-engine  | sqlalchemy.exc.ResourceClosedError: This result object is closed.
etradie-engine  | 2026-04-15T17:20:10.657050Z [DEBUG    ] snd_candidate_duplicate_skipped [engine.ta.storage.repositories.candidate] extra={'symbol': 'US30X10M', 'pattern': 'QMH_BASELINE', 'entry_price': 48489.3}
etradie-engine  | 2026-04-15T17:20:10.657385Z [ERROR    ] snd_candidate_persistence_failed [engine.ta.orchestrator] extra={'symbol': 'US30X10M', 'pattern': 'QMH_BASELINE', 'error': 'This result object is closed.'}
etradie-engine  | Traceback (most recent call last):
etradie-engine  |   File "/app/src/engine/ta/orchestrator.py", line 1065, in _persist_all_results
etradie-engine  |     await uow.candidate_repo.create_snd_candidate(
etradie-engine  |   File "/app/src/engine/ta/storage/repositories/candidate.py", line 152, in create_snd_candidate
etradie-engine  |     return existing.scalar_one_or_none()
etradie-engine  |            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 1485, in scalar_one_or_none
etradie-engine  |     return self._only_one_row(
etradie-engine  |            ^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 749, in _only_one_row
etradie-engine  |     row: Optional[_InterimRowType[Any]] = onerow(hard_close=True)
etradie-engine  |                                           ^^^^^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 2255, in _fetchone_impl
etradie-engine  |     self._raise_hard_closed()
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 2241, in _raise_hard_closed
etradie-engine  |     raise exc.ResourceClosedError("This result object is closed.")
etradie-engine  | sqlalchemy.exc.ResourceClosedError: This result object is closed.
etradie-engine  | 2026-04-15T17:20:10.665679Z [DEBUG    ] snd_candidate_created          [engine.ta.storage.repositories.candidate] extra={'symbol': 'US30X10M', 'pattern': 'QMH_BASELINE', 'direction': 'BULLISH'}
etradie-engine  | 2026-04-15T17:20:10.673839Z [DEBUG    ] snd_candidate_created          [engine.ta.storage.repositories.candidate] extra={'symbol': 'US30X10M', 'pattern': 'QMH_BASELINE', 'direction': 'BULLISH'}
etradie-engine  | 2026-04-15T17:20:10.683954Z [DEBUG    ] snd_candidate_created          [engine.ta.storage.repositories.candidate] extra={'symbol': 'US30X10M', 'pattern': 'QMH_BASELINE', 'direction': 'BULLISH'}
etradie-engine  | 2026-04-15T17:20:10.688348Z [DEBUG    ] snd_candidate_duplicate_skipped [engine.ta.storage.repositories.candidate] extra={'symbol': 'US30X10M', 'pattern': 'QML_BASELINE', 'entry_price': 48070.4}
etradie-engine  | 2026-04-15T17:20:10.688740Z [ERROR    ] snd_candidate_persistence_failed [engine.ta.orchestrator] extra={'symbol': 'US30X10M', 'pattern': 'QML_BASELINE', 'error': 'This result object is closed.'}
etradie-engine  | Traceback (most recent call last):
etradie-engine  |   File "/app/src/engine/ta/orchestrator.py", line 1065, in _persist_all_results
etradie-engine  |     await uow.candidate_repo.create_snd_candidate(
etradie-engine  |   File "/app/src/engine/ta/storage/repositories/candidate.py", line 152, in create_snd_candidate
etradie-engine  |     return existing.scalar_one_or_none()
etradie-engine  |            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 1485, in scalar_one_or_none
etradie-engine  |     return self._only_one_row(
etradie-engine  |            ^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 749, in _only_one_row
etradie-engine  |     row: Optional[_InterimRowType[Any]] = onerow(hard_close=True)
etradie-engine  |                                           ^^^^^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 2255, in _fetchone_impl
etradie-engine  |     self._raise_hard_closed()
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 2241, in _raise_hard_closed
etradie-engine  |     raise exc.ResourceClosedError("This result object is closed.")
etradie-engine  | sqlalchemy.exc.ResourceClosedError: This result object is closed.
etradie-engine  | 2026-04-15T17:20:10.694095Z [DEBUG    ] snd_candidate_duplicate_skipped [engine.ta.storage.repositories.candidate] extra={'symbol': 'US30X10M', 'pattern': 'QMH_BASELINE', 'entry_price': 47709.0}
etradie-engine  | 2026-04-15T17:20:10.694488Z [ERROR    ] snd_candidate_persistence_failed [engine.ta.orchestrator] extra={'symbol': 'US30X10M', 'pattern': 'QMH_BASELINE', 'error': 'This result object is closed.'}
etradie-engine  | Traceback (most recent call last):
etradie-engine  |   File "/app/src/engine/ta/orchestrator.py", line 1065, in _persist_all_results
etradie-engine  |     await uow.candidate_repo.create_snd_candidate(
etradie-engine  |   File "/app/src/engine/ta/storage/repositories/candidate.py", line 152, in create_snd_candidate
etradie-engine  |     return existing.scalar_one_or_none()
etradie-engine  |            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 1485, in scalar_one_or_none
etradie-engine  |     return self._only_one_row(
etradie-engine  |            ^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 749, in _only_one_row
etradie-engine  |     row: Optional[_InterimRowType[Any]] = onerow(hard_close=True)
etradie-engine  |                                           ^^^^^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 2255, in _fetchone_impl
etradie-engine  |     self._raise_hard_closed()
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/engine/result.py", line 2241, in _raise_hard_closed
etradie-engine  |     raise exc.ResourceClosedError("This result object is closed.")
etradie-engine  | sqlalchemy.exc.ResourceClosedError: This result object is closed.
etradie-engine  | 2026-04-15T17:20:10.701467Z [DEBUG    ] db_transaction_committed       [engine.shared.db.connection] extra={'trace_id': None, 'duration_ms': 2929.0}
etradie-engine  | 2026-04-15T17:20:10.702101Z [DEBUG    ] persistence_completed          [engine.ta.orchestrator] extra={'snapshots_persisted': 8, 'smc_candidates_persisted': 233, 'snd_candidates_persisted': 241}
etradie-engine  | 2026-04-15T17:20:10.702688Z [INFO     ] ta_mtf_analysis_completed      [engine.ta.orchestrator] extra={'symbol': 'US30_x10m', 'timeframes_analyzed': ['W1', 'D1', 'H4', 'H1', 'M30', 'M15', 'M5', 'M1'], 'snapshots_built': 8, 'smc_candidates': 233, 'snd_candidates': 241, 'alignments': 7, 'overall_trend': 'BEARISH'}
etradie-engine  | 2026-04-15T17:20:10.741179Z [DEBUG    ] cache_miss                     [engine.shared.cache.redis_cache] extra={'namespace': 'cot', 'key': 'latest', 'trace_id': None}