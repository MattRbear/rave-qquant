# GitHub Copilot Instructions for rave-qquant

## Repository Overview

This is a **crypto whale intel bot** with a gated waterfall architecture:

```
WhaleAlert trigger → Alchemy validate (WS + multicall) → Etherscan decode (ABI+proxy cache) → 
Moralis (rare) → Dune (rare) → scoring → alerts → Postgres/TimescaleDB
```

**Core Purpose:** Provide intel (not trade advice) on whale movements with strict budget/rate-limit constraints.

## Hard Constraints (MUST FOLLOW)

### 1. Safety & Destructive Operations
- ❌ **NEVER** use destructive commands: `rm -rf`, broad wildcard deletes, or delete data files
- ❌ **NEVER** delete or modify working code unless absolutely necessary
- ✅ Always fail-closed: on budget exhaustion or API errors → degrade gracefully and record reason
- ✅ All changes must be auditable with clear paper trail in commit messages

### 2. Idempotency & Data Integrity
- ✅ **ALWAYS** implement idempotency for event processing
- ✅ Use dedupe keys + DB constraints to prevent duplicate alerts
- ✅ DB writes must be atomic and idempotent (no duplicate alerts after restart/retry)
- ✅ Ensure replay safety: same input data → same output state

### 3. API Budget & Rate Limiting
- ✅ **ALWAYS** respect rate limits via existing `rate_limiting/` utilities
- ❌ **NEVER** bypass the rate limiter or budget tracker with direct API calls
- ❌ **NEVER** use ad-hoc `sleep()` loops for rate limiting
- ✅ Use token bucket pattern from existing utilities
- ✅ Track and log budget consumption
- ✅ Fail gracefully when budgets are exhausted

### 4. Architecture Patterns
- ✅ Prefer **validation over discovery**: use WebSockets where available, no polling
- ✅ Follow the waterfall pattern: early validation gates prevent expensive downstream calls
- ✅ Use append-only JSONL storage pattern (see existing `Rave_Quant_Vault/`)
- ✅ Maintain state cursors for incremental processing

### 5. Output & Communication
- ❌ **NEVER** use "signal" language or price targets in alerts
- ✅ Output is **intel only**, not trade advice
- ✅ Use structured logging (JSON format preferred)
- ✅ All logs must be machine-readable and auditable

## Coding Standards

### Python Requirements
- **Version:** Python 3.12
- **Type hints:** Required for all functions (mypy-friendly)
- **Logging:** Structured logging (JSON when possible)
- **Testing:** Every new feature gets at least unit tests for pure logic

### Async/Network Code
- ✅ All async/network code must have:
  - Timeouts configured
  - Retry logic with exponential backoff
  - Jitter to prevent thundering herd
- ✅ Use existing patterns from `coinayalze_bot/coinalyze_bot.py` as reference

### Code Style
```python
# Type hints required
def process_whale_alert(alert: Dict[str, Any], ctx: ProcessingContext) -> Optional[Alert]:
    """Process whale alert with idempotency check."""
    pass

# Structured logging
logger.info("whale_alert_processed", extra={
    "alert_id": alert["id"],
    "amount_usd": alert["amount_usd"],
    "dedupe_key": dedupe_key
})
```

## Development Workflow

### Before Making Changes
1. Check existing patterns in similar modules
2. Verify rate limiting is in place for any API calls
3. Ensure idempotency strategy is clear
4. Plan for failure modes and degradation

### Pull Request Requirements
- ✅ One subsystem per PR (prefer small PRs)
- ✅ All tests pass: `pytest -q`
- ✅ Linting passes (use existing config: ruff/black/etc)
- ✅ PR template checklist completed
- ✅ Clear commit messages explaining "why" not just "what"

### Testing Requirements
- ✅ Unit tests for all pure logic
- ✅ Integration tests for API interactions (with mocks)
- ✅ Idempotency tests: run twice, verify same result
- ✅ Rate limit tests: verify backoff behavior

## Data Patterns

### Storage: Append-Only JSONL
```
Input:  Vault\raw\{source}\{type}\{INSTID}\{DATE}.jsonl
Process: [Read → Process → Output]
Output: Vault\derived\{metric}\{exchange}\{market}\{INSTID}\{output}.jsonl
State:  Vault\state\{metric}\{exchange}\{market}\{INSTID}.state.json
```

**Why?**
- Append-only prevents corruption
- Human-readable for debugging
- Deterministic: same input = same output
- No database overhead

### State Management
```python
# Always load cursor before processing
cursor = load_state(state_file)
# Process only new data
new_records = fetch_since(cursor)
# Update cursor atomically
save_state(state_file, new_cursor)
```

## Common Pitfalls to Avoid

