---
post_title: Playlist Experience Checklist
author1: sacahan
post_slug: playlist-experience-checklist
microsoft_alias: sacahan
featured_image: https://github.com/user-attachments/assets/99ef6eaf-a6a2-43ef-b922-67d481daf400
categories: ["工具", "多平台", "下載器"]
tags: ["checklist", "playlist", "requirements"]
ai_note: 本文件由 AI 依據規格自動產生
summary: 播放清單使用體驗需求的品質檢查清單，協助作者在進入開發前自我稽核。
post_date: 2025-12-03
---

# Playlist Experience Checklist: Unified Download Pipeline Rebuild

**Purpose**: 播放清單使用體驗的需求品質自查（作者層級）
**Created**: 2025-12-03
**Feature**: [spec.md](../spec.md)

**Note**: 本清單聚焦播放清單提交、進度、輸出與錯誤呈現之需求品質，供功能負責人自我稽核。

## Requirement Completeness

- [x] CHK001 是否已描述 CLI 與 REST 在提交播放清單任務時的必要參數（URL、format、playlistZip 等）及其對等性？ [Completeness, Spec §FR-003, Spec §FR-004]
- [x] CHK002 播放清單 ZIP 內需要包含哪些檔案（個別檔案、任務摘要、壓縮報告）與命名規則是否明確？ [Completeness, Spec §FR-006]
- [x] CHK003 是否交代播放清單任務在成功完成後要回傳哪些欄位（成功/失敗列表、artifact 連結、壓縮比例）？ [Completeness, Spec §FR-006, Spec §FR-013]

## Requirement Clarity

- [x] CHK004 CLI 任務摘要列出成功與失敗項目時，所需欄位（序號、標題、錯誤訊息）是否具體？ [Clarity, Spec §FR-013]
- [x] CHK005 REST `/api/downloads/{jobId}` 回傳的播放清單資料結構是否定義 per-item 狀態與錯誤 remediation？ [Clarity, Spec §FR-013]

## Scenario Coverage

- [x] CHK006 播放清單中若混合音訊與影片，是否定義如何套用 `--format mp3/mp4` 需求與轉換順序？ [Coverage, Spec §FR-014]
- [x] CHK007 部分影片需登入或 cookies 才能下載時，是否描述如何在同一播放清單流程中提示並重試？ [Coverage, Spec §FR-015, Spec §Edge Cases]

## Edge Case Coverage

- [x] CHK008 當播放清單僅成功部分項目時，ZIP 與 API/CLI 應如何標示缺漏與 remediation，是否寫明？ [Edge Case, Spec §Edge Cases, Spec §FR-006, Spec §FR-013]
- [x] CHK009 播放清單任務在排隊等待 ffmpeg 期間，是否定義 `queued`/`waiting` 進度如何顯示給使用者？ [Edge Case, Spec §FR-012, Spec §Edge Cases]

## Non-Functional Requirements

- [x] CHK010 是否針對播放清單的整體完成時間、ZIP 最大檔案大小或並行限制訂出具體 SLA？ [Non-Functional, Gap] ← 已確認此為後續 SLA 追蹤項，暫不需納入本階段實作

## Dependencies & Assumptions

- [x] CHK011 是否明確列出播放清單下載所需的 cookies、proxy 或平台 API 限制，並說明如何於 CLI/REST 提供？ [Dependencies, Spec §FR-015, Spec §Edge Cases]

## Ambiguities & Conflicts

- [x] CHK012 播放清單 ZIP 內容的順序（依原排序或下載完成順序）是否定義，避免 CLI 與 Web 呈現不一致？ [Ambiguity, Spec §FR-006, Spec §Edge Cases]

## Notes

- 勾選 `[x]` 代表已確認需求品質無虞；如發現缺口請於規格補充並回填來源連結。
