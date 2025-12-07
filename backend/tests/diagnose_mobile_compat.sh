#!/bin/bash

# 手機播放兼容性診斷工具
# 用法: ./diagnose_mobile_compat.sh <output.mp4>

set -e

FILE="${1:-.}"

if [ -z "$FILE" ] || [ ! -f "$FILE" ]; then
	echo "❌ 用法: $0 <video_file.mp4>"
	echo "   或: $0 <directory> (診斷目錄中所有 .mp4 文件)"
	exit 1
fi

# 顏色定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_header() {
	echo -e "\n${BLUE}═══════════════════════════════════════════════════${NC}"
	echo -e "${BLUE}$1${NC}"
	echo -e "${BLUE}═══════════════════════════════════════════════════${NC}\n"
}

check_pass() {
	echo -e "${GREEN}✓ $1${NC}"
}

check_fail() {
	echo -e "${RED}✗ $1${NC}"
}

check_warn() {
	echo -e "${YELLOW}⚠ $1${NC}"
}

diagnose_file() {
	local video_file="$1"

	print_header "診斷: $(basename "$video_file")"

	# 1. 容器格式
	print_header "1️⃣ 容器格式檢查"

	format=$(ffprobe -show_format "$video_file" 2>/dev/null | grep format_name | cut -d= -f2)
	if [[ "$format" == "mov,mp4,m4a,3gp,3g2,mj2" ]]; then
		check_pass "容器格式: MP4 ✓"
	else
		check_fail "容器格式: $format (應為 MP4)"
	fi

	# 檢查 faststart
	if ffmpeg -i "$video_file" 2>&1 | grep -q "faststart"; then
		check_pass "Faststart: 已啟用 ✓"
	else
		check_warn "Faststart: 未啟用 (建議啟用以支持邊下邊播)"
	fi

	# 2. 視訊編碼檢查
	print_header "2️⃣ 視訊編碼檢查"

	video_info=$(ffprobe -select_streams v:0 -show_entries \
		stream=codec_name,codec_profile,codec_level,width,height,r_frame_rate,bit_rate \
		-of csv=p=0 "$video_file" 2>/dev/null)

	IFS=',' read -r codec profile level width height fps bitrate <<<"$video_info"

	echo "編碼器: $codec"
	echo "Profile: $profile"
	echo "Level: $level"
	echo "解析度: ${width}×${height}"
	echo "幀率: $fps"
	echo "位元率: $bitrate"

	# 兼容性檢查
	if [[ "$codec" == "h264" ]]; then
		check_pass "編碼器: H.264 ✓"
	else
		check_fail "編碼器: $codec (不是 H.264)"
	fi

	if [[ "$profile" == "Baseline" ]] || [[ "$profile" == "Main" ]]; then
		check_pass "Profile: $profile ✓"
	else
		check_fail "Profile: $profile (應為 Baseline 或 Main)"
	fi

	if [[ "$level" == "4.0" ]] || [[ "$level" == "4.1" ]] || [[ "$level" == "3.1" ]]; then
		check_pass "Level: $level ✓"
	else
		check_fail "Level: $level (應為 ≤ 4.1)"
	fi

	if [[ "$width" -le 1920 ]]; then
		check_pass "寬度: ${width} ✓"
	else
		check_fail "寬度: ${width} (超過 1920，手機可能無法播放)"
	fi

	if [[ "$height" -le 1080 ]]; then
		check_pass "高度: ${height} ✓"
	else
		check_fail "高度: ${height} (超過 1080，手機可能無法播放)"
	fi

	if [[ "$fps" == "30/1" ]] || [[ "$fps" == "25/1" ]] || [[ "$fps" == "24/1" ]]; then
		check_pass "幀率: $fps ✓"
	else
		check_warn "幀率: $fps (標準值: 24/25/30)"
	fi

	# 3. 音訊編碼檢查
	print_header "3️⃣ 音訊編碼檢查"

	audio_info=$(ffprobe -select_streams a:0 -show_entries \
		stream=codec_name,sample_rate,channels,bit_rate \
		-of csv=p=0 "$video_file" 2>/dev/null)

	if [ -n "$audio_info" ]; then
		IFS=',' read -r audio_codec sample_rate channels audio_bitrate <<<"$audio_info"

		echo "編碼器: $audio_codec"
		echo "採樣率: $sample_rate Hz"
		echo "聲道數: $channels"
		echo "位元率: $audio_bitrate"

		if [[ "$audio_codec" == "aac" ]] || [[ "$audio_codec" == "mp3" ]]; then
			check_pass "編碼器: $audio_codec ✓"
		else
			check_fail "編碼器: $audio_codec (應為 AAC 或 MP3)"
		fi

		if [[ "$sample_rate" == "48000" ]] || [[ "$sample_rate" == "44100" ]]; then
			check_pass "採樣率: $sample_rate Hz ✓"
		else
			check_fail "採樣率: $sample_rate Hz (應為 44100 或 48000)"
		fi

		if [[ "$channels" -le 2 ]]; then
			check_pass "聲道數: $channels ✓"
		else
			check_warn "聲道數: $channels (超過立體聲，手機可能無法正確播放)"
		fi
	else
		check_fail "無音訊軌道"
	fi

	# 4. 元數據檢查
	print_header "4️⃣ 元數據檢查"

	duration=$(ffprobe -show_entries format=duration -of csv=p=0 "$video_file" 2>/dev/null)
	echo "時長: ${duration} 秒"

	if [ -n "$duration" ] && [ "$duration" != "N/A" ]; then
		check_pass "Duration 標籤: 已設置 ✓"
	else
		check_fail "Duration 標籤: 缺失"
	fi

	# 5. 位元率統計
	print_header "5️⃣ 位元率統計"

	# 計算平均位元率
	file_size=$(stat -f%z "$video_file" 2>/dev/null || stat -c%s "$video_file" 2>/dev/null)
	avg_bitrate=$((file_size * 8 / ${duration%.*} / 1000))

	echo "檔案大小: $((file_size / 1024 / 1024)) MB"
	echo "平均位元率: ~${avg_bitrate} kbps"

	if [[ "$avg_bitrate" -lt 30000 ]]; then
		check_pass "位元率: ${avg_bitrate} kbps ✓ (適合手機)"
	else
		check_warn "位元率: ${avg_bitrate} kbps (較高，可能需要降低)"
	fi
}

# 主邏輯
if [ -d "$FILE" ]; then
	echo -e "${YELLOW}掃描目錄: $FILE${NC}\n"

	find "$FILE" -name "*.mp4" -o -name "*.mov" | while read -r video; do
		diagnose_file "$video"
	done
else
	diagnose_file "$FILE"
fi

print_header "診斷完成"
