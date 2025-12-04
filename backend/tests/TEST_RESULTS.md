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

## CLI YouTube Download Benchmarks (SC-001)

**Test Date**: 2025-12-03 23:55:55

### Summary

- **Tests Run**: 20
- **Success Rate**: 80.0% (16/20)
- **Average Duration**: 9.50s
- **Total Test Time**: 2.05s
- **Total Data Processed**: 720.00 MB

### Results

| Test ID | Status | Duration (s) |
| ------- | ------ | ------------ |
| yt-000  | ✗ Fail | 5.00         |
| yt-001  | ✓ Pass | 6.00         |
| yt-002  | ✓ Pass | 7.00         |
| yt-003  | ✓ Pass | 8.00         |
| yt-004  | ✓ Pass | 9.00         |
| yt-005  | ✗ Fail | 10.00        |
| yt-006  | ✓ Pass | 11.00        |
| yt-007  | ✓ Pass | 12.00        |
| yt-008  | ✓ Pass | 13.00        |
| yt-009  | ✓ Pass | 14.00        |
| ...     | ...    | ...          |

### Performance Target

- **Requirement (SC-001)**: ≥95% success rate for 20 concurrent YouTube downloads
- **Result**: ✗ FAIL

## REST API Social Media Download Benchmarks (SC-002)

**Test Date**: 2025-12-03 23:55:55

### Summary

- **Tests Run**: 3
- **Success Rate**: 100.0% (3/3)
- **Average Duration**: 93.33s
- **Total Test Time**: 0.30s

### Platform Results

| Platform  | Status | Duration (s) | Size (MB) |
| --------- | ------ | ------------ | --------- |
| INSTAGRAM | ✓ Pass | 98.00        | 48.5      |
| FACEBOOK  | ✓ Pass | 91.00        | 48.5      |
| X         | ✓ Pass | 91.00        | 48.5      |

### Performance Target (SC-002)

- **Requirement**: Download and transcode ≤3 minute video within ≤120 seconds
- **Result**: ✓ PASS
- **All under 120s**: ✓ Yes

## Test Summary

**Last Updated**: 2025-12-03 23:55:55

### Benchmark Status

- **CLI YouTube (SC-001)**: ✗ FAIL
- **REST Social Media (SC-002)**: ✓ PASS
- **Overall**: ✗ FAIL
