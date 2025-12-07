#!/bin/bash

# 快速轉碼參數對比工具
# 用法: ./test_transcode_profiles.sh input.mp4 output_dir

INPUT="${1:-test.mp4}"
OUTPUT_DIR="${2:-.}"

if [ ! -f "$INPUT" ]; then
	echo "❌ 錯誤: 找不到輸入文件 '$INPUT'"
	exit 1
fi

mkdir -p "$OUTPUT_DIR"

echo "════════════════════════════════════════════════════════════════"
echo "開始對比不同轉碼參數的手機兼容性"
echo "輸入: $INPUT"
echo "輸出目錄: $OUTPUT_DIR"
echo "════════════════════════════════════════════════════════════════"

# Profile 1: 最大兼容性 (Baseline)
echo ""
echo "📌 Profile 1: 最大兼容性 (Baseline)"
echo "   特點: 最廣泛的手機支持，檔案較大"
ffmpeg -i "$INPUT" \
	-c:v libx264 \
	-profile:v baseline \
	-level 4.0 \
	-preset medium \
	-crf 23 \
	-x264opts "nal-hrd=cbr:vbv-maxrate=25000:vbv-bufsize=31250" \
	-c:a aac -b:a 160k -ac 2 -ar 48000 \
	-movflags +faststart \
	-y "$OUTPUT_DIR/output_baseline.mp4"
echo "✓ 已生成: output_baseline.mp4"

# Profile 2: 當前設定 (Main)
echo ""
echo "📌 Profile 2: 當前設定 (Main + 簡化參數)"
echo "   特點: 平衡兼容性和檔案大小"
ffmpeg -i "$INPUT" \
	-c:v libx264 \
	-profile:v main \
	-level 4.0 \
	-preset fast \
	-crf 22 \
	-x264opts "level=4.0:vbv-bufsize=31250:vbv-maxrate=25000" \
	-c:a aac -b:a 160k -ac 2 -ar 48000 \
	-movflags +faststart \
	-y "$OUTPUT_DIR/output_main.mp4"
echo "✓ 已生成: output_main.mp4"

# Profile 3: 高兼容性 720p
echo ""
echo "📌 Profile 3: 高兼容性 720p"
echo "   特點: 舊手機友好，檔案最小"
ffmpeg -i "$INPUT" \
	-c:v libx264 \
	-profile:v main \
	-level 4.0 \
	-preset fast \
	-crf 23 \
	-vf "scale=1280:720:force_original_aspect_ratio=decrease,pad=1280:720:(ow-iw)/2:(oh-ih)/2" \
	-x264opts "level=4.0:vbv-bufsize=15625:vbv-maxrate=12500" \
	-c:a aac -b:a 128k -ac 2 -ar 48000 \
	-movflags +faststart \
	-y "$OUTPUT_DIR/output_720p.mp4"
echo "✓ 已生成: output_720p.mp4"

# Profile 4: 超低位元率 (低網速)
echo ""
echo "📌 Profile 4: 超低位元率 (低網速測試)"
echo "   特點: 網速有限環境"
ffmpeg -i "$INPUT" \
	-c:v libx264 \
	-profile:v main \
	-level 4.0 \
	-preset fast \
	-crf 26 \
	-vf "scale=1280:720:force_original_aspect_ratio=decrease" \
	-x264opts "level=4.0:vbv-bufsize=10000:vbv-maxrate=8000" \
	-c:a aac -b:a 96k -ac 2 -ar 44100 \
	-movflags +faststart \
	-y "$OUTPUT_DIR/output_lowbitrate.mp4"
echo "✓ 已生成: output_lowbitrate.mp4"

# 比較統計
echo ""
echo "════════════════════════════════════════════════════════════════"
echo "📊 生成結果對比"
echo "════════════════════════════════════════════════════════════════"
echo ""

for file in "$OUTPUT_DIR"/output_*.mp4; do
	if [ -f "$file" ]; then
		basename=$(basename "$file")
		filesize=$(stat -f%z "$file" 2>/dev/null || stat -c%s "$file" 2>/dev/null)
		filesize_mb=$((filesize / 1024 / 1024))

		duration=$(ffprobe -show_entries format=duration -of csv=p=0 "$file" 2>/dev/null)
		avg_bitrate=$((filesize * 8 / ${duration%.*} / 1000))

		video_codec=$(ffprobe -select_streams v:0 -show_entries stream=codec_name -of csv=p=0 "$file" 2>/dev/null)
		video_profile=$(ffprobe -select_streams v:0 -show_entries stream=profile -of csv=p=0 "$file" 2>/dev/null)
		video_level=$(ffprobe -select_streams v:0 -show_entries stream=level -of csv=p=0 "$file" 2>/dev/null)
		resolution=$(ffprobe -select_streams v:0 -show_entries stream=width,height -of csv=p=0:s=x "$file" 2>/dev/null)

		printf "%-30s | %4d MB | %6d kbps | %-10s | %-8s | %s\n" \
			"$basename" "$filesize_mb" "$avg_bitrate" "$video_profile" "$video_level" "$resolution"
	fi
done

echo ""
echo "════════════════════════════════════════════════════════════════"
echo "✅ 轉碼完成！"
echo ""
echo "建議測試步驟："
echo "1. 複製各個文件到測試手機"
echo "2. 使用不同的播放器測試 (系統播放器、VLC、MXPlayer 等)"
echo "3. 檢查是否能流暢播放、是否有卡頓或花屏"
echo "4. 記錄結果，哪個 Profile 兼容性最好"
echo ""
echo "推薦診斷工具："
echo "  ./diagnose_mobile_compat.sh $OUTPUT_DIR"
echo "════════════════════════════════════════════════════════════════"
