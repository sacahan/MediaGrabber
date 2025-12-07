"""輸出管理器：管理 output/{jobId} 下的產出檔案目錄和元資料。

此服務負責：
1. 為每個任務建立獨立的目錄結構
2. 管理產出檔案、暫存檔案和元資料
3. 監控磁碟空間使用狀況
4. 自動清理舊檔案以釋放空間
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any, Iterable, Optional


class OutputManager:
    """輸出管理器：統一管理下載任務的輸出目錄結構。

    每個任務會建立以下目錄結構：
    output/
      {job_id}/
        artifacts/    # 最終的產出檔案
        tmp/          # 暫存檔案
        metadata/     # 元資料檔案

    屬性:
        _root: 輸出檔案的根目錄
    """

    def __init__(self, root_dir: Path) -> None:
        """初始化輸出管理器。

        Args:
            root_dir: 輸出檔案的根目錄路徑
        """
        self._root = root_dir
        self._root.mkdir(parents=True, exist_ok=True)  # 確保根目錄存在

    @property
    def root(self) -> Path:
        """獲取輸出檔案的根目錄。

        Returns:
            根目錄的 Path 物件
        """
        return self._root

    def job_root(self, job_id: str) -> Path:
        """獲取指定任務的根目錄。

        Args:
            job_id: 任務 ID

        Returns:
            任務根目錄的 Path 物件
        """
        return self._root / job_id

    def prepare_job(self, job_id: str) -> Path:
        """為任務準備目錄結構：建立所需的子目錄。

        建立三個子目錄：
        - artifacts: 存放最終的產出檔案
        - tmp: 存放處理過程中的暫存檔案
        - metadata: 存放元資料和報告檔案

        Args:
            job_id: 任務 ID

        Returns:
            任務根目錄的 Path 物件
        """
        job_root = self.job_root(job_id)
        (job_root / "artifacts").mkdir(parents=True, exist_ok=True)
        (job_root / "tmp").mkdir(parents=True, exist_ok=True)
        (job_root / "metadata").mkdir(parents=True, exist_ok=True)
        return job_root

    def artifact_path(self, job_id: str, filename: str) -> Path:
        """獲取產出檔案的完整路徑。

        Args:
            job_id: 任務 ID
            filename: 檔案名稱

        Returns:
            產出檔案的絕對路徑
        """
        return (self.job_root(job_id) / "artifacts" / filename).resolve()

    def temp_path(self, job_id: str, filename: str) -> Path:
        """獲取暫存檔案的完整路徑。

        Args:
            job_id: 任務 ID
            filename: 檔案名稱

        Returns:
            暫存檔案的絕對路徑
        """
        return (self.job_root(job_id) / "tmp" / filename).resolve()

    def metadata_path(self, job_id: str, filename: str) -> Path:
        """獲取元資料檔案的完整路徑。

        Args:
            job_id: 任務 ID
            filename: 檔案名稱

        Returns:
            元資料檔案的絕對路徑
        """
        return (self.job_root(job_id) / "metadata" / filename).resolve()

    def write_metadata(self, job_id: str, filename: str, payload: Any) -> Path:
        path = self.metadata_path(job_id, filename)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
        return path

    def write_compression_report(self, job_id: str, lines: Iterable[str]) -> Path:
        path = self.metadata_path(job_id, "COMPRESSION_REPORT.txt")
        with path.open("w", encoding="utf-8") as handle:
            handle.write("\n".join(lines))
        return path

    def cleanup_job(self, job_id: str) -> None:
        job_root = self.job_root(job_id)
        if job_root.exists():
            shutil.rmtree(job_root, ignore_errors=True)

    def cleanup_all(self) -> None:
        for child in self._root.iterdir():
            if child.is_dir():
                shutil.rmtree(child, ignore_errors=True)

    def list_jobs(self) -> list[Path]:
        return sorted([child for child in self._root.iterdir() if child.is_dir()])

    def oldest_job(self) -> Optional[Path]:
        jobs = self.list_jobs()
        return min(jobs, key=lambda path: path.stat().st_mtime) if jobs else None

    def get_disk_usage(self) -> tuple[int, int]:
        """獲取磁碟使用狀況：返回托管根目錄的檔案系統上的磁碟使用狀況。

        Returns:
            元組 (used_bytes, free_bytes)
            - used_bytes: 已使用的位元組數
            - free_bytes: 可用的位元組數
        """
        stat = shutil.disk_usage(self._root)
        return (stat.total - stat.free, stat.free)

    def ensure_free_space(
        self, required_bytes: int, min_free_bytes: int = 100 * 1024 * 1024
    ) -> tuple[bool, Optional[str]]:
        """確保有足夠的可用空間：如果空間不足，嘗試清理舊任務。

        此方法會檢查可用磁碟空間，如果不足會自動刪除最舊的任務目錄，
        直到有足夠的空間或無法釋放更多空間為止。

        Args:
            required_bytes: 新任務所需的空間（位元組）
            min_free_bytes: 需要維持的最小可用空間（預設 100 MB）

        Returns:
            元組 (success, remediation_message)
            - success: 是否成功確保足夠空間
            - remediation_message: 如果失敗，提供補救建議
        """
        used, free = self.get_disk_usage()
        total_needed = required_bytes + min_free_bytes

        # 如果現有空間足夠，直接返回成功
        if free >= total_needed:
            return (True, None)

        # 嘗試透過移除最舊的任務來釋放空間
        freed = 0
        while free + freed < total_needed:
            oldest = self.oldest_job()
            if not oldest:
                # 沒有更多可清理的任務，返回失敗
                msg = (
                    f"磁碟空間不足：現有 {free} 位元組，"
                    f"需要 {required_bytes} 位元組。"
                    "請手動清理檔案或增加磁碟空間。"
                )
                return (False, msg)
            # 計算任務目錄的大小
            job_size = sum(f.stat().st_size for f in oldest.rglob("*") if f.is_file())
            # 清理任務目錄
            self.cleanup_job(oldest.name)
            freed += job_size

        return (True, None)  # 成功釋放足夠的空間