### ❌ Don't Do This
```python
# Direct API call without rate limiting
response = requests.get(api_url)

# Ad-hoc sleep for rate limiting  
time.sleep(1)

# Non-idempotent alert insertion
db.execute("INSERT INTO alerts VALUES (?)", alert)

# Polling when WebSocket available
while True:
    data = fetch_latest()
    time.sleep(interval)
```

### ✅ Do This Instead
```python
# Use rate limiter
with rate_limiter.acquire():
    response = requests.get(api_url)

# Use existing rate limiting utilities
bot._enforce_rate_limit()
response = requests.get(api_url)

# Idempotent insertion with constraint
db.execute(
    "INSERT INTO alerts VALUES (?) ON CONFLICT (dedupe_key) DO NOTHING", 
    alert
)

# WebSocket with validation
async def on_message(msg):
    if validate(msg):
        process(msg)
```

## Architecture Guidelines

### The Waterfall Pattern
Each stage validates before passing to the next expensive stage:

```python
# Stage 1: Cheap validation (free)
if not meets_threshold(alert):
    return  # Early exit

# Stage 2: WebSocket validation (cheap, existing connection)
if not validate_via_ws(alert):
    return

# Stage 3: Multicall (moderate cost)
if not validate_via_multicall(alert):
    return

# Stage 4: Etherscan (rate limited)
abi_data = fetch_with_rate_limit(etherscan_api)

# Stage 5: Moralis/Dune (expensive, rare)
if needs_deep_validation:
    moralis_data = fetch_with_budget_check(moralis_api)
```

### Budget Tracking
```python
# Always check budget before expensive calls
if not budget_tracker.can_afford(cost):
    logger.warning("budget_exhausted", extra={"api": "moralis"})
    return None  # Fail closed

# Track consumption
budget_tracker.consume(cost, api="moralis")
```

## Migration Guidelines

### Database Migrations
- ✅ Migrations must be reversible
- ✅ Add new columns as nullable first
- ✅ Backfill in separate transaction
- ✅ Make column non-nullable in separate migration
- ✅ Document rollback procedure

### Breaking Changes
- ✅ Version APIs and data formats
- ✅ Support old and new formats during transition
- ✅ Deprecate gradually with warnings
- ✅ Document migration path in PR

## Documentation Requirements

### Code Documentation
```python
def process_alert(alert: Dict[str, Any]) -> Optional[Alert]:
    """
    Process whale alert with validation and deduplication.
    
    Args:
        alert: Raw alert data from WhaleAlert API
        
    Returns:
        Processed Alert object or None if validation fails
        
    Note:
        This function is idempotent. Calling twice with same
        alert will result in single DB entry due to dedupe_key.
    """
```

### README Updates
When adding new features, update:
- Setup instructions if new dependencies added
- Environment variables section if new configs required
- Architecture diagram if flow changes
- Example commands for running the feature

## Security Considerations

### API Keys & Secrets
- ❌ **NEVER** commit API keys or secrets
- ✅ Use environment variables
- ✅ Document required env vars in README
- ✅ Provide `.env.example` template

### Input Validation
- ✅ Validate all external inputs
- ✅ Sanitize before database insertion
- ✅ Use parameterized queries (no string concatenation)
- ✅ Validate data types and ranges

## Performance Guidelines

### Optimization Priorities
1. **Correctness** - Must work correctly
2. **Idempotency** - Must be safe to retry
3. **Budget Safety** - Must respect limits
4. **Performance** - Optimize only after above are satisfied

### When to Optimize
- ✅ Batch operations when possible
- ✅ Use indexes for frequent queries
- ✅ Cache ABI/proxy data (as shown in Etherscan decode)
- ❌ Don't optimize prematurely
- ❌ Don't sacrifice clarity for minor performance gains

## Getting Help

### Resources
- `SYSTEM_OVERVIEW.txt` - High-level system description
- `README.md` - Detailed component documentation
- `coinayalze_bot/coinalyze_bot.py` - Rate limiting pattern reference
- Module READMEs - Component-specific documentation

### When Stuck
1. Check similar existing code for patterns
2. Verify you're following rate limiting rules
3. Check logs for budget/rate limit issues
4. Ensure idempotency is maintained

## Review Checklist

Before submitting PR, verify:
- [ ] No direct API calls bypass rate limiter
- [ ] All new code has type hints
- [ ] Idempotency is maintained (can run twice safely)
- [ ] Structured logging is used
- [ ] Tests are added and passing
- [ ] Documentation is updated
- [ ] No secrets are committed
- [ ] Budget tracking is in place for expensive calls
- [ ] Error handling degrades gracefully
- [ ] Commit messages explain "why"

---

**Remember:** This system handles real money decisions. Prioritize correctness, safety, and auditability over speed of development.
