<script>
  // Svelte 響應式狀態定義
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

  // API 後端 URL。
  const API_BASE_URL = "http://localhost:8080";

  // 響應式變數，用於 URL 輸入框的 placeholder。
  let urlInputPlaceholder = "https://www.youtube.com/watch?v=...";

  // Tailwind CSS 樣式類別定義 (這些類別現在應該由 CDN 提供)
  let activeTabClasses = {
    active: "bg-blue-600 text-white font-semibold px-4 py-2 rounded-md transition duration-300 ease-in-out",
    inactive: "bg-gray-200 text-gray-700 hover:bg-gray-300 px-4 py-2 rounded-md transition duration-300 ease-in-out"
  };

  let buttonClasses = {
    primary: "bg-blue-600 hover:bg-blue-700 text-white font-bold py-3 px-6 rounded-lg w-full transition duration-300",
    secondary: "bg-gray-300 hover:bg-gray-400 text-gray-800 font-bold py-3 px-6 rounded-lg w-full transition duration-300",
    disabled: "opacity-50 cursor-not-allowed"
  };

  let messageClasses = {
    success: "bg-green-100 text-green-800 border border-green-300 p-4 rounded-md",
    error: "bg-red-100 text-red-800 border border-red-300 p-4 rounded-md",
    default: "bg-gray-100 text-gray-800 border border-gray-300 p-4 rounded-md"
  };

  // 根據下載狀態動態設置 message 的 class
  $: currentMessageClasses = message.includes("Error") ? messageClasses.error : (message.includes("Download File") ? messageClasses.success : messageClasses.default);

  /**
   * 處理分頁切換的邏輯。
   * @param {string} tabKey - 被點擊的分頁鍵 (e.g., 'youtube', 'facebook', 'instagram').
   */
  function handleTabClick(tabKey) {
    if (activeTab === tabKey) return;

    activeTab = tabKey;
    url = "";
    title = "";
    thumbnail = "";
    message = "";
    downloadProgress = 0;
    overlayVisible = false;

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

  // 防抖函數
  function debounce(func, delay) {
    let timeout;
    return function (...args) {
      const context = this;
      clearTimeout(timeout);
      timeout = setTimeout(() => func.apply(context, args), delay);
    };
  }

  /**
   * 處理 URL 輸入框的輸入事件，用於獲取影片的 metadata。
   */
  async function handleUrlInputLogic() {
    message = "";
    title = "";
    thumbnail = "";

    const val = url.trim();
    let cleanUrl = val;
    let showMeta = false;

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
        const response = await fetch(`${API_BASE_URL}/metadata`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ url: cleanUrl }),
        });

        if (!response.ok) {
          const errorData = await response.json();
          throw new Error(errorData.error || "Failed to fetch metadata.");
        }

        const data = await response.json();
        title = data.title || "";
        thumbnail = data.thumbnail || "";
      } catch (error) {
        console.error("Error fetching metadata:", error);
        message = `Error fetching metadata: ${error.message}`;
        title = "";
        thumbnail = "";
      }
    }
  }

  const handleUrlInput = debounce(handleUrlInputLogic, 500);

  /**
   * 處理下載按鈕點擊事件。
   */
  async function handleDownload() {
    const rawUrl = url.trim();
    if (!rawUrl) return;

    let sendUrl = rawUrl;
    if (activeTab === "youtube") {
      const m2 = rawUrl.match(/(?:v=|youtu\.be\/|embed\/)([\w-]{11})/);
      if (m2) sendUrl = "https://www.youtube.com/watch?v=" + m2[1];
    }

    downloadBtnDisabled = true;
    clearBtnDisabled = true;
    message = "";
    downloadProgress = 0;
    overlayTitle = "Downloading...";
    overlayVisible = true;

    try {
      const response = await fetch(`${API_BASE_URL}/download_start`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          url: sendUrl,
          source: activeTab,
          format: selectedFormat,
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || "Failed to start download.");
      }

      const data = await response.json();
      const jobId = data.job_id;

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

          if (statusData.error) {
            message = `Error: ${statusData.error}`;
            clearInterval(pollInterval);
            overlayVisible = false;
            downloadBtnDisabled = false;
            clearBtnDisabled = false;
            return;
          }

          downloadProgress = statusData.progress || 0;

          if (statusData.stage === "transcoding") {
            overlayTitle = "Transcoding...";
          } else if (statusData.stage === "downloading") {
            overlayTitle = "Downloading...";
          } else {
            overlayTitle = "Processing...";
          }

          if (statusData.status === "done") {
            clearInterval(pollInterval);
            overlayVisible = false;
            message = ""; 

            const downloadLinkContainer = document.createElement("div");
            downloadLinkContainer.className = "mt-4"; 

            const link = document.createElement("a");
            link.href = `${API_BASE_URL}/download_file/${jobId}`;
            link.className =
              "inline-block px-6 py-3 rounded-lg font-bold text-white bg-green-500 hover:bg-green-600 transition duration-300";
            link.textContent = "Download File";

            downloadLinkContainer.appendChild(link);
            message = downloadLinkContainer.outerHTML;

            downloadBtnDisabled = false;
            clearBtnDisabled = false;
          }
        } catch (error) {
          message = `Download failed: ${error.message}`;
          clearInterval(pollInterval);
          overlayVisible = false;
          downloadBtnDisabled = false;
          clearBtnDisabled = false;
        }
      }, 500);
    } catch (error) {
      message = `Download failed: ${error.message}`;
      overlayVisible = false;
      downloadBtnDisabled = false;
      clearBtnDisabled = false;
    }
  }

  /**
   * 處理清除按鈕點擊事件。
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
    if (activeTab === "youtube") {
      selectedFormat = "mp3";
    }
  }
</script>

<main>
  {#if overlayVisible}
  <div class="fixed inset-0 bg-black bg-opacity-75 flex items-center justify-center z-50">
    <div class="bg-white rounded-lg shadow-xl p-8 text-center animate-fade-in max-w-sm w-full">
      <h2 class="text-3xl font-semibold text-gray-800 mb-6">{overlayTitle}</h2>
      <div class="w-full mb-4">
        <div class="w-full h-3 bg-gray-300 rounded-full overflow-hidden">
          <div
            class="h-full bg-blue-500 transition-all duration-500 ease-in-out"
            style="width: {downloadProgress}%;"
          ></div>
        </div>
      </div>
      <p class="text-lg font-medium text-gray-700 mt-2">{downloadProgress}%</p>
    </div>
  </div>
  {/if}

  <section class="min-h-screen bg-gradient-to-br from-blue-400 to-purple-500 flex items-center justify-center p-4">
    <div class="container mx-auto text-center">
      <h1 class="text-5xl font-bold text-white mb-8">
        MediaGrabber
      </h1>
      <div class="flex justify-center">
        <div class="w-full max-w-md">
          <div class="bg-white rounded-lg shadow-xl p-6">
            <nav class="flex space-x-4 mb-6 justify-center" aria-label="Platform tabs">
              <button
                on:click={() => handleTabClick("youtube")}
                class="{activeTab === 'youtube' ? activeTabClasses.active : activeTabClasses.inactive}"
                role="tab"
                aria-selected={activeTab === "youtube"}
              >
                <i class="fab fa-youtube mr-2"></i> YouTube
              </button>
              <button
                on:click={() => handleTabClick("facebook")}
                class="{activeTab === 'facebook' ? activeTabClasses.active : activeTabClasses.inactive}"
                role="tab"
                aria-selected={activeTab === "facebook"}
              >
                <i class="fab fa-facebook mr-2"></i> Facebook
              </button>
              <button
                on:click={() => handleTabClick("instagram")}
                class="{activeTab === 'instagram' ? activeTabClasses.active : activeTabClasses.inactive}"
                role="tab"
                aria-selected={activeTab === "instagram"}
              >
                <i class="fab fa-instagram mr-2"></i> Instagram
              </button>
            </nav>

            <form on:submit|preventDefault={handleDownload} class="space-y-4">
              <div>
                <label for="url" class="block text-lg font-medium text-gray-700 mb-2">
                  {activeTab.charAt(0).toUpperCase() + activeTab.slice(1)} URL
                </label>
                <div class="relative">
                  <input
                    type="text"
                    id="url"
                    name="url"
                    bind:value={url}
                    on:input={handleUrlInput}
                    placeholder={urlInputPlaceholder}
                    required
                    class="w-full px-4 py-3 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500 shadow-sm text-lg"
                  />
                </div>
              </div>

              {#if activeTab === "youtube"}
                <div>
                  <p class="block text-lg font-medium text-gray-700 mb-2">Download Format</p>
                  <div class="flex items-center space-x-4 justify-center">
                    <label for="format-mp3" class="inline-flex items-center cursor-pointer">
                      <input
                        type="radio"
                        name="format"
                        value="mp3"
                        bind:group={selectedFormat}
                        id="format-mp3"
                        class="form-radio accent-blue-500 h-5 w-5"
                      />
                      <span class="ml-2 text-gray-700">MP3 (Sound)</span>
                    </label>
                    <label for="format-mp4" class="inline-flex items-center cursor-pointer">
                      <input
                        type="radio"
                        name="format"
                        value="mp4"
                        bind:group={selectedFormat}
                        id="format-mp4"
                        class="form-radio accent-blue-500 h-5 w-5"
                      />
                      <span class="ml-2 text-gray-700">MP4 (Video)</span>
                    </label>
                  </div>
                </div>
              {/if}

              {#if thumbnail}
                <figure class="w-full h-48 object-cover rounded-md mb-4 overflow-hidden">
                  <img src={thumbnail} alt="Video Thumbnail" class="w-full h-full object-cover"/>
                </figure>
              {/if}
              {#if title}
                <h2 class="text-2xl font-semibold text-gray-800 text-center mb-4">{title}</h2>
              {/if}

              <div class="grid grid-cols-2 gap-4 flex justify-center">
                <button
                  type="submit"
                  class="{buttonClasses.primary} {downloadBtnDisabled ? buttonClasses.disabled : ''}"
                  disabled={downloadBtnDisabled}
                >
                  Go
                </button>
                <button
                  type="button"
                  on:click={handleClear}
                  class="{buttonClasses.secondary} {clearBtnDisabled ? buttonClasses.disabled : ''}"
                  disabled={clearBtnDisabled}
                >
                  Clear
                </button>
              </div>
            </form>

            {#if message}
              <div class="{currentMessageClasses} mt-5 text-center">
                {@html message}
              </div>
            {/if}
          </div>
        </div>
      </div>
    </div>
  </section>
</main>

<style>
  @keyframes fadeIn {
    from { opacity: 0; }
    to { opacity: 1; }
  }
  .animate-fade-in {
    animation: fadeIn 0.5s ease-out forwards;
  }
  .form-radio {
    appearance: none;
    -webkit-appearance: none;
    border-radius: 9999px;
    border-width: 2px;
    border-color: #9ca3af; /* gray-400 */
    background-color: white;
    transition: background-color 0.2s, border-color 0.2s;
  }
  .form-radio:checked {
    background-color: #3b82f6; /* blue-500 */
    border-color: #3b82f6; /* blue-500 */
  }
  .form-radio:focus {
    outline: none;
    box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.5); /* focus ring */
  }
  .accent-blue-500 {
    accent-color: #3b82f6; /* blue-500 */
  }
</style>
