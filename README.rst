guillotina_redsys
=================

Redsys (Sermepa) REST + 3-D Secure 2.x integration for the Guillotina framework.

This package provides:

- A Guillotina utility to orchestrate Redsys REST calls.
- Pydantic v1 models for merchant parameters, EMV3DS, final authorization, and errors.
- An async HTTP client (aiohttp + tenacity) with retries.
- Mandatory Redis usage to correlate and finish 3-DS flows (stores threeDSCompInd and CRES).
- Guillotina services (endpoints) to start transactions, run AuthenticationData, and handle ACS callbacks.

Requirements
------------

- Python 3.9+
- Guillotina
- aiohttp, tenacity, pydantic==1.*
- Redis via guillotina.contrib.redis
- Redsys merchant credentials (FUC, Terminal, Secret Key)

Installation
------------

.. code-block:: bash

   pip install guillotina_redsys

Configuration
-------------

Enable the app and configure the utility in Guillotina settings. The Redis add-on must be enabled.

Example (pseudocode):

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

Exposed services (HTTP)
-----------------------

Resource-scoped:

- POST ``@initTransactionRedsys``: calls ``iniciaPeticionREST``; returns decoded payload and a prebuilt payload for 3DS Method.
- POST ``@initThreeDS``: helper to initiate 3DS Method (mainly for testing; in production the browser posts the form).
- POST ``@initTrataPeticion``: builds AuthenticationData; returns either (acsURL + creq) for challenge or a final frictionless result.

Container-scoped (callbacks and finalization):

- POST ``@notificationRedsys3DS/{order_id}/{three_dss_trans_id}``: stores ``threeDSCompInd`` in Redis (TTL 15m).
- GET  ``@getnotificationRedsys3DS/{order_id}/{three_dss_trans_id}``: reads ``threeDSCompInd``.
- POST ``@notificationRedsysChallenge/{order_id}/{three_dss_trans_id}``: stores raw CRES in Redis (TTL 30m).
- POST ``@performNotificationRedsysChallenge/{order_id}/{three_dss_trans_id}``: reads CRES and finalizes with ChallengeResponse; returns final authorization result.

Redis keys
----------

- ``notification_3DS:{order}:{sid}`` → ``"Y"`` or ``"N"`` (TTL 15 minutes)
- ``notification_CRES:{order}:{sid}`` → base64url CRES (TTL 30 minutes)

Flow summary
------------

1. Start: backend calls Redsys ``iniciaPeticionREST`` (CardData).  
2. Optional 3DS Method: browser posts ``threeDSMethodData``; backend receives method callback and records ``threeDSCompInd`` in Redis.  
3. AuthenticationData: backend calls Redsys ``trataPeticionREST``; either gets (acsURL + creq) for challenge or a frictionless final result.  
4. Challenge: browser posts ``creq`` to ACS; ACS posts ``CRES`` to backend callback.  
5. Finalization: backend reads ``CRES`` from Redis and calls Redsys ``trataPeticionREST`` with ``threeDSInfo="ChallengeResponse"``; returns final authorization.

Security notes
--------------

- Use HTTPS for all public endpoints.
- Do not log PAN/CVV.
- If you store card data yourself, encrypt and keep a short TTL; purge after finalization.
- Ensure unique order ids to avoid Redsys duplicate-order errors (e.g. SIS0051).
