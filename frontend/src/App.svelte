<!--
  Refactored Svelte component based on the new prototype.html design.
  This component integrates the modern UI with the existing Svelte logic for state management and API communication.
-->
<script>
  import { onMount } from "svelte";

  // --- State Management ---
  let activeTab = "instagram"; // Default active tab
  let url = "";
  let title = "";
  let thumbnail = "";
  let message = "";
  let downloadProgress = 0;
  let overlayVisible = false;
  let overlayTitle = "Downloading...";
  let downloadBtnDisabled = false;
  let clearBtnDisabled = false;
  let selectedFormat = "mp4"; // Default format, will be updated by handleTabClick
  let currentJobId = null;
  let downloadFileUrl = null;
  let showDownloadButtons = false;
  let cookie = "";
  let isDark = false;

  // --- Playlist State ---
  let isPlaylist = false;
  let playlistMetadata = null;
  let playlistJobId = null;
  let playlistDownloading = false;
  let playlistProgress = 0;
  let currentVideo = null;
  let completedVideos = 0;
  let totalVideos = 0;
  let downloadDelay = 3; // Default delay between downloads
  let failedVideos = [];
  let selectedVideos = []; // Array of selected video IDs

  // --- Constants ---
  const API_BASE_URL =
    import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8080";

  const cookiePlaceholder = `[{"domain": ".instagram.com", ...}]`;

  const platforms = {
    instagram: {
      name: "Instagram",
      placeholder: "https://www.instagram.com/p/...",
      format: "mp4",
      icon: `<path fill-rule="evenodd" d="M12.315 2c2.43 0 2.784.013 3.808.06 1.064.049 1.791.218 2.427.465a4.902 4.902 0 012.153 2.153c.247.636.416 1.363.465 2.427.048 1.024.06 1.378.06 3.808s-.012 2.784-.06 3.808c-.049 1.064-.218 1.791-.465 2.427a4.902 4.902 0 01-2.153 2.153c-.636.247-1.363.416-2.427.465-1.024.048-1.378.06-3.808.06s-2.784-.012-3.808-.06c-1.064-.049-1.791-.218-2.427-.465a4.902 4.902 0 01-2.153-2.153c-.247-.636-.416-1.363-.465-2.427-.048-1.024-.06-1.378-.06-3.808s.012-2.784.06-3.808c.049-1.064.218-1.791.465-2.427a4.902 4.902 0 012.153-2.153c.636-.247 1.363.416 2.427.465C9.53 2.013 9.884 2 12.315 2zM12 7a5 5 0 100 10 5 5 0 000-10zm0-2a7 7 0 110 14 7 7 0 010-14zm4.5-1.5a1.5 1.5 0 100-3 1.5 1.5 0 000 3z" clip-rule="evenodd"></path>`,
    },
    youtube: {
      name: "YouTube",
      placeholder: "https://www.youtube.com/watch?v=...",
      format: "mp3", // Default to mp3 for youtube
      icon: `<path fill-rule="evenodd" d="M19.812 5.418c.861.23 1.538.907 1.768 1.768C21.998 8.78 22 12 22 12s0 3.22-.42 4.814a2.506 2.506 0 0 1-1.768 1.768c-1.594.42-7.812.42-7.812.42s-6.218 0-7.812-.42a2.506 2.506 0 0 1-1.768-1.768C2 15.22 2 12 2 12s0-3.22.42-4.814a2.506 2.506 0 0 1 1.768-1.768C5.782 5 12 5 12 5s6.218 0 7.812.418ZM15.197 12 10 14.885V9.115L15.197 12Z" clip-rule="evenodd" />`,
    },
    facebook: {
      name: "Facebook",
      placeholder: "https://www.facebook.com/user/videos/...",
      format: "mp4",
      icon: `<path fill-rule="evenodd" d="M22 12c0-5.523-4.477-10-10-10S2 6.477 2 12c0 4.991 3.657 9.128 8.438 9.878v-6.987h-2.54V12h2.54V9.797c0-2.506 1.492-3.89 3.777-3.89 1.094 0 2.238.195 2.238.195v2.46h-1.26c-1.243 0-1.63.771-1.63 1.562V12h2.773l-.443 2.89h-2.33v6.988C18.343 21.128 22 16.991 22 12Z" clip-rule="evenodd" />`,
    },
    threads: {
      name: "Threads",
      placeholder: "https://www.threads.net/@user/post/...",
      format: "mp4",
      icon: `<path d="M11.082 8.533a3.463 3.463 0 1 0 3.462 3.462 3.463 3.463 0 0 0-3.462-3.462Zm1.56-4.416a.4.4 0 0 0-.784.175 6.463 6.463 0 0 1-2.924 11.835.4.4 0 0 0 .19.762 7.265 7.265 0 0 0 10.11-2.223.4.4 0 0 0-.583-.583 6.466 6.466 0 0 1-6.009-9.966Z M18.91 15.48a3.463 3.463 0 1 0-3.463-3.463 3.463 3.463 0 0 0 3.463 3.463Zm-1.561 4.415a.4.4 0 0 0 .784-.175 6.463 6.463 0 0 1 2.924-11.835.4.4 0 0 0-.19-.762 7.265 7.265 0 0 0-10.11 2.223.4.4 0 0 0 .583.583 6.466 6.466 0 0 1 6.009 9.966Z" />`,
    },
  };

  // --- Lifecycle ---
  onMount(() => {
    // Initialize theme based on user preference
    if (
      localStorage.getItem("theme") === "dark" ||
      (!("theme" in localStorage) &&
        window.matchMedia("(prefers-color-scheme: dark)").matches)
    ) {
      document.documentElement.classList.add("dark");
      isDark = true;
    } else {
      document.documentElement.classList.remove("dark");
      isDark = false;
    }
  });

  // --- Functions ---
  function toggleTheme() {
    isDark = document.documentElement.classList.toggle("dark");
    localStorage.setItem("theme", isDark ? "dark" : "light");
  }

  function handleTabClick(tabKey) {
    if (activeTab === tabKey) return;
    activeTab = tabKey;
    selectedFormat = platforms[tabKey].format;
    handleClear(); // Clear all fields when switching tabs
  }

  function handleClear() {
    url = "";
    title = "";
    thumbnail = "";
    message = "";
    cookie = "";
    downloadProgress = 0;
    overlayVisible = false;
    downloadBtnDisabled = false;
    clearBtnDisabled = false;
    currentJobId = null;
    showDownloadButtons = false;
    downloadFileUrl = null;
    // Clear playlist state
    isPlaylist = false;
    playlistMetadata = null;
    playlistJobId = null;
    playlistDownloading = false;
    playlistProgress = 0;
    currentVideo = null;
    completedVideos = 0;
    totalVideos = 0;
    failedVideos = [];
    selectedVideos = [];
  }

  // --- Playlist Functions ---
  function isPlaylistUrl(urlString) {
    return urlString.includes("list=");
  }

  function toggleVideoSelection(videoId) {
    if (selectedVideos.includes(videoId)) {
      selectedVideos = selectedVideos.filter(id => id !== videoId);
    } else {
      selectedVideos = [...selectedVideos, videoId];
    }
  }

  function toggleSelectAll() {
    if (!playlistMetadata || !playlistMetadata.videos) return;

    if (selectedVideos.length === playlistMetadata.videos.length) {
      // Deselect all
      selectedVideos = [];
    } else {
      // Select all
      selectedVideos = playlistMetadata.videos.map(v => v.id);
    }
  }

  const debounce = (func, delay) => {
    let timeout;
    return (...args) => {
      clearTimeout(timeout);
      timeout = setTimeout(() => func(...args), delay);
    };
  };

  async function handleUrlInputLogic() {
    if (!url.trim()) return;

    message = "";
    title = "";
    thumbnail = "";
    showDownloadButtons = false;
    isPlaylist = false;
    playlistMetadata = null;

    // Check if it's a playlist URL (YouTube only)
    if (activeTab === "youtube" && isPlaylistUrl(url.trim())) {
      isPlaylist = true;
      await fetchPlaylistMetadata();
      return;
    }

    try {
      const response = await fetch(`${API_BASE_URL}/metadata`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url: url.trim(), cookie: cookie }),
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
      message = `Error: ${error.message}`;
      title = "";
      thumbnail = "";
    }
  }

  async function fetchPlaylistMetadata() {
    try {
      const response = await fetch(`${API_BASE_URL}/playlist/metadata`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url: url.trim(), cookie: cookie }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || "Failed to fetch playlist metadata.");
      }

      const data = await response.json();
      playlistMetadata = data;
      title = data.title || "";
      thumbnail = data.thumbnail || "";

      // Auto-select all videos by default
      if (data.videos && data.videos.length > 0) {
        selectedVideos = data.videos.map(v => v.id);
      }
    } catch (error) {
      console.error("Error fetching playlist metadata:", error);
      message = `Error: ${error.message}`;
      isPlaylist = false;
      playlistMetadata = null;
      selectedVideos = [];
    }
  }

  async function downloadPlaylist() {
    if (!url.trim() || !isPlaylist) return;

    // Check if any videos are selected
    if (selectedVideos.length === 0) {
      message = "Error: 請至少選擇一個視頻";
      return;
    }

    downloadBtnDisabled = true;
    clearBtnDisabled = true;
    message = "";
    playlistProgress = 0;
    playlistDownloading = true;
    overlayVisible = true;
    overlayTitle = "正在下載播放列表...";
    completedVideos = 0;
    totalVideos = selectedVideos.length; // Use selected count instead of total
    currentVideo = null;
    failedVideos = [];

    try {
      const response = await fetch(`${API_BASE_URL}/playlist/download_start`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          url: url.trim(),
          format: selectedFormat,
          cookie: cookie,
          delay: downloadDelay,
          selected_videos: selectedVideos, // Send selected video IDs
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || "Failed to start playlist download.");
      }

      const data = await response.json();
      playlistJobId = data.job_id;

      // Poll for progress
      const pollInterval = setInterval(async () => {
        try {
          const statusResponse = await fetch(`${API_BASE_URL}/playlist/progress/${playlistJobId}`);
          if (!statusResponse.ok) {
            const errorData = await statusResponse.json();
            throw new Error(errorData.error || "Failed to get playlist progress.");
          }
          const statusData = await statusResponse.json();

          if (statusData.error) {
            message = `Error: ${statusData.error}`;
            clearInterval(pollInterval);
            overlayVisible = false;
            playlistDownloading = false;
            downloadBtnDisabled = false;
            clearBtnDisabled = false;
            return;
          }

          completedVideos = statusData.completed_videos || 0;
          totalVideos = statusData.total_videos || 0;
          currentVideo = statusData.current_video;
          playlistProgress = statusData.overall_progress || 0;
          failedVideos = statusData.failed_videos || [];

          if (currentVideo) {
            overlayTitle = `正在下載: ${currentVideo.title} (${completedVideos + 1}/${totalVideos})`;
          }

          if (statusData.status === "completed") {
            clearInterval(pollInterval);
            overlayVisible = false;
            playlistDownloading = false;

            if (failedVideos.length > 0) {
              message = `下載完成！成功: ${completedVideos}/${totalVideos}，失敗: ${failedVideos.length} 個視頻`;
            } else {
              message = `下載完成！所有 ${totalVideos} 個視頻已打包為 ZIP`;
            }

            // Auto-download ZIP file
            downloadPlaylistZip();

            downloadBtnDisabled = false;
            clearBtnDisabled = false;
          } else if (statusData.status === "error") {
            clearInterval(pollInterval);
            overlayVisible = false;
            playlistDownloading = false;
            message = `Error: ${statusData.message || "播放列表下載失敗"}`;
            downloadBtnDisabled = false;
            clearBtnDisabled = false;
          }
        } catch (error) {
          message = `Error: ${error.message}`;
          clearInterval(pollInterval);
          overlayVisible = false;
          playlistDownloading = false;
          downloadBtnDisabled = false;
          clearBtnDisabled = false;
        }
      }, 2000); // Poll every 2 seconds
    } catch (error) {
      message = `Error: ${error.message}`;
      overlayVisible = false;
      playlistDownloading = false;
      downloadBtnDisabled = false;
      clearBtnDisabled = false;
    }
  }

  function downloadPlaylistZip() {
    if (!playlistJobId) return;
    const zipUrl = `${API_BASE_URL}/playlist/download_file/${playlistJobId}`;
    window.location.href = zipUrl;
  }

  const handleUrlInput = debounce(handleUrlInputLogic, 500);

  async function handleDownload() {
    if (!url.trim()) return;

    downloadBtnDisabled = true;
    clearBtnDisabled = true;
    message = "";
    downloadProgress = 0;
    overlayTitle = "Downloading...";
    overlayVisible = true;
    showDownloadButtons = false;
    downloadFileUrl = null;

    try {
      const response = await fetch(`${API_BASE_URL}/download_start`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          url: url.trim(),
          source: activeTab,
          format: selectedFormat,
          cookie: cookie,
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || "Failed to start download.");
      }

      const data = await response.json();
      const jobId = data.job_id;
      currentJobId = jobId;

      const pollInterval = setInterval(async () => {
        try {
          const statusResponse = await fetch(`${API_BASE_URL}/progress/${jobId}`);
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
          overlayTitle = `${statusData.stage.charAt(0).toUpperCase() + statusData.stage.slice(1)}...`;

          if (statusData.status === "done") {
            clearInterval(pollInterval);
            overlayVisible = false;
            downloadFileUrl = `${API_BASE_URL}/download_file/${jobId}`;
            showDownloadButtons = true;
            message = "Download complete!";
            downloadBtnDisabled = false;
            clearBtnDisabled = false;
          }
        } catch (error) {
          message = `Error: ${error.message}`;
          clearInterval(pollInterval);
          overlayVisible = false;
          downloadBtnDisabled = false;
          clearBtnDisabled = false;
        }
      }, 1000);
    } catch (error) {
      message = `Error: ${error.message}`;
      overlayVisible = false;
      showDownloadButtons = false;
      downloadFileUrl = null;
      downloadBtnDisabled = false;
      clearBtnDisabled = false;
    }
  }
