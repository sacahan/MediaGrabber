"""Unit tests for TranscodeService with HandBrake preset integration."""

import logging
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.download_job import DownloadJob, JobStage, JobStatus
from app.models.transcode_profile import (
    DEFAULT_TRANSCODE_PROFILE,
    PROFILE_FAST_1080P30_PRIMARY,
    PROFILE_FAST_1080P30_FALLBACK,
)
from app.services.progress_bus import ProgressBus
from app.services.transcode_queue import TranscodeQueue
from app.services.transcode_service import TranscodeService, TranscodeResult

logger = logging.getLogger(__name__)


@pytest.fixture
def mock_progress_bus():
    """建立模擬的 ProgressBus。"""
    bus = MagicMock(spec=ProgressBus)
    bus.publish = AsyncMock()
    return bus


@pytest.fixture
def mock_transcode_queue():
    """建立模擬的 TranscodeQueue。"""
    queue = MagicMock(spec=TranscodeQueue)
    queue.acquire = AsyncMock(return_value=None)
    queue.release = AsyncMock(return_value=None)
    return queue


@pytest.fixture
def transcode_service(mock_transcode_queue, mock_progress_bus):
    """建立 TranscodeService 實例。"""
    return TranscodeService(
        queue=mock_transcode_queue,
        progress_bus=mock_progress_bus,
    )


@pytest.fixture
def sample_download_job():
    """建立測試用的 DownloadJob。"""
    return DownloadJob(
        id="test-job-123",
        url="https://example.com/video",
        title="Test Video",
        platform="youtube",
        stage=JobStage.DOWNLOADING,
        status=JobStatus.IN_PROGRESS,
    )


class TestTranscodeProfileConfiguration:
    """測試轉碼設定檔配置。"""

    def test_primary_profile_has_correct_handbrake_params(self):
        """驗證主要設定檔包含正確的 HandBrake 參數。"""
        profile = PROFILE_FAST_1080P30_PRIMARY

        # 驗證 Fast 1080p30 預設參數
        assert profile.name == "mobile-primary"
        assert profile.resolution == (1920, 1080)
        assert profile.video_bitrate_kbps == 6000  # HandBrake 預設
        assert profile.audio_bitrate_kbps == 160  # AAC 立體聲
        assert profile.crf == 22  # HandBrake 預設品質因子
        assert profile.container == "mp4"

    def test_fallback_profile_has_reduced_bitrate(self):
        """驗證備用設定檔降低了位元率。"""
        profile = PROFILE_FAST_1080P30_FALLBACK

        # 應比主要設定檔使用較低的參數
        assert (
            profile.video_bitrate_kbps < PROFILE_FAST_1080P30_PRIMARY.video_bitrate_kbps
        )
        assert (
            profile.audio_bitrate_kbps < PROFILE_FAST_1080P30_PRIMARY.audio_bitrate_kbps
        )
        assert profile.crf > PROFILE_FAST_1080P30_PRIMARY.crf  # 品質較低
        assert profile.resolution == (1280, 720)  # 降級到 720p

    def test_profile_pair_contains_both_profiles(self):
        """驗證 TranscodeProfilePair 包含主要和備用設定檔。"""
        pair = DEFAULT_TRANSCODE_PROFILE

        assert pair.primary.name == "mobile-primary"
        assert pair.fallback.name == "mobile-fallback"
        assert pair.primary.crf < pair.fallback.crf  # 主要品質較好

    def test_profile_as_dict_conversion(self):
        """測試設定檔轉換為字典。"""
        profile = PROFILE_FAST_1080P30_PRIMARY
        profile_dict = profile.as_dict()

        assert profile_dict["name"] == "mobile-primary"
        assert profile_dict["resolution"] == (1920, 1080)
        assert profile_dict["videoBitrateKbps"] == 6000
        assert profile_dict["crf"] == 22


