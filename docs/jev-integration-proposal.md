# Proposal: add an optional JEV decision layer

## Summary

This proposal adds an optional JEV (TypeSafe System One) decision layer to Stockbot. JEV would make bounded, confidence-aware decisions from a normalized market snapshot; Stockbot would continue to own validation, wallet custody, risk limits, transaction construction, and submission.

This is intentionally a proposal rather than a live-trading implementation. JEV is a hosted, early-access service and Stockbot currently has wallet/balance UI plus a simulated transaction path, not a complete market-data or order-execution loop. The first milestone should therefore be a paper/shadow integration with no path from a model response directly to a signed transaction.

## Why JEV is a useful fit for Stockbot

1. **It removes a fragile classification boundary.** A trading decision has a small, known answer space. JEV's `Choice`, `Score`, and `Noul` primitives return typed answers and probabilities, so Stockbot would not need to ask a text-generating model for `BUY`/`SELL`/`HOLD` and then parse arbitrary prose. This makes malformed or unexpected model output less likely to reach trading code.
2. **It enables several decisions in one request.** A single state can ask for direction, market regime, risk, and whether conditions are safe to trade. Batching those questions avoids repeating the same market snapshot and lets Stockbot make one consistent decision cycle rather than coordinating several independent model calls.
3. **Its confidence is actionable.** Stockbot can distinguish a high-confidence decision from an ambiguous one and turn uncertainty into `HOLD` or human review. This is more useful than treating every model label as an instruction to trade. The returned probability must be measured against Stockbot's own historical outcomes before it is used as a position-sizing input.
4. **It is suitable for a fast decision gate.** JEV is designed for structured decisions rather than prose generation. A bounded call can sit after data ingestion and before deterministic risk checks, where a slow, verbose model would make quotes and prices stale. The integration should record actual p50/p95 latency in Stockbot instead of assuming published latency will hold for every network path.
5. **It can lower repeated-decision overhead.** The current published price is per input token and output is free. Sending one compact, normalized snapshot with multiple questions should be cheaper than sending the same snapshot to separate prompt-and-parse workflows. Stockbot must still cap request frequency and log usage; cost is not a reason to bypass risk controls.

## Proposed decision pipeline

```text
market data + wallet state
          |
          v
normalized snapshot (timestamped, no secrets)
          |
          v
JEV: direction + regime + risk + data-quality questions
          |
          v
schema validation and confidence policy
          |
          v
pure Python risk gate
          |
          +--> HOLD / review (default on uncertainty or stale data)
          |
          +--> paper order first; live execution only after explicit opt-in
```

### Snapshot contract

The adapter should send only the information needed for a decision, for example:

- asset/pair and venue;
- bid, ask, mid, spread, quote age, and available depth;
- returns over fixed windows and volatility;
- volume/liquidity and estimated fees/slippage;
- current position, available balance, exposure, and cooldown state; and
- a `data_as_of` timestamp and an explicit missing-data marker.

Private keys, encrypted wallet material, API keys, and raw credentials must never be included in the JEV state. The adapter should reject a snapshot whose timestamp is older than the configured maximum age.

### Typed questions

The first version can ask all of these in one request:

- `action`: `Choice` of `buy`, `sell`, and `hold`;
- `regime`: `Choice` of `trend`, `range`, `high_volatility`, and `unknown`;
- `risk`: `Score` with documented levels from `acceptable` to `unacceptable`; and
- `tradeable`: `Noul` asking whether the supplied snapshot contains enough reliable evidence to trade.

The question descriptions should define every option. They should not ask JEV to choose an amount, sign a transaction, or override a risk limit. A model answer is a signal, never authorization.

## How Stockbot should use the result

The deterministic policy should be the final authority. A conservative first policy would:

1. return `HOLD` for a missing, stale, malformed, or internally inconsistent snapshot;
2. return `HOLD` unless `tradeable` passes a separately calibrated threshold;
3. require a minimum action probability and a minimum margin over the runner-up choice;
4. enforce allowlisted assets, maximum notional, maximum exposure, cooldowns, slippage and fee limits, and a circuit breaker;
5. map `buy`/`sell` to a paper order and log the complete decision before any live feature is considered; and
6. keep live execution behind an explicit opt-in and a final user confirmation while the integration is experimental.

JEV should not replace the existing wallet security boundary. In particular, it should never receive a private key and should never call `send_transaction` itself. The current simulated send path is the correct place to begin validating the contract.

## Suggested implementation plan

### Phase 1: adapter and shadow mode

- Add an optional `typesafe_sdk` dependency or a small HTTP client behind a feature flag.
- Read `TYPESAFE_API_KEY`, model version, endpoint, timeout, and confidence thresholds from environment/configuration; never commit credentials.
- Introduce a JEV adapter with typed request/response models, strict response validation, bounded retries, and request timeouts.
- Add a deterministic snapshot builder that redacts secrets and rejects stale data.
- Record decisions, returned model version, latency, token usage, probabilities, and the eventual observed outcome without placing orders.

### Phase 2: paper trading and evaluation

- Run the same snapshots through a replayable paper-trading loop.
- Compare JEV against the existing/no-op baseline and a simple deterministic baseline.
- Report precision, recall by action, abstention rate, calibration/error by confidence bucket, turnover, fees, slippage, drawdown, and p50/p95 decision latency.
- Pin a model version for evaluation and retain the version returned by each response so an alias update cannot silently change results.

### Phase 3: guarded opt-in execution

Only after the paper results meet agreed thresholds should a separate change add live execution. That change must retain the deterministic risk gate, default to paper mode, support an immediate kill switch, and require explicit opt-in for each environment.

## Acceptance criteria for this proposal

- Stockbot starts and retains all current wallet/balance behavior when no JEV key is configured.
- No secret or private key is present in the JEV payload or logs.
- A JEV outage, timeout, malformed answer, low-confidence answer, or stale snapshot results in `HOLD`, not an order.
- Multiple questions are submitted against one snapshot, and the adapter validates the fixed action set before policy evaluation.
- Shadow/paper logs include timestamp, snapshot identifier, requested and returned model version, action probabilities, confidence, latency, and cost/usage when supplied.
- Tests cover malformed responses, missing fields, stale data, timeout/retry behavior, threshold boundaries, and the never-send-on-failure rule.
- The evaluation report demonstrates whether JEV improves decisions after fees and slippage; model confidence alone is not considered proof of profitability.

## Risks and open questions

- JEV is a hosted dependency and may require account approval, have changing limits, or experience outages. The feature must remain optional and fail closed.
- A calibrated probability for the supplied question is not automatically a calibrated trading win rate. Stockbot needs timestamped, out-of-sample evaluation and should avoid using confidence for sizing until calibration is demonstrated.
- Market data can be delayed, manipulated, or incomplete. Explicit freshness and liquidity gates are as important as the model call.
- The model may add latency or cost without improving net returns. The decision log and baseline comparison are required before enabling live execution.
- The current repository does not yet provide a production market-data feed or real order path. Those interfaces should be defined separately rather than hidden inside the JEV adapter.

## References

- [TypeSafe introduction](https://docs.typesafe.ai/introduction)
- [TypeSafe quick start](https://docs.typesafe.ai/introduction/quickstart)
- [TypeSafe model limits and pricing](https://docs.typesafe.ai/models)
- [TypeSafe Choice primitive](https://docs.typesafe.ai/primitives/choice)
