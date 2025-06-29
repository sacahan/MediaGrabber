<script>
  // Svelte 響應式狀態定義
  // 使用 `let` 關鍵字聲明的變數在 Svelte 中是響應式的。
  // 當這些變數的值改變時，Svelte 會自動更新 DOM 中所有使用到它們的地方。
  let activeTab = "youtube"; // 當前選中的分頁 (youtube, facebook, instagram)
  let url = ""; // URL 輸入框的值
  let title = ""; // 影片標題
  let thumbnail = ""; // 影片縮圖 URL
  let message = ""; // 顯示給使用者的訊息 (例如錯誤訊息或下載完成提示)
  let downloadProgress = 0; // 下載進度 (0-100)
  let overlayVisible = false; // 控制下載遮罩的顯示/隱藏
  let overlayTitle = "Downloading..."; // 遮罩上顯示的標題 (下載中/轉碼中)
  let downloadBtnDisabled = false; // 控制下載按鈕是否禁用
  let clearBtnDisabled = false; // 控制清除按鈕是否禁用
  let selectedFormat = "mp3"; // YouTube 下載格式 (mp3/mp4)

  // API 後端 URL。確保這裡的 URL 與您的 Flask 後端運行地址一致。
  const API_BASE_URL = "http://localhost:8080";

  // 響應式變數，用於 URL 輸入框的 placeholder。
  // Svelte 會自動追蹤 activeTab 的變化來更新這個變數。
  let urlInputPlaceholder = "https://www.youtube.com/watch?v=...";

  /**
   * 處理分頁切換的邏輯。
   * @param {string} tabKey - 被點擊的分頁鍵 (e.g., 'youtube', 'facebook', 'instagram').
   */
  function handleTabClick(tabKey) {
    // 如果點擊的是當前已激活的分頁，則不做任何操作。
    if (activeTab === tabKey) return;

    // 更新 activeTab 狀態，Svelte 會自動更新相關的 class。
    activeTab = tabKey;

    // 重置表單和訊息狀態，為新分頁做準備。
    url = "";
    title = "";
    thumbnail = "";
    message = "";
    downloadProgress = 0;
    overlayVisible = false;

    // 根據新的 activeTab 更新 URL 輸入框的 placeholder 和預設下載格式。
    if (tabKey === "youtube") {
      urlInputPlaceholder = "https://www.youtube.com/watch?v=...";
      selectedFormat = "mp3"; // YouTube 預設 MP3
    } else if (tabKey === "facebook") {
      urlInputPlaceholder = "https://www.facebook.com/...";
      selectedFormat = "mp4"; // Facebook 預設 MP4
    } else {
      urlInputPlaceholder = "https://www.instagram.com/...";
      selectedFormat = "mp4"; // Instagram 預設 MP4
    }
  }

  // 防抖函數：延遲執行一個函數，直到它在指定的時間內沒有被再次調用。
  function debounce(func, delay) {
    let timeout;
    return function (...args) {
      const context = this;
      clearTimeout(timeout);
      timeout = setTimeout(() => func.apply(context, args), delay);
    };
  }

  /**
   * 處理 URL 輸入框的輸入事件，用於獲取影片的 metadata (標題和縮圖)。
   * 該函數是異步的，因為它會發送網絡請求。
   */
  async function handleUrlInputLogic() {
    // 清空之前的訊息和 metadata 顯示。
    message = "";
    title = "";
    thumbnail = "";

    const val = url.trim();
    let cleanUrl = val;
    let showMeta = false;

    // 根據當前選中的分頁，驗證 URL 格式並提取乾淨的 URL。
    // 只有當 URL 格式有效時，才嘗試獲取 metadata。
    if (activeTab === "youtube") {
      const m = val.match(/(?:v=|youtu\.be\/|embed\/)([\w-]{11})/);
      if (m) {
        cleanUrl = "https://www.youtube.com/watch?v=" + m[1];
        showMeta = true;
      }
    } else if (activeTab === "facebook") {
      if (val.includes("facebook.com") || val.includes("fb.watch")) {
        showMeta = true;
      }
    } else if (activeTab === "instagram") {
      if (val.includes("instagram.com")) {
        showMeta = true;
      }
    }

    if (showMeta) {
      try {
        // 向後端 /metadata API 發送 POST 請求。
        const response = await fetch(`${API_BASE_URL}/metadata`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ url: cleanUrl }),
        });

        // 檢查 HTTP 響應是否成功 (狀態碼 2xx)。
        if (!response.ok) {
          // 如果響應不成功，嘗試解析錯誤訊息並拋出異常。
          const errorData = await response.json();
          throw new Error(errorData.error || "Failed to fetch metadata.");
        }

        // 解析 JSON 響應。
        const data = await response.json();
        // 更新 Svelte 狀態變數，Svelte 會自動更新 DOM。
        title = data.title || "";
        thumbnail = data.thumbnail || "";
      } catch (error) {
        // 捕獲網絡錯誤或後端返回的錯誤。
        console.error("Error fetching metadata:", error);
        message = `Error fetching metadata: ${error.message}`;
        title = ""; // 清空標題和縮圖，因為獲取失敗。
        thumbnail = "";
      }
    }
  }

  // 將 handleUrlInputLogic 包裝在防抖函數中，並將其賦值給 handleUrlInput
  const handleUrlInput = debounce(handleUrlInputLogic, 500);

  /**
   * 處理下載按鈕點擊事件，啟動下載流程。
   * 該函數是異步的，因為它會發送網絡請求並輪詢進度。
   */
  async function handleDownload() {
    const rawUrl = url.trim();
    if (!rawUrl) return; // 如果 URL 為空，則不做任何操作。

    let sendUrl = rawUrl;
    // 對 YouTube URL 進行清理，確保格式一致。
    if (activeTab === "youtube") {
      const m2 = rawUrl.match(/(?:v=|youtu\.be\/|embed\/)([\w-]{11})/);
      if (m2) sendUrl = "https://www.youtube.com/watch?v=" + m2[1];
    }

    // 禁用按鈕並顯示遮罩，防止使用者在下載過程中進行其他操作。
    downloadBtnDisabled = true;
    clearBtnDisabled = true;
    message = ""; // 清空之前的訊息。
    downloadProgress = 0; // 重置進度條。
    overlayTitle = "Downloading..."; // 設置遮罩初始標題。
    overlayVisible = true; // 顯示遮罩。

    try {
      // 向後端 /download_start API 發送 POST 請求，啟動下載任務。
      const response = await fetch(`${API_BASE_URL}/download_start`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          url: sendUrl,
          source: activeTab,
          format: selectedFormat, // 使用 Svelte 綁定的 selectedFormat
        }),
      });

      // 檢查 HTTP 響應是否成功。
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || "Failed to start download.");
      }

      // 解析響應，獲取 job_id。
      const data = await response.json();
      const jobId = data.job_id;

      // 每 500 毫秒輪詢後端 /progress API，獲取下載進度。
      const pollInterval = setInterval(async () => {
        try {
          const statusResponse = await fetch(
            `${API_BASE_URL}/progress/${jobId}`
          );
          if (!statusResponse.ok) {
            const errorData = await statusResponse.json();
            throw new Error(errorData.error || "Failed to get progress.");
          }
          const statusData = await statusResponse.json();

          // 如果後端返回錯誤，則顯示錯誤訊息並停止輪詢。
          if (statusData.error) {
            message = `Error: ${statusData.error}`;
            clearInterval(pollInterval);
            overlayVisible = false; // 隱藏遮罩。
            downloadBtnDisabled = false; // 啟用按鈕。
            clearBtnDisabled = false;
            return;
          }

          // 更新進度條的值。
          downloadProgress = statusData.progress || 0;

          // 根據後端回報的 'stage' 更新遮罩上的文字。
          if (statusData.stage === "transcoding") {
            overlayTitle = "Transcoding...";
          } else if (statusData.stage === "downloading") {
            overlayTitle = "Downloading...";
          } else {
            overlayTitle = "Processing..."; // 預設或排隊狀態
          }

          // 如果下載完成，則停止輪詢，隱藏遮罩，並顯示下載連結。
          if (statusData.status === "done") {
            clearInterval(pollInterval);
            overlayVisible = false;
            message = ""; // 清空之前的訊息。

            // 創建一個 div 作為下載連結按鈕的容器。
            const downloadLinkContainer = document.createElement("div");
            downloadLinkContainer.className = "mt-4"; // 添加一些頂部間距。

            // 創建下載連結按鈕。
            const link = document.createElement("a");
            link.href = `${API_BASE_URL}/download_file/${jobId}`;
            // 應用 Tailwind CSS 類別，使其看起來像一個綠色按鈕。
            link.className =
              "button is-success is-large";
            link.textContent = "Download File";

            // 將按鈕添加到容器中，再將容器添加到訊息區域。
            downloadLinkContainer.appendChild(link);
            // 使用 Svelte 的響應式特性，直接更新 message 變數的 HTML 內容。
            // 注意：直接賦值 HTML 字符串可能存在 XSS 風險，但在這裡用於內部生成的 HTML 是可接受的。
            message = downloadLinkContainer.outerHTML;

            downloadBtnDisabled = false; // 啟用按鈕。
            clearBtnDisabled = false;
          }
        } catch (error) {
          // 捕獲輪詢過程中的網絡錯誤或後端錯誤。
          message = `Download failed: ${error.message}`;
          clearInterval(pollInterval);
          overlayVisible = false;
          downloadBtnDisabled = false;
          clearBtnDisabled = false;
        }
      }, 500); // 每 500 毫秒輪詢一次。
    } catch (error) {
      // 捕獲啟動下載請求時的網絡錯誤或後端錯誤。
      message = `Download failed: ${error.message}`;
      overlayVisible = false;
      downloadBtnDisabled = false;
      clearBtnDisabled = false;
    }
  }

  /**
   * 處理清除按鈕點擊事件，重置表單和 UI 狀態。
   */
  function handleClear() {
    url = "";
    title = "";
    thumbnail = "";
    message = "";
    downloadProgress = 0;
    overlayVisible = false;
    downloadBtnDisabled = false;
    clearBtnDisabled = false;
    // 如果當前是 YouTube 分頁，重置格式選擇為 MP3。
    if (activeTab === "youtube") {
      selectedFormat = "mp3";
    }
  }