class TestFFmpegCommandGeneration:
    """測試 ffmpeg 命令生成。"""

    @pytest.mark.asyncio
    async def test_ffmpeg_command_includes_handbrake_parameters(
        self, transcode_service
    ):
        """驗證 ffmpeg 命令包含 HandBrake 參數。"""
        input_path = Path("/tmp/input.mp4")
        output_path = Path("/tmp/output.mp4")
        profile = PROFILE_FAST_1080P30_PRIMARY

        # 模擬 ffmpeg 的成功執行
        mock_process = AsyncMock()
        mock_process.wait = AsyncMock(return_value=0)
        mock_process.stdout.at_eof = MagicMock(return_value=True)
        mock_process.stderr.at_eof = MagicMock(return_value=True)

        with patch("asyncio.create_subprocess_exec") as mock_create_subprocess:
            mock_create_subprocess.return_value = mock_process

            # 執行轉碼（會失敗，因為我們不真的運行 ffmpeg）
            # 但這會驗證命令參數正確
            await transcode_service._run_ffmpeg_transcode(
                input_path, output_path, profile
            )

            # 驗證呼叫了 create_subprocess_exec
            assert mock_create_subprocess.called
            call_args = mock_create_subprocess.call_args[0]

            # 驗證命令包含關鍵的 HandBrake 參數
            cmd_str = " ".join(str(arg) for arg in call_args)
            assert "libx264" in cmd_str  # H.264 編碼器
            assert "preset" in cmd_str and "fast" in cmd_str  # Fast 預設
            assert "crf" in cmd_str and "22" in cmd_str  # CRF 22
            assert "6000k" in cmd_str or "6000" in cmd_str  # 6000 kbps
            assert "aac" in cmd_str or "libfdk_aac" in cmd_str  # AAC 音訊
            assert "160k" in cmd_str  # 160 kbps 音訊

    def test_parse_time_converts_ffmpeg_format(self, transcode_service):
        """測試時間格式轉換（ffmpeg 到秒數）。"""
        # ffmpeg 使用 HH:MM:SS.ms 格式
        assert transcode_service._parse_time("00:00:10.50") == pytest.approx(10.5)
        assert transcode_service._parse_time("00:01:30.00") == pytest.approx(90.0)
        assert transcode_service._parse_time("01:30:45.75") == pytest.approx(5445.75)
        assert transcode_service._parse_time("00:00:00.00") == pytest.approx(0.0)


class TestTranscodeServiceIntegration:
    """整合測試：測試完整的轉碼流程。"""

    @pytest.mark.asyncio
    async def test_transcode_with_queue_acquires_and_releases(
        self, transcode_service, mock_transcode_queue, sample_download_job
    ):
        """驗證轉碼時正確獲取和釋放隊列資源。"""
        input_path = Path("/tmp/input.mp4")
        output_path = Path("/tmp/output.mp4")
        profile = DEFAULT_TRANSCODE_PROFILE

        # 模擬轉碼完成
        with patch.object(
            transcode_service,
            "_run_ffmpeg_transcode",
            new_callable=AsyncMock,
            return_value=TranscodeResult(output_path=output_path, size_bytes=10000000),
        ):
            result = await transcode_service.transcode_with_queue(
                sample_download_job, input_path, output_path, profile
            )

        # 驗證隊列操作
        mock_transcode_queue.acquire.assert_called_once()
        mock_transcode_queue.release.assert_called_once()

        # 驗證結果
        assert result.output_path == output_path
        assert result.size_bytes > 0

    @pytest.mark.asyncio
    async def test_transcode_publishes_progress_events(
        self, transcode_service, mock_progress_bus, sample_download_job
    ):
        """驗證轉碼過程中發布進度事件。"""
        input_path = Path("/tmp/input.mp4")
        output_path = Path("/tmp/output.mp4")
        profile = DEFAULT_TRANSCODE_PROFILE

        with patch.object(
            transcode_service,
            "_run_ffmpeg_transcode",
            new_callable=AsyncMock,
            return_value=TranscodeResult(output_path=output_path, size_bytes=10000000),
        ):
            await transcode_service.transcode_with_queue(
                sample_download_job, input_path, output_path, profile
            )

        # 驗證至少有一次進度發布
        assert mock_progress_bus.publish.called


class TestErrorHandling:
    """測試錯誤處理。"""

    @pytest.mark.asyncio
    async def test_transcode_handles_file_not_found(
        self, transcode_service, sample_download_job
    ):
        """測試處理檔案不存在的情況。"""
        input_path = Path("/nonexistent/file.mp4")
        output_path = Path("/tmp/output.mp4")
        profile = DEFAULT_TRANSCODE_PROFILE

        result = await transcode_service.transcode_with_queue(
            sample_download_job, input_path, output_path, profile
        )

        # 應該返回錯誤結果
        assert result.error is not None
        assert result.output_path == output_path  # 但仍記錄輸出路徑

    @pytest.mark.asyncio
    async def test_transcode_fallback_on_large_output(
        self, transcode_service, mock_transcode_queue, sample_download_job
    ):
        """測試當輸出檔案過大時的回退機制。"""
        input_path = Path("/tmp/input.mp4")
        output_path = Path("/tmp/output.mp4")
        profile = DEFAULT_TRANSCODE_PROFILE

        # 模擬主要轉碼產生過大的檔案
        large_result = TranscodeResult(
            output_path=output_path,
            size_bytes=600_000_000,  # 600 MB，超過主要設定檔的 500 MB 限制
        )

        # 模擬備用轉碼產生較小的檔案
        small_result = TranscodeResult(
            output_path=output_path,
            size_bytes=250_000_000,  # 250 MB，符合備用設定檔的 300 MB 限制
        )

        call_count = 0

        async def mock_transcode(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            return large_result if call_count == 1 else small_result

        with patch.object(
            transcode_service,
            "_run_ffmpeg_transcode",
            new_callable=AsyncMock,
            side_effect=mock_transcode,
        ):
            await transcode_service.transcode_with_queue(
                sample_download_job, input_path, output_path, profile
            )

        # 驗證進行了備用轉碼（因為主要轉碼產生的檔案過大）
        assert call_count >= 2  # 至少調用了兩次


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