</script>

<div
  class="bg-gray-100 dark:bg-gray-900 flex flex-col items-center justify-center min-h-screen p-4 transition-colors duration-500 font-sans"
>
  <!-- Theme Toggle Button -->
  <div class="absolute top-4 right-4">
    <button
      on:click={toggleTheme}
      class="p-2 rounded-full bg-white dark:bg-gray-800 text-gray-600 dark:text-gray-300 shadow-md hover:bg-gray-100 dark:hover:bg-gray-700 transition"
      aria-label="Toggle theme"
    >
      <svg
        class:hidden={isDark}
        class="w-6 h-6"
        fill="none"
        stroke="currentColor"
        viewBox="0 0 24 24"
        xmlns="http://www.w3.org/2000/svg"
      >
        <path
          stroke-linecap="round"
          stroke-linejoin="round"
          stroke-width="2"
          d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z"
        ></path>
      </svg>
      <svg
        class:hidden={!isDark}
        class="w-6 h-6"
        fill="none"
        stroke="currentColor"
        viewBox="0 0 24 24"
        xmlns="http://www.w3.org/2000/svg"
      >
        <path
          stroke-linecap="round"
          stroke-linejoin="round"
          stroke-width="2"
          d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z"
        ></path>
      </svg>
    </button>
  </div>

  <!-- Main Card -->
  <div
    class="w-full max-w-2xl bg-white/80 dark:bg-gray-800/80 backdrop-blur-xl rounded-2xl shadow-xl overflow-hidden"
  >
    <div class="p-6 sm:p-10">
      <!-- Header -->
      <div class="text-center mb-8">
        <h1 class="text-3xl sm:text-4xl font-bold text-gray-800 dark:text-white">
          MediaGrabber
        </h1>
        <p class="text-gray-500 dark:text-gray-400 mt-2">
          輕鬆下載您喜愛的社群媒體內容
        </p>
      </div>

      <!-- Tabs -->
      <div class="mb-6 border-b border-gray-200 dark:border-gray-700">
        <nav
          class="-mb-px flex space-x-4 sm:space-x-8 overflow-x-auto no-scrollbar"
          aria-label="Tabs"
        >
          {#each Object.entries(platforms) as [key, platform] (key)}
            <button
              on:click={() => handleTabClick(key)}
              class="group inline-flex items-center py-4 px-1 border-b-2 font-semibold text-sm transition-colors duration-200"
              class:tab-active={activeTab === key}
              class:text-gray-500={activeTab !== key}
              class:dark:text-gray-400={activeTab !== key}
              class:hover:text-blue-600={activeTab !== key}
              class:dark:hover:text-blue-400={activeTab !== key}
              class:hover:border-gray-300={activeTab !== key}
              class:dark:hover:border-gray-500={activeTab !== key}
              class:border-transparent={activeTab !== key}
            >
              <svg
                class="w-5 h-5 mr-2"
                fill="currentColor"
                viewBox="0 0 24 24"
                aria-hidden="true"
              >
                {@html platform.icon}
              </svg>
              {platform.name}
            </button>
          {/each}
        </nav>
      </div>

      <!-- Form -->
      <form on:submit|preventDefault={handleDownload}>
        <div class="space-y-6">
          <!-- URL Input -->
          <div>
            <label
              for="url-input"
              class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1"
            >
              {platforms[activeTab].name} URL
            </label>
            <input
              type="url"
              id="url-input"
              class="block w-full px-4 py-3 bg-white/50 dark:bg-gray-700/50 border border-gray-300 dark:border-gray-600 rounded-lg shadow-sm placeholder-gray-400 dark:placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition text-gray-900 dark:text-gray-200"
              required
              bind:value={url}
              on:input={handleUrlInput}
              placeholder={platforms[activeTab].placeholder}
            />
          </div>

          <!-- YouTube Format Selection -->
          {#if activeTab === 'youtube' && !isPlaylist}
            <div>
              <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2 text-center">
                下載格式
              </label>
              <div class="flex justify-center gap-x-2 rounded-lg bg-gray-500/10 dark:bg-gray-900/50 p-1">
                <label for="format-mp3" class="flex-1 text-center cursor-pointer px-3 py-1.5 rounded-md transition-colors text-sm font-semibold"
                  class:bg-white={selectedFormat === 'mp3'}
                  class:dark:bg-gray-700={selectedFormat === 'mp3'}
                  class:shadow-sm={selectedFormat === 'mp3'}
                  class:text-blue-600={selectedFormat === 'mp3'}
                  class:dark:text-white={selectedFormat === 'mp3'}
                  class:text-gray-500={selectedFormat !== 'mp3'}
                  class:dark:text-gray-400={selectedFormat !== 'mp3'}
                >
                  <input type="radio" id="format-mp3" value="mp3" bind:group={selectedFormat} class="hidden">
                  MP3 (音訊)
                </label>
                <label for="format-mp4" class="flex-1 text-center cursor-pointer px-3 py-1.5 rounded-md transition-colors text-sm font-semibold"
                  class:bg-white={selectedFormat === 'mp4'}
                  class:dark:bg-gray-700={selectedFormat === 'mp4'}
                  class:shadow-sm={selectedFormat === 'mp4'}
                  class:text-blue-600={selectedFormat === 'mp4'}
                  class:dark:text-white={selectedFormat === 'mp4'}
                  class:text-gray-500={selectedFormat !== 'mp4'}
                  class:dark:text-gray-400={selectedFormat !== 'mp4'}
                >
                  <input type="radio" id="format-mp4" value="mp4" bind:group={selectedFormat} class="hidden">
                  MP4 (影片)
                </label>
              </div>
            </div>
          {/if}

          <!-- Playlist Information & Options -->
          {#if isPlaylist && playlistMetadata}
            <div class="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4">
              <div class="flex items-center mb-3">
                <svg class="w-5 h-5 text-blue-600 dark:text-blue-400 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-3 7h3m-3 4h3m-6-4h.01M9 16h.01"></path>
                </svg>
                <h3 class="text-lg font-semibold text-blue-900 dark:text-blue-100">播放列表</h3>
              </div>

              <p class="text-sm text-gray-700 dark:text-gray-300 mb-2">
                <span class="font-medium">標題:</span> {playlistMetadata.title}
              </p>
              <p class="text-sm text-gray-700 dark:text-gray-300 mb-3">
                <span class="font-medium">視頻數量:</span> {playlistMetadata.video_count} 個
              </p>

              <!-- Video Selection List -->
              {#if playlistMetadata.videos && playlistMetadata.videos.length > 0}
                <div class="mb-3">
                  <div class="flex items-center justify-between mb-2">
                    <p class="text-sm font-medium text-gray-700 dark:text-gray-300">
                      選擇視頻 ({selectedVideos.length} / {playlistMetadata.videos.length})
                    </p>
                    <button
                      type="button"
                      on:click={toggleSelectAll}
                      class="text-xs text-blue-600 dark:text-blue-400 hover:underline font-medium"
                    >
                      {selectedVideos.length === playlistMetadata.videos.length ? '取消全選' : '全選'}
                    </button>
                  </div>
                  <div class="max-h-48 overflow-y-auto border border-gray-200 dark:border-gray-700 rounded-md p-2 space-y-1">
                    {#each playlistMetadata.videos as video, index}
                      <label class="flex items-start gap-2 p-2 hover:bg-gray-100 dark:hover:bg-gray-700/50 rounded cursor-pointer transition">
                        <input
                          type="checkbox"
                          checked={selectedVideos.includes(video.id)}
                          on:change={() => toggleVideoSelection(video.id)}
                          class="mt-0.5 w-4 h-4 text-blue-600 bg-white dark:bg-gray-700 border-gray-300 dark:border-gray-600 rounded focus:ring-blue-500 focus:ring-2"
                        />
                        <span class="text-sm text-gray-700 dark:text-gray-300 flex-1 truncate">
                          {index + 1}. {video.title}
                        </span>
                      </label>
                    {/each}
                  </div>
                </div>
              {/if}

              <!-- Download Options -->
              <div class="grid grid-cols-2 gap-3">
                <!-- Format Selection -->
                <div>
                  <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                    下載格式
                  </label>
                  <select bind:value={selectedFormat} class="w-full px-3 py-2 text-sm bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent text-gray-900 dark:text-gray-200">
                    <option value="mp3">MP3 (音訊)</option>
                    <option value="mp4">MP4 (影片)</option>
                  </select>
                </div>

                <!-- Delay Configuration -->
                <div>
                  <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                    下載間隔 (秒)
                  </label>
                  <input type="number" bind:value={downloadDelay} min="1" max="10"
                    class="w-full px-3 py-2 text-sm bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent text-gray-900 dark:text-gray-200">
                </div>
              </div>

              <!-- Warning for Large Playlists -->
              {#if playlistMetadata.video_count > 20}
                <div class="mt-3 p-2 bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded text-sm text-yellow-800 dark:text-yellow-200">
                  ⚠️ 播放列表較大，下載可能需要較長時間。建議設置較長的下載間隔以避免被限流。
                </div>
              {/if}
            </div>
          {/if}

          <!-- Cookie Input -->
          <div>
            <label
              for="cookie-input"
              class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1"
            >
              Cookie (選填)
            </label>
            <textarea
              id="cookie-input"
              rows="3"
              class="block w-full px-4 py-3 bg-white/50 dark:bg-gray-700/50 border border-gray-300 dark:border-gray-600 rounded-lg shadow-sm placeholder-gray-400 dark:placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition text-gray-900 dark:text-gray-200"
              placeholder={cookiePlaceholder}
              bind:value={cookie}
            ></textarea>
          </div>
        </div>

        <!-- Result Display -->
        {#if thumbnail}
          <div class="mt-6 bg-gray-50 dark:bg-gray-700/50 rounded-lg p-4 flex items-center space-x-4">
            <img src={thumbnail} alt="Video Thumbnail" class="w-24 h-24 object-cover rounded-md shadow-md" />
            <h3 class="font-semibold text-gray-800 dark:text-gray-200 text-left">{title}</h3>
          </div>
        {/if}

        <!-- Action Buttons -->
        <div class="mt-8 grid grid-cols-1 sm:grid-cols-2 gap-4">
          <button
            type="button"
            on:click={isPlaylist ? downloadPlaylist : handleDownload}
            class="w-full flex justify-center items-center gap-2 py-3 px-4 border border-transparent rounded-lg shadow-sm text-base font-semibold text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 transition-transform active:scale-95 disabled:opacity-50"
            disabled={downloadBtnDisabled || !url.trim()}
          >
            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"></path></svg>
            {isPlaylist ? '下載播放列表 (ZIP)' : '下載'}
          </button>
          <button
            type="button"
            on:click={handleClear}
            class="w-full flex justify-center items-center gap-2 py-3 px-4 border border-gray-300 dark:border-gray-600 rounded-lg shadow-sm text-base font-semibold text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-700 hover:bg-gray-50 dark:hover:bg-gray-600 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 transition-transform active:scale-95 disabled:opacity-50"
            disabled={clearBtnDisabled}
          >
             <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-4v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"></path></svg>
            清除
          </button>
        </div>
      </form>

       <!-- Message & Download Area -->
      {#if message}
        <div class="mt-6 p-4 rounded-lg text-center {
          (showDownloadButtons || (playlistDownloading === false && completedVideos > 0))
            ? 'bg-green-100 dark:bg-green-900/20 text-green-800 dark:text-green-200'
            : message.toLowerCase().includes('error')
            ? 'bg-red-100 dark:bg-red-900/20 text-red-800 dark:text-red-200'
            : ''
        }">
          <p class="font-medium">{message}</p>

          {#if showDownloadButtons}
            <div class="mt-4 flex items-center justify-center space-x-3">
              <a
                href={downloadFileUrl}
                class="inline-block px-6 py-3 rounded-lg font-bold text-white bg-green-500 hover:bg-green-600 transition duration-300"
                > <i class="fas fa-download mr-2"></i>Download File
              </a>
            </div>
          {/if}

          <!-- Failed Videos List -->
          {#if failedVideos.length > 0}
            <div class="mt-4 p-3 bg-orange-50 dark:bg-orange-900/20 border border-orange-200 dark:border-orange-800 rounded-lg text-left">
              <p class="text-sm font-semibold text-orange-900 dark:text-orange-100 mb-2">
                ⚠️ 下載失敗的視頻 ({failedVideos.length} 個):
              </p>
              <ul class="text-xs text-orange-800 dark:text-orange-200 space-y-1 max-h-32 overflow-y-auto">
                {#each failedVideos as failed}
                  <li class="truncate">
                    {failed.index}. {failed.title} - {failed.error}
                  </li>
                {/each}
              </ul>
            </div>
          {/if}
        </div>
      {/if}

    </div>
  </div>

  <!-- Footer -->
  <footer class="text-center pt-8 pb-4 px-4">
    <p class="text-sm text-gray-500 dark:text-gray-400">
      © 2025 MediaGrabber. All Rights Reserved.
    </p>
  </footer>

  <!-- Progress Overlay -->
  {#if overlayVisible}
    <div
      class="fixed inset-0 bg-black bg-opacity-75 flex items-center justify-center z-50"
    >
      <div
        class="bg-white dark:bg-gray-800 rounded-lg shadow-xl p-8 text-center animate-fade-in max-w-md w-full"
      >
        <h2 class="text-2xl font-semibold text-gray-800 dark:text-white mb-6">
          {overlayTitle}
        </h2>

        <!-- Playlist Progress Details -->
        {#if playlistDownloading}
          <div class="mb-4 text-left">
            <p class="text-sm text-gray-600 dark:text-gray-400 mb-2">
              整體進度: {completedVideos} / {totalVideos} 個視頻
            </p>
            {#if currentVideo}
              <p class="text-sm text-gray-700 dark:text-gray-300 truncate">
                正在下載: {currentVideo.title}
              </p>
              <div class="mt-2 w-full h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
                <div
                  class="h-full bg-green-500 transition-all duration-300"
                  style="width: {currentVideo.progress || 0}%;"
                ></div>
              </div>
              <p class="text-xs text-gray-500 dark:text-gray-400 mt-1">
                當前視頻: {currentVideo.progress || 0}%
              </p>
            {/if}
          </div>
        {/if}

        <!-- Overall Progress Bar -->
        <div class="w-full mb-4">
          <div class="w-full h-3 bg-gray-300 dark:bg-gray-600 rounded-full overflow-hidden">
            <div
              class="h-full bg-blue-500 transition-all duration-500 ease-in-out"
              style="width: {playlistDownloading ? playlistProgress : downloadProgress}%;"
            ></div>
          </div>
        </div>
        <p class="text-lg font-medium text-gray-700 dark:text-gray-200 mt-2">
          {playlistDownloading ? playlistProgress : downloadProgress}%
        </p>
      </div>
    </div>
  {/if}
</div>

<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
  :global(body) {
    font-family: "Inter", sans-serif;
  }
  .no-scrollbar::-webkit-scrollbar {
    display: none;
  }
  .no-scrollbar {
    -ms-overflow-style: none; /* IE and Edge */
    scrollbar-width: none; /* Firefox */
  }
  .tab-active {
    --tw-text-opacity: 1;
    color: rgb(37 99 235 / var(--tw-text-opacity));
    --tw-border-opacity: 1;
    border-color: rgb(37 99 235 / var(--tw-border-opacity));
  }
  :global(.dark) .tab-active {
    --tw-text-opacity: 1;
    color: rgb(96 165 250 / var(--tw-text-opacity));
    --tw-border-opacity: 1;
    border-color: rgb(96 165 250 / var(--tw-border-opacity));
  }
  @keyframes fadeIn {
    from {
      opacity: 0;
    }
    to {
      opacity: 1;
    }
  }
  .animate-fade-in {
    animation: fadeIn 0.5s ease-out forwards;
  }
</style>