</script>

<main>
  <!-- Overlay (下載遮罩) -->
  {#if overlayVisible}
  <div class="modal is-active">
    <div class="modal-background"></div>
    <div class="modal-content box has-text-centered animate-fade-in">
      <!-- 遮罩標題，根據下載階段動態更新 -->
      <h2 class="title is-3 has-text-grey-dark mb-4">{overlayTitle}</h2>
      <div class="has-text-centered">
        <!-- 進度條，value 綁定到 downloadProgress 變數 -->
        <progress class="progress is-primary is-large" value={downloadProgress} max="100"></progress>
        <!-- 進度文字，顯示百分比 -->
        <p class="has-text-grey-dark is-size-6 has-text-weight-medium">{downloadProgress}%</p>
      </div>
    </div>
  </div>
  {/if}

  <!-- 主要內容區域 -->
  <section class="hero is-fullheight is-primary is-light">
    <div class="hero-body">
      <div class="container has-text-centered">
        <!-- 頁面標題 -->
        <h1 class="title is-1 has-text-grey-dark">
          MediaGrabber
        </h1>
        <!-- 卡片化容器，包含導航和表單 -->
        <div class="columns is-centered">
          <div class="column is-half">
            <div class="box p-5 has-background-white">
          <!-- 分頁導航 -->
        <div class="tabs is-boxed is-fullwidth">
          <nav>
            <ul>
              <!-- YouTube 分頁按鈕 -->
              <li class:is-active={activeTab === "youtube"}>
                <a
                  on:click={() => handleTabClick("youtube")}
                  on:keydown={(e) => { if (e.key === 'Enter' || e.key === ' ') handleTabClick('youtube'); }}
                  role="tab"
                  aria-selected={activeTab === "youtube"}
                  tabindex="0"
                >
                  YouTube
                </a>
              </li>
              <!-- Facebook 分頁按鈕 -->
              <li class:is-active={activeTab === "facebook"}>
                <a
                  on:click={() => handleTabClick("facebook")}
                  on:keydown={(e) => { if (e.key === 'Enter' || e.key === ' ') handleTabClick('facebook'); }}
                  role="tab"
                  aria-selected={activeTab === "facebook"}
                  tabindex="0"
                >
                  Facebook
                </a>
              </li>
              <!-- Instagram 分頁按鈕 -->
              <li class:is-active={activeTab === "instagram"}>
                <a
                  on:click={() => handleTabClick("instagram")}
                  on:keydown={(e) => { if (e.key === 'Enter' || e.key === ' ') handleTabClick('instagram'); }}
                  role="tab"
                  aria-selected={activeTab === "instagram"}
                  tabindex="0"
                >
                  Instagram
                </a>
              </li>
            </ul>
          </nav>
        </div>
        <!-- 下載表單 -->
        <!-- on:submit|preventDefault 阻止表單的默認提交行為 -->
        <form on:submit|preventDefault={handleDownload} class="mt-5">
          <div class="field">
            <!-- URL 輸入框的 Label，動態顯示平台名稱 -->
            <label
              for="url"
              class="label"
            >
              {activeTab.charAt(0).toUpperCase() + activeTab.slice(1)} URL
            </label>
            <!-- URL 輸入框，bind:value 實現雙向綁定 -->
            <div class="control">
              <input
                type="text"
                id="url"
                name="url"
                bind:value={url}
                on:input={handleUrlInput}
                placeholder={urlInputPlaceholder}
                required
                class="input is-large"
              />
            </div>
          </div>
          <!-- 格式選擇容器，只在 YouTube 分頁顯示 -->
          {#if activeTab === "youtube"}
            <div class="field">
              <label class="label">Download Format</label>
              <div class="control">
                <label class="radio" for="format-mp3">
                  <input
                    type="radio"
                    name="format"
                    value="mp3"
                    bind:group={selectedFormat}
                    id="format-mp3"
                  />
                  MP3 (Sound)
                </label>
                <label class="radio" for="format-mp4">
                  <input
                    type="radio"
                    name="format"
                    value="mp4"
                    bind:group={selectedFormat}
                    id="format-mp4"
                  />
                  MP4 (Video)
                </label>
              </div>
            </div>
          {/if}
          <!-- 縮圖容器，只有當 thumbnail 變數有值時才顯示 -->
          {#if thumbnail}
            <figure class="image is-16by9 mb-5">
              <img
                src={thumbnail}
                alt="Video Thumbnail"
              />
            </figure>
          {/if}
          <!-- 標題容器，只有當 title 變數有值時才顯示 -->
          {#if title}
            <h2 class="title is-4 has-text-centered mb-5">{title}</h2>
          {/if}
          <!-- 下載按鈕 -->
          <!-- 綁定到 downloadBtnDisabled 變數 -->
          <div class="field is-grouped is-grouped-centered">
            <p class="control">
              <button
                type="submit"
                class="button is-primary is-large is-fullwidth"
                disabled={downloadBtnDisabled}
              >
                Go
              </button>
            </p>
            <p class="control">
              <button
                type="button"
                class="button is-light is-large is-fullwidth"
                on:click={handleClear}
                disabled={clearBtnDisabled}
              >
                Clear
              </button>
            </p>
          </div>
        </form>
        <!-- 訊息顯示區域 -->
        <!-- {@html message} 用於渲染包含 HTML 內容的字符串 -->
        <div class="notification is-light is-primary mt-5 has-background-white">
          {@html message}
        </div>
      </div>
    </div>
  </div>
</div>
</section>
</main>
