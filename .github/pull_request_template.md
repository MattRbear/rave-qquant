## Description
<!-- Provide a brief description of the changes in this PR -->

## Type of Change
<!-- Mark the relevant option with an 'x' -->
- [ ] Bug fix (non-breaking change which fixes an issue)
- [ ] New feature (non-breaking change which adds functionality)
- [ ] Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] Documentation update
- [ ] Refactoring (no functional changes)
- [ ] Performance improvement
- [ ] Dependency update

## Checklist

### Core Requirements
- [ ] **Tests added/updated**: All new features have unit tests (at least for pure logic)
- [ ] **Tests passing**: `pytest -q` runs successfully
- [ ] **Lint/format passing**: Code follows existing style (ruff/black/etc)
- [ ] **Type hints added**: All new functions have mypy-friendly type hints
- [ ] **Documentation updated**: README or module docs reflect changes

### API Budget & Rate Limiting
- [ ] **No rate limiter bypass**: All API calls use existing rate limiting utilities
- [ ] **Budget tracking**: Expensive API calls (Moralis/Dune/Etherscan) check budget before calling
- [ ] **Graceful degradation**: System fails closed on budget exhaustion with logged reason
- [ ] **No ad-hoc sleep**: Rate limiting uses token bucket pattern, not `time.sleep()` loops

### Idempotency & Data Integrity
- [ ] **Idempotent operations**: Event processing can be safely retried/replayed
- [ ] **Dedupe keys present**: Database operations use unique constraints to prevent duplicates
- [ ] **Atomic writes**: No partial state or duplicate alerts possible after restart
- [ ] **Idempotency test**: Verified that running operation twice produces same result

### Architecture & Patterns
- [ ] **Follows waterfall**: Changes respect the validation gate pattern
- [ ] **WebSocket preferred**: No polling added where WebSocket/event-driven option exists
- [ ] **JSONL pattern**: New data storage uses append-only JSONL format
- [ ] **State cursors**: Incremental processing maintains cursor in state files

### Database Changes
- [ ] **No migrations**: This PR does not include database schema changes
- OR (if migrations included):
  - [ ] **Migration reversible**: Rollback procedure documented
  - [ ] **Nullable first**: New columns added as nullable initially
  - [ ] **Backfill separate**: Data backfill is separate transaction
  - [ ] **Migration tested**: Tested both upgrade and rollback

### Security & Safety
- [ ] **No secrets committed**: API keys/tokens use environment variables only
- [ ] **Input validated**: All external inputs are validated and sanitized
- [ ] **Parameterized queries**: No SQL string concatenation
- [ ] **No destructive commands**: No `rm -rf` or broad wildcard deletes

### Logging & Monitoring
- [ ] **Structured logging**: Uses JSON-formatted logging where possible
- [ ] **Machine-readable**: Logs include relevant context (IDs, amounts, keys)
- [ ] **Audit trail**: Changes are traceable through logs
- [ ] **Error logging**: Failures are logged with context for debugging

### Output Standards
- [ ] **No "signal" language**: Alerts use intel language, not trade advice
- [ ] **No price targets**: Output does not suggest entry/exit prices

## Testing Notes
<!-- Describe how you tested these changes -->

## Environment Variables
<!-- List any new environment variables required, or write "None" -->

## Breaking Changes
<!-- Describe any breaking changes and migration path, or write "None" -->

## Rollback Plan
<!-- Describe how to rollback these changes if needed, or write "N/A" -->

## Related Issues
<!-- Link related issues: Fixes #123, Relates to #456 -->

---

## Reviewer Notes
<!-- Additional context for reviewers -->

### Focus Areas
<!-- Highlight specific areas that need careful review -->

### Questions
<!-- Any open questions or decisions needed -->
