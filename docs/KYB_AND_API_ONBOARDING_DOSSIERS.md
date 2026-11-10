# DOMINUS Stage G — First-Principles Venue Authorization, KYB & Read-Only API Onboarding Dossiers

This document records verified first-principles legal and technical distinctions across all six Stage G venues—strictly separating **public read-only market data**, **authenticated read-only APIs**, **account operations**, **order placement / real-money trading**, **corporate entity/KYB eligibility**, and **server/IP hosting**.

---

## 1. First-Principles Permission Separation Matrix

| Venue | Governing Terms / Regulator | Public Data (`REST` / `WS`) | Read-Only API | Account Authorization | Trading Eligibility | Server Hosting (`FI` vs `CA-ON`) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Polymarket International** | Adventure One QSS Inc. ToS, Geographic Restrictions (`docs.polymarket.com`) & Apr 2025 OSC Settlement | **`PUBLIC_DATA_AUTHORIZED`** (`gamma-api.polymarket.com`, `clob.polymarket.com/book`, `ws-subscriptions-clob.polymarket.com/ws/market` require `0` auth and `0` geoblock) | **`PUBLIC_DATA_AUTHORIZED`** (keyless public L2 REST/WS) | **`RESTRICTED`** in `CA-ON` (unless independently eligible non-restricted entity holds written `DOMINUS_KYB_REFERENCE_ID`) | **`RESTRICTED`** in `CA-ON` (`POST /order` geoblocked; retail KYB does NOT override `CA-ON`) | Keyless public market-data permitted on `FI` & `CA-ON`; `POST /order` prohibited from `CA-ON` or via proxy |
| **Predict.fun** | PDF Labs Limited Terms of Service Section 1 (`docs.predict.fun/terms-of-service`, Nov 18, 2025) | **`CREDENTIALS_REQUIRED`** on mainnet (`x-api-key` required); **`PUBLIC_DATA_AUTHORIZED`** on BNB Testnet (`api-testnet.predict.fun`, strictly `TESTNET_SANDBOX`) | **`AUTHORIZED_LIVE`** (`Content Features` expressly permitted in Restricted Jurisdictions per Section 1 using `PREDICT_FUN_API_KEY` from `developers.predict.fun`, `0` wallet connection, `0` JWT, `0` trading) | **`RESTRICTED`** under `CA-ON` (`POST /v1/auth` wallet JWT / Technology Features barred) | **`RESTRICTED`** under `CA-ON` (`POST /v1/orders` & BNB Chain Contracts barred) | Mainnet read-only `Content Features` **ACTIVE** on `FI` with `PREDICT_FUN_API_KEY`; `LIVE_TRADING_ACCESS` & `ACCOUNT_PRIVATE` strictly `RESTRICTED` under `CA-ON` |
| **SX Bet** | SX Bet Developer Docs (`docs.sx.bet/developers/authentication.md`, `rate-limits.md`) & SX Bet Terms (`sx.bet` — *"Your Obligations"* wagering rules) | **`PUBLIC_DATA_AUTHORIZED`** (documented OpenAPI `security: []` endpoints `/metadata/obv3`, `/summary-v3/{popular,inplay,upcoming}`, `/markets/active`, `/trades-v3/public`; `500 req/60s` per IP, `0` credentials, `0` wagering) | **`CREDENTIALS_PENDING`** until `SX_BET_API_KEY` (`x-sx-api-key`) is provisioned (`api.sx.bet` enforces `HTTP 401 BAD_AUTH` without key on `/orderbook-v3/snapshot/market`, `/orders-v3/odds/best`, & `/user/realtime-token-v3/api-key` Centrifugo WS) | **`RESTRICTED`** under `CA-ON` (wagering/account creation) | **`RESTRICTED`** under `CA-ON` (`POST /orders-v3` & EIP-712 signing barred) | Keyless public OBv3 REST **ACTIVE** on `FI`; `SX_BET_API_KEY` upgrades to L2 `/orderbook-v3/snapshot/market` + Centrifugo WS |
| **Limitless Exchange** | Street Chow Inc. Terms of Service Section 1 (`limitless.exchange/terms`) | **`PUBLIC_DATA_AUTHORIZED`** (Section 1 classifies `CA-ON`/`CA-AB`/`US` as *"not available for trading"*, distinct from the comprehensive access ban on `RU`/`BY`/`CU`/`IR`/`KP`/`SY`; keyless `GET /markets/active?limit=25`, `GET /markets/{slug}/orderbook`, & Socket.IO `/markets`) | **`PUBLIC_DATA_AUTHORIZED`** (keyless public L2 REST/WS; `0` HMAC secrets) | **`RESTRICTED`** in `CA-ON` | **`RESTRICTED`** in `CA-ON` | Keyless public market-data permitted on `FI` & `CA-ON`; HMAC/account/order placement disabled under `CA-ON` |
| **ForecastEx / IBKR** | CFTC (US DCM/DCO) & CIRO (`Interactive Brokers Canada Inc.`) | **`PUBLIC_DATA_AUTHORIZED`** (`https://forecastex.com/api/download` CFTC DCM `summary`, `prices`, & 10m `pairs` CSVs) | **`CREDENTIALS_REQUIRED`** in `CA-ON` (`IBKR_GATEWAY_URL` local Client Portal Gateway); **`RESTRICTED`** on `FI` for proxying personal `CA-ON` IBKR sessions | **`CREDENTIALS_REQUIRED`** in `CA-ON` (eligible via IBKR Canada `CIRO` `FORECASTX` `OPT` permission) | **`CREDENTIALS_REQUIRED`** in `CA-ON` (Stage G shadow keeps order placement hard-disabled) | Public CFTC transparency CSVs **ACTIVE** on `FI` & `CA-ON`; authenticated IBKR CPAPI runs directly on `CA-ON` workstation |
| **STX Ontario** | AGCO & iGaming Ontario (`on.stxapp.ca` / `apps.stxapp.io`) | **`CREDENTIALS_REQUIRED`** (`STX` exposes zero unauthenticated market endpoints) | **Path A (`CA-ON` direct):** `CREDENTIALS_REQUIRED` until **BOTH** `STX_API_KEY_ID` **AND** `0600` `STX_ED25519_KEY_FILE` are provisioned (`RESTRICTED` from `FI` per iGO geolocation). **Path B (`apps.stxapp.io`):** Institutional server-to-server `Data` track (`STX_APPS_DATA_TOKEN`) | **`CREDENTIALS_REQUIRED`** in `CA-ON`; **`RESTRICTED`** on `FI` (Path A) | **`CREDENTIALS_REQUIRED`** in `CA-ON`; **`RESTRICTED`** on `FI` | Path A runs strictly in `CA-ON`; Path B (`apps.stxapp.io` `Data`) is required for cloud server-to-server ingestion |

