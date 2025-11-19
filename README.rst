
guillotina_redsys
=================

Redsys (Sermepa) **REST + 3‑D Secure 2.x** integration for the **Guillotina** framework.

This package provides:

- A Guillotina utility (``IRedsysUtility``) to orchestrate Redsys REST calls.
- Strong Pydantic v1 models for requests/responses (merchant parameters, EMV3DS, final auth, errors).
- An async HTTP client (``aiohttp`` + ``tenacity``) for Redsys with retries/backoff.
- A **mandatory Redis** short‑lived state layer used by the included API endpoints to coordinate browser‑based 3‑DS steps (3DS Method + Challenge).
- Ready‑to‑use Guillotina services (endpoints) for: starting a transaction, initiating the optional 3DS Method, starting the AuthenticationData step, and handling both ACS callbacks (3DS Method notify and CRes/Challenge).

Why Redis is mandatory?
-----------------------
Redsys REST + 3‑DS is a multi‑step flow. The browser must post to the issuer’s ACS, while your backend receives asynchronous callbacks and later finalizes the payment. Redis stores minimal per‑order state (such as 3‑DS indicators and the transient CRes) with a short TTL to safely chain these steps.

Requirements
------------
- Python 3.9+
- Guillotina
- ``aiohttp``, ``tenacity``, ``pydantic==1.*``
- **Redis** (via ``guillotina.contrib.redis``) – *required*
- A Redsys merchant test account (FUC, Terminal, Secret Key).

Installation
------------
.. code-block:: bash

   pip install guillotina_redsys

Configuration
-------------
``guillotina_redsys.init`` registers the utility and endpoints. Configure via environment variables and enable ``guillotina.contrib.redis``.

.. code-block:: python

   apps = ["guillotina.contrib.redis", "guillotina_redsys"]

   app_settings = {
       "applications": apps,
       "load_utilities": {
           "redsys": {
               "provides": "guillotina_redsys.interfaces.IRedsysUtility",
               "factory": "guillotina_redsys.utility.RedsysUtility",
               "settings": {
                   "merchant_code": os.environ["REDSYS_MERCHANT_CODE"],
                   "terminal": os.environ.get("REDSYS_TERMINAL", "001"),
                   "secret_key": os.environ["REDSYS_SECRET_KEY"],
                   "url_redsys": os.environ.get(
                       "REDSYS_URL", "https://sis-t.redsys.es:25443/sis/rest"
                   ),
                   # Your public base URL to build callback routes (see below)
                   "container_url": os.environ["REDSYS_CONTAINER_URL"],
               },
           }
       },
   }

Suggested environment variables:

.. code-block:: bash

   export REDSYS_MERCHANT_CODE=999008881
   export REDSYS_TERMINAL=001
   export REDSYS_SECRET_KEY=...
   export REDSYS_URL=https://sis-t.redsys.es:25443/sis/rest
   export REDSYS_CONTAINER_URL=https://your.app/db/container

Exposed Services (HTTP endpoints)
---------------------------------

All routes are registered on a *resource* (for start/init) or the *container* (for callbacks).

1) Start a transaction
~~~~~~~~~~~~~~~~~~~~~~
``POST  @initTransactionRedsys`` (resource)

Builds Redsys merchant params (CardData), calls ``iniciaPeticionREST``, decodes payload, and returns it plus a pre‑built ``payload_3DS`` (base64url of ``threeDSServerTransID`` + the 3DS Method callback URL).

**Request body** (JSON)::

   {
     "amount": "12.49",
     "card": "4548810000000003",
     "expiry_date": "4912",
     "cvv": "123",
     "order_id": "ABCD1234"
   }

Returns: decoded ``RedsysIniciaPeticionResponse`` (may include ``threeDSMethodURL`` and ``payload_3DS`` for the browser).

2) Optional: 3DS Method kick‑off (front‑end oriented)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
``POST  @initThreeDS`` (resource)

Accepts ``transaction_id`` (``threeDSServerTransID``) and ``three_method_url``. The browser **should** post a form with ``threeDSMethodData`` to the issuer’s URL; this endpoint is provided mainly for testing.

**Request body** (JSON)::

   { "transaction_id": "uuid", "three_method_url": "https://.../threeDsMethod.jsp" }

Returns: ``{ "threeDSCompInd": "Y|N" }`` (based on a 10s wait).

**Callback for Method:**

- ``POST  @notificationRedsys3DS/{order_id}/{three_dss_trans_id}`` (container)
- Body example: ``{ "threeDSCompInd": "Y" }``
- Redis key: ``notification_3DS:{order}:{trans}`` (TTL 15 min).
- You can check it with: ``GET  @getnotificationRedsys3DS/{order_id}/{three_dss_trans_id}``.

