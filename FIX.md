

#### Problem

The `app_client` fixture boots the full FastAPI app (including loading the 250MB sentence_transformers model at ~22s per load) once per test function. 28 API integration tests = 28 app boots = ~10 minutes of wasted model loading.

#### Optimization

Upgrade `pytest-asyncio` from `0.25.3` to `0.26+` which supports `loop_scope="session"` directly on the fixture decorator:

```python
@pytest_asyncio.fixture(loop_scope="session", scope="session")
async def app_client() -> AsyncGenerator[AsyncClient, None]:
```

Then make `seeded_client` a `yield` fixture that deletes its seed rows after each test to prevent data leaks across the shared app instance.

No changes to `pyproject.toml` needed. No manual `event_loop` fixture needed. The newer `pytest-asyncio` handles it cleanly.