---

## 2. Actionable Onboarding & Credential Activation Workflows

### Workflow A — STX Ontario Path A (Personal Read-Only BYOK Ed25519 in `CA-ON`) & Path B (`apps.stxapp.io` Institutional `Data`)
- **Path A — Direct Ontario Personal Read-Only API (`https://api.on.stxapp.ca/api/v1`):**
  1. Generate a local `0600` Ed25519 keypair on your Ontario (`CA-ON`) machine (private key stays on disk, never echoed):
     ```bash
     python scripts/deploy_cross_venue_shadow.py --generate-stx-ed25519-keypair
     ```
  2. Log into `https://on.stxapp.ca` -> **Account Settings -> API Management**, paste ONLY `public_key_pem`, select **`Read-Only`** scope, and copy the issued `Key ID`.
  3. Set **both** `STX_API_KEY_ID` and `STX_ED25519_KEY_FILE` (a bare `Key ID` without the `0600` private signing key cannot produce `X-STX-ACCESS-SIGNATURE` headers and will stay `CREDENTIALS_REQUIRED`):
     ```bash
     python scripts/deploy_cross_venue_shadow.py --provision-secret STX_ED25519_KEY_FILE --local-env-path .env.shadow
     python scripts/deploy_cross_venue_shadow.py --provision-secret STX_API_KEY_ID --local-env-path .env.shadow
     ```
- **Path B — Institutional Server-to-Server `Data` Track (`https://apps.stxapp.io`):**
  - Submit an institutional partner application at `https://apps.stxapp.io` selecting the **`Data`** track (`Server-to-Server Read-Only Orderbook Feed`).
  - Record the pending ticket as `STX_APPS_APPLICATION_ID=<ticket_id>` (`APPROVAL_PENDING`), and once approved, provision `STX_APPS_DATA_TOKEN` via `--provision-secret STX_APPS_DATA_TOKEN`.

