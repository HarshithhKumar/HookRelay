# Known Failure Modes

This document lists realistic ways the current LinkPLEASE implementation can still lose a DM, duplicate a DM, or report an incorrect statistic. Each item explains the exact condition, what may happen, why the current system cannot fully prevent it, and suggestions for improvement.

1) Process crash between POST /v1/dm/send acceptance and Delivery creation

Condition:
- The DM worker receives HTTP 202 from PseudoGram (contains dm_id) and the process crashes after updating DMJob status to ACCEPTED but before creating the Delivery record (or committed transaction partially applied).

What can happen:
- The system has a DMJob marked ACCEPTED with dm_id but no Delivery record to reconcile it. Delivery reconciliation will not track that dm_id, so a delivered DM may never be counted as sent.

Why current system cannot fully prevent it:
- The DM worker updates the DMJob and then separately creates a Delivery row inside the same application flow. If a crash occurs between these steps or the DB transaction is not atomic across both updates, reconciliation state may be missing.

Mitigation / improvement:
- Create Delivery records in the same database transaction that marks the DMJob accepted (or embed Delivery creation as part of the DMJob update). Use transactional tests and retries to ensure idempotence.

2) Network partition after sending but before idempotent record creation

Condition:
- The worker posts to PseudoGram and the POST succeeds on the remote side but the response is lost due to network partition. The local process retries and obtains a second dm_id or a 202 again.

What can happen:
- Duplicate outbound DMs may be created if the idempotency key differs across retry attempts or if the local state does not persist the initial acceptance consistently.

Why current system cannot fully prevent it:
- The system relies on stable idempotency keys built from the DMJob ID. If the job record was not updated before the network failure, or multiple workers race without a consistent lease, duplicates are possible.

Mitigation / improvement:
- Persist an initial send-attempt record with the idempotency key in the same transaction as modifying the DMJob lease; ensure retries reuse the same idempotency key.

3) Reconciliation delay during extended downtime

Condition:
- Reconciliation worker is down for an extended period while many DMJobs are in ACCEPTED state.

What can happen:
- Delivered messages are not promptly reflected as "sent"; stats under-count delivered messages until the worker runs again. Rate limiting and retry decisions may be delayed.

Why current system cannot fully prevent it:
- The reconciliation worker runs as a separate process. If it's not deployed, reconciliation cannot proceed.

Mitigation / improvement:
- Run reconciliation as a scheduled platform job (cron/managed worker) and implement alerting when deliveries accumulate in ACCEPTED state beyond a threshold.

4) Race between duplicate-block insert and concurrent job creation

Condition:
- Two webhook events for the same rule and recipient are processed concurrently on different workers; both check uniqueness and try to insert DMJob.

What can happen:
- Database uniqueness constraint prevents duplicate DMJob, but one worker may observe the constraint violation only after attempting insert and then records a duplicate-block entry — timing may cause inconsistent counts or missed duplicate-block records.

Why current system cannot fully prevent it:
- The uniqueness constraint prevents two DMJob rows but the application-level duplicate-block recording is a separate insert, which may be lost if the transaction ordering differs.

Mitigation / improvement:
- Use transactional upsert patterns that insert both DMJob and duplicate-block deterministically, or record duplicate-blocks inside the same transaction that observes the uniqueness violation.

(End of file)
