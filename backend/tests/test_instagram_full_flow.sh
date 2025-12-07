#!/bin/bash
# 完整的 Instagram Reel 下載 + 轉碼測試流程

set -e

OUTPUT_DIR="/tmp/instagram_transcode_test_$(date +%s)"
mkdir -p "$OUTPUT_DIR"

echo "════════════════════════════════════════════════════════════════════════════════"
echo "📱 Instagram Reel 完整下載 + 轉碼測試"
echo "════════════════════════════════════════════════════════════════════════════════"
echo ""
echo "📁 測試目錄: $OUTPUT_DIR"
echo ""

# Instagram URL
INSTAGRAM_URL="https://www.instagram.com/reel/DPthOqAkU3Y/?utm_source=ig_web_copy_link&igsh=NTc4MTIwNjQ2YQ=="

echo "════════════════════════════════════════════════════════════════════════════════"
echo "Step 1: 使用 yt-dlp 從 Instagram 下載"
echo "════════════════════════════════════════════════════════════════════════════════"
echo ""
echo "🔗 URL: $INSTAGRAM_URL"
echo "⏳ 下載中..."
echo ""

# 使用 yt-dlp 下載視訊
if command -v yt-dlp &>/dev/null; then
	# 嘗試下載到 MP4 格式
	yt-dlp \
		-f "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]" \
		-o "$OUTPUT_DIR/downloaded.mp4" \
		"$INSTAGRAM_URL" 2>&1 | tail -10

	DOWNLOAD_PATH="$OUTPUT_DIR/downloaded.mp4"

	if [ -f "$DOWNLOAD_PATH" ]; then
		echo "✅ 下載完成"
		echo "   檔案: $DOWNLOAD_PATH"
		echo "   大小: $(du -h "$DOWNLOAD_PATH" | cut -f1)"
	else
		echo "❌ 下載失敗"
		exit 1
	fi
else
	echo "⚠️ yt-dlp 未安裝，跳過下載步驟"
	exit 1
fi

echo ""
echo "════════════════════════════════════════════════════════════════════════════════"
echo "Step 2: 診斷原始檔案"
echo "════════════════════════════════════════════════════════════════════════════════"
echo ""

if command -v ffprobe &>/dev/null; then
	echo "原始檔案編碼信息:"
	ffprobe -v error -select_streams v:0 \
		-show_entries stream=codec_name,profile,level,width,height,r_frame_rate \
		-of csv=p=0 "$DOWNLOAD_PATH" 2>/dev/null || echo "⚠️ 無法解析檔案"
	echo ""
else
	echo "⚠️ ffprobe 未安裝，跳過診斷"
fi

echo "════════════════════════════════════════════════════════════════════════════════"
echo "Step 3: 使用新的轉碼參數進行轉碼"
echo "════════════════════════════════════════════════════════════════════════════════"
echo ""

TRANSCODED_PATH="$OUTPUT_DIR/transcoded_NEW.mp4"

echo "⏳ 轉碼中..."
echo "   輸入: $(basename $DOWNLOAD_PATH)"
echo "   輸出: $(basename $TRANSCODED_PATH)"
echo ""

ffmpeg -i "$DOWNLOAD_PATH" \
	-c:v libx264 \
	-profile:v baseline \
	-level 4.0 \
	-preset medium \
	-crf 22 \
	-x264opts "vbv-bufsize=31250:vbv-maxrate=25000" \
	-c:a aac -b:a 160k -ac 2 -ar 48000 \
	-movflags +faststart \
	-y "$TRANSCODED_PATH" 2>&1 | grep -E "(frame=|time=|speed=|Duration|100%)" | tail -5

if [ -f "$TRANSCODED_PATH" ]; then
	echo ""
	echo "✅ 轉碼完成"
	echo "   檔案大小: $(du -h "$TRANSCODED_PATH" | cut -f1)"
else
	echo "❌ 轉碼失敗"
	exit 1
fi

echo ""
echo "════════════════════════════════════════════════════════════════════════════════"
echo "Step 4: 驗證轉碼結果的手機兼容性"
echo "════════════════════════════════════════════════════════════════════════════════"
echo ""

if command -v ffprobe &>/dev/null; then
	echo "轉碼後的編碼信息:"
	CODEC_INFO=$(ffprobe -v error -select_streams v:0 \
		-show_entries stream=codec_name,profile,level,width,height,r_frame_rate \
		-of csv=p=0 "$TRANSCODED_PATH" 2>/dev/null)
	echo "  $CODEC_INFO"
	echo ""

	# 驗證關鍵參數
	if echo "$CODEC_INFO" | grep -q "h264"; then
		echo "✅ 視訊編碼: H.264 ✓"
	else
		echo "❌ 視訊編碼: 非 H.264"
	fi

	if echo "$CODEC_INFO" | grep -q -i "baseline"; then
		echo "✅ Profile: Baseline ✓"
	else
		echo "⚠️ Profile: 可能不是 Baseline"
	fi

else
	echo "⚠️ ffprobe 未安裝"
fi

echo ""
echo "════════════════════════════════════════════════════════════════════════════════"
echo "✨ 測試完成!"
echo "════════════════════════════════════════════════════════════════════════════════"
echo ""
echo "📁 檔案位置:"
echo "   原始: $DOWNLOAD_PATH"
echo "   轉碼: $TRANSCODED_PATH"
echo ""
echo "💡 建議:"
echo "   1. 複製轉碼後的檔案到手機進行播放測試"
echo "   2. 驗證系統播放器能否流暢播放"
echo "   3. 測試快進、倒轉等功能"
echo ""