### Workflow B — Interactive Brokers Canada (`CIRO`) ForecastEx Streaming CPAPI (`CA-ON` Direct)
- **Official Source:** Interactive Brokers Canada Inc. (`https://www.interactivebrokers.ca`) & IBKR Campus CPAPI (`FORECASTX` `OPT`, `C=Yes` / `P=No`, snapshot fields `84,86,88,85,6509`).
- **Checklist:**
  1. In IBKR Client Portal -> **Settings -> Trading Permissions -> Event Contracts**, enable `FORECASTX`.
  2. Start local IBKR Client Portal Gateway (`https://localhost:5000/v1/api`) on the `CA-ON` host and complete browser 2FA (`GET /iserver/auth/status` -> `authenticated: true`; `ForecastExIBKRConnector` automatically sends `GET /tickle` every `55s`).
  3. Set `IBKR_GATEWAY_URL=https://localhost:5000/v1/api` and `IBKR_ALLOW_LOCALHOST_SELF_SIGNED=1` on the `CA-ON` shadow instance. (Never proxy a personal `CA-ON` IBKR session through `kraken-finland`.)

### Workflow C — SX Bet Read-Only Market-Data & Non-Restricted Entity Onboarding (`Priority C`)
- **Official Sources:** SX Bet Terms (`https://sx.bet` — *"Your Obligations"*) & SX Bet API v3 Docs (`https://api.docs.sx.bet` — REST `/metadata/obv3`, `/markets/active`, `/orders-v3`, `/orders-v3/odds/best`, `/orderbook-v3/snapshot/market`, `/summary-v3`, and Centrifugo `wss://realtime.sx.bet/connection/websocket` via `GET /user/realtime-token-v3/api-key` `<= 30 req/60s`).
- **7-Scope Technical vs Contractual Distinction:**
  - **Eligible Non-Restricted Operator/Entity:** SX Bet imposes **zero** written data-license requirement. `PUBLIC_REST` is immediately `AUTHORIZED_LIVE` (`verified_outcome_state = AUTHORIZED_REST_ONLY` with `0` API keys), and provisioning `SX_BET_API_KEY` unlocks Centrifugo WebSocket (`verified_outcome_state = AUTHORIZED_LIVE`). Any prior internally assumed `SX_BET_WRITTEN_DATA_LICENSE_ID` requirement has been removed for eligible operators.
  - **Attested `CA-ON` Operator:** SX Bet Terms (*"Your Obligations"*) contractually warrant *"You are not a resident of... Ontario, Canada"* across site/service access (`verified_outcome_state = RESTRICTED` unless operated by an independently eligible non-restricted entity or granted written read-only approval `SX_BET_DATA_APPROVAL_ID`).
