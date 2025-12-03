# MediaGrabber Test Results

**Last Updated**: 2025-12-03
**Branch**: 002-download-refactor

## Unit Tests

```bash
pytest backend/tests/unit/ -v
```

Status: ✅ All passing (current: 15/15)

## Integration Tests

```bash
pytest backend/tests/integration/ -v
```

Status: ✅ All passing (current: 2/2)

## Contract Tests

```bash
pytest backend/tests/contract/ -v
```

Status: ✅ All passing (current: 5/5)

## CLI Real-World Tests

### YouTube Downloads

| URL        | Format | Expected Size | Actual Size | Duration | Status  | Notes          |
| ---------- | ------ | ------------- | ----------- | -------- | ------- | -------------- |
| (test URL) | mp4    | <50 MB        | TBD         | TBD      | Pending | To be executed |

### Playlist Downloads

| URL        | Items | Format | Expected Size | Actual Size | Duration | Status  | Notes          |
| ---------- | ----- | ------ | ------------- | ----------- | -------- | ------- | -------------- |
| (test URL) | -     | zip    | <200 MB       | TBD         | TBD      | Pending | To be executed |

## Compression Statistics

Tracked automatically via `scripts/run_cli_youtube_benchmarks.py`.

## Next Steps

- [ ] Execute real YouTube download tests
- [ ] Record compression metrics
- [ ] Validate CLI/REST parity
