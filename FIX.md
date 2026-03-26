

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






YOU HAVE FULL AND COMPLETE READ AND WRITE ACCESS TO THE REPO FROM MY OTHER ACCOUNT BECAUSE I HAVE ADDED YOU AS A GROUP MEMEBER WITH A DEVELOPER ROLE:

https://gitlab.com/exoper-chi/exoper-izi

SO IT MEANS YOU CAN EXAMINE FILES, MODIFY, CREATE AND IMPLEMENT, COMMIT AND CREATE MERGE REQUEST ETC

CRITICAL: EVERYTHING IS ON THE MAIN BRANCH. DO NOT FOOLSIHLY START LISTING WHAT IS ON THE MASTER BRANCH



THIS IS EXACTLY WHAT WE WANT TO DO AND I WANT YOU TO EXAMINE IT THOROUGHLY IN THE ORDER I GAVE IT NOW FROM THE BEGINNING TO THE END:



CURRENTLY METAAPI IS USING ENVIRONMENT VARIABLE I THINK AND EA CONFIGURED LOCALLY

SO WE ARE GOING TO MODIFY AND UPDATE EVERYTHING:

1. Users goes to the dashboard and clicks connect broker
2. They select EA or metaapi from dashboard.  twelve-data IS FOR FALLBACK FOR EITHER OF THAT IN CASE
3. If they select EA then A MODAL/PAGE WILL APPEAR FOR THEM TO SETUP THEIR MT5 ACCOUNT
4. But IF THEY SELECT METAAPI THEN A MODAL/PAGE APPEAR: THEY WILL HAVE TO ALSO SETUP THEIR MT5 ACCOUNTS

ONCE THEY SETUP IT WILL BE PERSISTED IN THE DATABASE AND THEY SHOULD ALSO BE ABLE TO activate/deactivate/delete 


SO EXAMINE BOTH OF THESE THOROUGHLY FROM THE BEGINNING TO THE END SO THAT YOU WILL UNDERSTAND WHAT I AM EXPLAING AND WE NEED TO DO.

THIS IS VERY HUG SO WE EXECUTE STEP BY STEP INSTEAD OF RUSHING ANYTHING. OF COURSE THE EA (ZEOMQ) WILL BE DEPLOYED IN SAME VPS AS THE APPLICATION SO BOTH WILL BE DONE TOGETHER


FOR EA,

## **Current Problem & Proposed Solution**

**Current Setup (Local):**

We're currently running MT5 with the ZeroMQ EA on a local Windows PC (IP: 192.168.43.183:5555), which the eTradie application on Linux Docker connects to for market data and trade execution. This setup has critical limitations: MT5 only runs when the Windows PC is powered on, requiring the PC to stay running 24/7 for continuous operation. This creates dependency on local hardware, increases electricity costs, ties the system to a single location, and makes the system unavailable during PC shutdowns, restarts, or power outages.

**Proposed Solution (Cloud VPS):**

Migrate MT5 and the ZeroMQ EA to a Windows VPS (Virtual Private Server) running 24/7 in a data center. The eTradie application will connect to the VPS public IP instead of the local PC IP. This provides true 24/7 uptime independent of local hardware, eliminates electricity costs and PC wear, enables access from anywhere with internet, ensures better reliability with data center infrastructure, and reduces overall operational costs to $10-30/month. **We will keep the current local Windows PC setup exactly as it is for backup and redundancy, allowing us to switch back to local operation if needed.** The transition only requires: (1) deploying a Windows VPS, (2) installing MT5 and the EA on the VPS, (3) updating the `MT5_ZMQ_HOST` environment variable in eTradie to the VPS IP, and (4) restarting the Docker containers. All functionality remains identical with improved reliability and availability.



SOWE ARE HANDLING BOTH EA AND METAAPI



## **Broker Connection Management - Current vs New Approach**

**Current Setup (Hardcoded Environment Variables):**

The system currently uses hardcoded MetaAPI credentials stored in `.env` files, supporting only a single MT5 account for all users. This approach doesn't scale for multi-user scenarios and provides no flexibility for users to configure their own broker connections. Users cannot choose their preferred connection method or manage multiple MT5 accounts.

**Proposed Solution (Database-Driven Multi-User Connections):**

Implement a database-driven broker connection system where each user can configure their own MT5 accounts via the dashboard. Users will select between two connection methods: EA (ZeroMQ) for direct MT5 connection via their own MT5 instance, or MetaAPI for cloud-provisioned MT5 accounts. Twelve-data will serve as a fallback data provider if primary connections fail. Users will be able to create, activate, deactivate, and delete their broker connections through the dashboard, with all credentials securely stored in the database per user. This requires: (1) creating a `broker_connections` database table, (2) implementing CRUD API endpoints for connection management, (3) building dashboard UI for connection configuration (modals for EA and MetaAPI setup), (4) adding credential encryption, and (5) updating the trading engine to fetch connections from the database instead of environment variables. This enables true multi-user support with flexible broker connection options.

---


THIS IS JUST AND EXAMPLE:

# Broker Connection Management

POST   /api/v1/broker/connections
# Create new broker connection (EA or MetaAPI)
# Body: { type: 'ea'|'metaapi', name, credentials }

GET    /api/v1/broker/connections
# List all user's broker connections

GET    /api/v1/broker/connections/{id}
# Get specific connection details

PATCH  /api/v1/broker/connections/{id}
# Update connection (activate/deactivate)
# Body: { is_active: true|false }

DELETE /api/v1/broker/connections/{id}
# Delete broker connection

POST   /api/v1/broker/connections/{id}/test
# Test connection status

POST   /api/v1/broker/connections/{id}/set-primary
# Set as primary connection

# MetaAPI-specific
POST   /api/v1/broker/metaapi/provision
# Provision new MetaAPI account
# Body: { login, password, server }

# EA-specific
POST   /api/v1/broker/ea/test-connection
# Test EA ZeroMQ connection
# Body: { host, port, auth_token }