- **Prepared External Onboarding Application (`support@sx.bet` / Official SX Discord Institutional Support Ticket):**
  > **Subject:** Read-Only Market-Data API & Non-Restricted Entity Onboarding Application (`quant-pipeline-finland` / `FI`)
  >
  > **1. Intended Scope:** Strictly read-only public order-book telemetry and quantitative shadow research (`0` order placement, `0` `/orders/new` or `/orders/fill` calls, `0` wallet signing, `0` fund custody).
  > **2. Target Endpoints & Rate Budget:**
  > - REST (`<= 60 req/min`, well below SX Bet's `500–1,200 req/60s` limits): `GET /metadata/obv3`, `GET /markets/active`, `GET /orders-v3`, `GET /orderbook-v3/snapshot/market`, `GET /summary-v3/{popular,inplay,upcoming}`.
  > - WebSocket (`1` persistent Centrifugo connection, token refresh every `55m` `<< 30 req/60s`): `GET /user/realtime-token-v3/api-key` -> `wss://realtime.sx.bet/connection/websocket` (`orderbook_v3:{marketHash}`, `best_odds_v3:global`).
  > **3. Server Hosting Location:** Dedicated cloud VM `quant-pipeline-finland` in Finland (`FI`, EU), sandboxed via systemd with `0600` secret storage (`0` redistribution; internal SQLite WAL research retention only).
  > **4. Authorization Request:** Please confirm (a) whether SX Bet grants standalone written read-only market-data permission (`SX_BET_DATA_APPROVAL_ID`) for non-trading research on `FI` infrastructure, or (b) onboarding requirements for our non-restricted corporate entity to issue a fresh read-only `SX_BET_API_KEY`.
- **Single-Collector Hot-Reload Commands (Zero Restart of Other Feeds):**
  ```bash
  # While inquiry is under review (`AUTHORIZATION_PENDING`):
  python scripts/deploy_cross_venue_shadow.py --host kraken-finland --provision-secret SX_BET_DATA_INQUIRY_ID
  # Once approved (or under an eligible entity) + fresh SX_BET_API_KEY issued:
  python scripts/deploy_cross_venue_shadow.py --host kraken-finland --provision-secret SX_BET_DATA_APPROVAL_ID
  python scripts/deploy_cross_venue_shadow.py --host kraken-finland --provision-secret SX_BET_API_KEY
  ```

### Workflow D — Predict.fun Mainnet Read-Only `Content Features` (`x-api-key`, Active) vs. `Technology Features` (`RESTRICTED` in `CA-ON`)
- **Official Sources:** PDF Labs Limited Terms of Service Section 1 (`https://docs.predict.fun/terms-of-service`, Last Updated Nov 18, 2025), Predict.fun Developer Console (`https://developers.predict.fun`), & API Docs (`https://dev.predict.fun` — `GET /v1/markets?first=100&status=OPEN&after=...`, `GET /v1/markets/{id}/orderbook`, `GET /v1/categories`, and `wss://ws.predict.fun/ws` `x-api-key` header `predictOrderbook/{id}` + `predictTopOfBook/{id}`).
- **First-Principles 3-Capability Separation:**
  - **`MARKET_DATA_ACCESS = AUTHORIZED_LIVE` (`Content Features`):** Section 1 defines `Content Features` as *"all content, informational functionality, and information features"* and `Technology Features` as *"software, including... the Platform, that may be available to users by connecting their self-hosted wallets via an Interface"*, and expressly provides: *"If you are in a Restricted Jurisdiction, you are only permitted to use the Content Features on the Site or any other Interface"*. Predict.fun imposes zero `PREDICT_FUN_DATA_LICENSE_ID` requirement; provisioning `PREDICT_FUN_API_KEY` + `PREDICT_FUN_ENV=mainnet` activates live read-only REST + WebSocket market data (`0` wallet connection, `0` `POST /v1/auth` JWT, `0` trading).
  - **`SHADOW_RESEARCH_ACCESS = AUTHORIZED_LIVE`:** Local read-only cross-venue matching (`polymarketConditionIds` + SHA-256 rule parity) and L2 simulation active.
  - **`LIVE_TRADING_ACCESS = RESTRICTED` (`Technology Features`):** `POST /v1/auth` wallet-signed JWTs, `POST /v1/orders`, and BNB Chain `Contracts` remain hard-disabled under `CA-ON` unless operated by an independently eligible non-restricted entity.
- **Single-Collector Hot-Reload Commands (Zero Restart of Other Feeds):**
  ```bash
  /home/skybullet1987/quant_pipeline/venv/bin/python /home/skybullet1987/quant_pipeline/scripts/deploy_cross_venue_shadow.py --host self --provision-secret PREDICT_FUN_ENV,PREDICT_FUN_API_KEY
  ```

### Workflow E — Limitless Exchange Full Mainnet REST + Realtime Socket.IO v4 Streaming (`Priority A`)
- **Official Sources:** Street Chow Inc. Terms of Service Section 1 (`https://limitless.exchange/terms`) & Limitless API Docs (`https://api.limitless.exchange/api-v1`).
- **7-Scope Status (`verified_outcome_state = AUTHORIZED_LIVE`):**
  - `PUBLIC_REST = AUTHORIZED_LIVE` (`GET /markets/active?limit=25&page=1..12` across all ~`296` active markets, `/markets/active/slugs`, `/categories`, `/markets/{slug}/orderbook`).
  - `PUBLIC_WEBSOCKET = AUTHORIZED_LIVE` (`wss://ws.limitless.exchange/socket.io/?EIO=4&transport=websocket`, namespace `/markets`, `subscribe_market_prices` -> `orderbookUpdate`, `oraclePriceData`, `newPriceData`, `25s` `'2'->'3'` Engine.IO heartbeat, `23.5h` proactive rotation).
  - `SERVER_HOSTING = AUTHORIZED_LIVE` (`FI` EU VM).
  - `AUTHENTICATED_READONLY = RESTRICTED`, `ACCOUNT_PRIVATE = RESTRICTED`, `TRADING = RESTRICTED` under `CA-ON` (`0` API/HMAC keys used; chat-exposed legacy secret permanently SHA-256 blocklisted).