3) AuthenticationData (trataPeticion – step 1)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
``POST  @initTrataPeticion`` (resource)

Builds EMV3DS **AuthenticationData** (browser hints, ``threeDSCompInd``, ``notificationURL`` for CRes) and calls ``trataPeticionREST``. Returns either:

- ``RedsysEMV3DSResponse`` with **``acsURL`` + ``creq``** (Challenge), or
- ``RedsysAuthResult`` (Frictionless final, with ``Ds_Response``).

**Request body** (JSON)::

   {
     "transaction_id": "uuid",
     "amount": "12.49",
     "card": "4548810000000003",
     "expiry_date": "4912",
     "cvv": "123",
     "order_id": "ABCD1234",
     "protocol_version": "2.2.0",
     "three_ds_comp_ind": "Y"
   }

**Challenge callback (CRes):**

- ``POST  @notificationRedsysChallenge/{order_id}/{three_dss_trans_id}`` (container)
- Body: ``{ "CRES": "<base64url>" }`` → stored in Redis under ``notification_CRES:{order}:{trans}`` (TTL 30 min).
- To finalize: ``POST  @performNotificationRedsysChallenge/{order_id}/{three_dss_trans_id}`` with the original transaction context (amount/card/expiry/cvv/protocol).

4) ChallengeResponse Finalization
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
``POST  @performNotificationRedsysChallenge/{order_id}/{three_dss_trans_id}`` (container)

Reads the ``CRES`` from Redis, calls ``trataPeticionREST`` with ``threeDSInfo="ChallengeResponse"`` + ``cres``, and returns ``RedsysAuthResult`` (``Ds_Response == "0000"`` means authorized).

**Request body** (JSON)::

   {
     "amount": "12.49",
     "card": "4548810000000003",
     "expiry_date": "4912",
     "cvv": "123",
     "protocol_version": "2.2.0",
     "currency": 978
   }

Backend Utility
---------------
``RedsysUtility`` wires everything together. Key methods:

- ``init_transaction(...)`` → wraps ``iniciaPeticionREST``; returns ``RedsysIniciaPeticionResponse`` with ``payload_3DS`` generated and the method notification URL prefilled.
- ``init_threeds_method(...)`` → helper for testing; in production post ``threeDSMethodData`` from the browser.
- ``init_trata_peticion(...)`` → builds AuthenticationData and returns either ``RedsysEMV3DSResponse`` (Challenge) or ``RedsysAuthResult`` (Frictionless).
- ``authenticate_cres(...)`` → reads stored CRes and finalizes with ``threeDSInfo="ChallengeResponse"``.

Data kept in Redis
------------------
- ``notification_3DS:{order}:{sid}`` → ``"Y"``/``"N"`` (TTL 15 min)
- ``notification_CRES:{order}:{sid}`` → raw CRes base64url (TTL 30 min)

Note: This package keeps the bare minimum in Redis to correlate callbacks and finish the flow. *Card/PAN/CVV are passed again by the caller when finalizing*. If you wish to hold card data between steps, do so **encrypted** and purge immediately after finalization.

Frontend contract (recommended)
-------------------------------
1. Start with ``@initTransactionRedsys`` → if it returns ``threeDSMethodURL`` and ``payload_3DS``, post ``threeDSMethodData`` via hidden form and wait 10s in the UI.
2. Call ``@initTrataPeticion`` with ``three_ds_comp_ind`` = ``"Y"`` if method callback was received (use ``@getnotificationRedsys3DS/...``), otherwise ``"N"``.
3. If you receive ``acsURL + creq``, post ``creq`` (form) to the ACS; the issuer will send ``CRES`` to the backend’s ``@notificationRedsysChallenge/...``.
4. Finalize by calling ``@performNotificationRedsysChallenge/...`` with the original transaction context to get the final result.

Security notes
--------------
- Use HTTPS everywhere (callbacks/public base URL).
- Do **not** log PAN or CVV2.
- If you persist card data between steps, encrypt and set short TTLs (purge on completion).
- Handle callbacks quickly and idempotently (return ``200`` fast and rely on Redis).
- Ensure unique ``order_id`` per transaction to avoid Redsys ``SIS0051`` errors.

Testing
-------
- Use Redsys test credentials and the sandbox URL (``sis-t``).
- Always generate unique order ids per test run.
- The ACS simulator may behave differently across issuers; prefer exercising flows via the browser where possible.

License
-------
Choose a license (e.g., MIT).
