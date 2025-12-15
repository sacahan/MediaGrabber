<!--
  Refactored Svelte component based on the new prototype.html design.
  This component integrates the modern UI with the existing Svelte logic for state management and API communication.
-->
<script lang="ts">
  import { onMount } from "svelte";
  import {
    submitDownload,
    getJobProgress,
    pollJobProgress,
    formatRemediation,
    formatETA,
    formatBytes,
    formatSpeed,
    type ProgressState,
    type RemediationSuggestion,
  } from "./lib/services/downloads";

  // --- Download History Interface ---
  interface DownloadHistoryItem {
    jobId: string;
    title: string;
    url: string;
    format: string;
    platform: string;
    downloadUrl: string;
    fileSize?: number;
    completedAt: number; // timestamp
  }

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
  let isDark = false;

  // --- Download History State ---
  let downloadHistory: DownloadHistoryItem[] = [];
  let showHistory = false;
  const HISTORY_STORAGE_KEY = "mediagrabber_download_history";
  const HISTORY_MAX_AGE_HOURS = 24; // 24 hours

  // --- Progress & Remediation State (T026, T045) ---
  let progressState: ProgressState | null = null;
  let queueDepth = 0;
  let queuePosition = 0;
  let remediation: RemediationSuggestion | null = null;
  let retryAfterSeconds: number | null = null;
  let attemptsRemaining: number | null = null;
  let stopPolling: (() => void) | null = null;

  // --- Playlist State ---
  let isPlaylist = false;
  let playlistJobId = null;
  let playlistDownloading = false;
  let playlistProgress = 0;
  let currentVideo = null;
  let completedVideos = 0;
  let totalVideos = 0;

  // --- Threads Cookies State ---
  let threadsCookies = "";
  let threadsCookiesError = "";
  let downloadDelay = 3; // Default delay between downloads
  let failedVideos = [];

  // --- Constants ---
  const API_BASE_URL =
    import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8080";

  const platforms = {
    instagram: {
      name: "Instagram",
      placeholder: "https://www.instagram.com/p/...",
      format: "mp4",
      icon: `<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path fill-rule="evenodd" d="M12.315 2c2.43 0 2.784.013 3.808.06 1.064.049 1.791.218 2.427.465a4.902 4.902 0 012.153 2.153c.247.636.416 1.363.465 2.427.048 1.024.06 1.378.06 3.808s-.012 2.784-.06 3.808c-.049 1.064-.218 1.791-.465 2.427a4.902 4.902 0 01-2.153 2.153c-.636.247-1.363.416-2.427.465-1.024.048-1.378.06-3.808.06s-2.784-.012-3.808-.06c-1.064-.049-1.791-.218-2.427-.465a4.902 4.902 0 01-2.153-2.153c-.247-.636-.416-1.363-.465-2.427-.048-1.024-.06-1.378-.06-3.808s.012-2.784.06-3.808c.049-1.064.218-1.791.465-2.427a4.902 4.902 0 012.153-2.153c.636-.247 1.363.416 2.427.465C9.53 2.013 9.884 2 12.315 2zM12 7a5 5 0 100 10 5 5 0 000-10zm0-2a7 7 0 110 14 7 7 0 010-14zm4.5-1.5a1.5 1.5 0 100-3 1.5 1.5 0 000 3z" clip-rule="evenodd"/></svg>`,
    },
    threads: {
      name: "Threads",
      placeholder: "https://www.threads.net/@user/post/...",
      format: "mp4",
      requiresCookies: true,
      icon: `<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path d="M12.186 24h-.007c-3.581-.024-6.334-1.205-8.184-3.509C2.35 18.44 1.5 15.586 1.472 12.01v-.017c.03-3.579.879-6.43 2.525-8.482C5.845 1.205 8.6.024 12.18 0h.014c2.746.02 5.043.725 6.826 2.098 1.677 1.29 2.858 3.13 3.509 5.467l-2.04.569c-1.104-3.96-3.898-5.984-8.304-6.015-2.91.022-5.11.936-6.54 2.717C4.307 6.504 3.616 8.914 3.589 12c.027 3.086.718 5.496 2.057 7.164 1.43 1.783 3.631 2.698 6.54 2.717 2.623-.02 4.358-.631 5.8-2.045 1.647-1.613 1.618-3.593 1.09-4.798-.31-.71-.873-1.3-1.634-1.75-.192 1.352-.622 2.446-1.284 3.272-.886 1.102-2.14 1.704-3.73 1.79-1.202.065-2.361-.218-3.259-.801-1.063-.689-1.685-1.74-1.752-2.96-.065-1.182.408-2.256 1.333-3.022.812-.672 1.927-1.073 3.222-1.16 1.009-.068 1.94.019 2.766.204-.058-.702-.322-1.25-.792-1.638-.548-.45-1.378-.678-2.467-.678h-.03c-.915.008-1.66.249-2.216.717l-1.31-1.556c.88-.742 2.039-1.126 3.448-1.142h.043c1.63 0 2.915.419 3.823 1.244.86.782 1.348 1.884 1.452 3.28.218.072.428.155.628.249 1.162.545 2.063 1.36 2.604 2.36.74 1.367.96 3.455-.482 5.87-1.168 1.954-2.987 3.226-5.552 3.887-1.106.286-2.331.431-3.642.431l-.003.001zm-.378-9.025c-1.018.061-1.803.335-2.331.808-.47.42-.674.927-.643 1.503.043.791.469 1.33 1.268 1.601.452.154.976.217 1.525.184 1.083-.057 1.9-.453 2.429-1.177.44-.601.68-1.453.716-2.535-.643-.137-1.32-.207-2.01-.207-.328 0-.651.017-.954.05v-.227z"/></svg>`,
    },
    youtube: {
      name: "YouTube",
      placeholder: "https://www.youtube.com/watch?v=...",
      format: "mp3",
      icon: `<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path fill-rule="evenodd" d="M19.812 5.418c.861.23 1.538.907 1.768 1.768C21.998 8.78 22 12 22 12s0 3.22-.42 4.814a2.506 2.506 0 0 1-1.768 1.768c-1.594.42-7.812.42-7.812.42s-6.218 0-7.812-.42a2.506 2.506 0 0 1-1.768-1.768C2 15.22 2 12 2 12s0-3.22.42-4.814a2.506 2.506 0 0 1 1.768-1.768C5.782 5 12 5 12 5s6.218 0 7.812.418ZM15.197 12 10 14.885V9.115L15.197 12Z" clip-rule="evenodd"/></svg>`,
    },
    facebook: {
      name: "Facebook",
      placeholder: "https://www.facebook.com/user/videos/...",
      format: "mp4",
      icon: `<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path fill-rule="evenodd" d="M22 12c0-5.523-4.477-10-10-10S2 6.477 2 12c0 4.991 3.657 9.128 8.438 9.878v-6.987h-2.54V12h2.54V9.797c0-2.506 1.492-3.89 3.777-3.89 1.094 0 2.238.195 2.238.195v2.46h-1.26c-1.243 0-1.63.771-1.63 1.562V12h2.773l-.443 2.89h-2.33v6.988C18.343 21.128 22 16.991 22 12Z" clip-rule="evenodd"/></svg>`,
    },
    twitter: {
      name: "X (Twitter)",
      placeholder: "https://x.com/user/status/... 或 https://twitter.com/...",
      format: "mp4",
      icon: `<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z"/></svg>`,
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

    // Load download history from localStorage
    loadDownloadHistory();
  });

  // --- Reactive theme update ---
  $: if (typeof document !== "undefined") {
    if (isDark) {
      document.documentElement.classList.add("dark");
      localStorage.setItem("theme", "dark");
    } else {
      document.documentElement.classList.remove("dark");
      localStorage.setItem("theme", "light");
    }
  }

  // --- Download History Functions ---
  function loadDownloadHistory() {
    try {
      const stored = localStorage.getItem(HISTORY_STORAGE_KEY);
      if (stored) {
        const items: DownloadHistoryItem[] = JSON.parse(stored);
        const cutoffTime = Date.now() - HISTORY_MAX_AGE_HOURS * 60 * 60 * 1000;
        downloadHistory = items.filter((item) => item.completedAt > cutoffTime);
        saveDownloadHistory();
      }
    } catch (e) {
      console.error("Failed to load download history:", e);
      downloadHistory = [];
    }
  }

  function saveDownloadHistory() {
    try {
      localStorage.setItem(
        HISTORY_STORAGE_KEY,
        JSON.stringify(downloadHistory)
      );
    } catch (e) {
      console.error("Failed to save download history:", e);
    }
  }

  function addToDownloadHistory(item: DownloadHistoryItem) {
    downloadHistory = [
      item,
      ...downloadHistory.filter((h) => h.jobId !== item.jobId),
    ];
    if (downloadHistory.length > 50) {
      downloadHistory = downloadHistory.slice(0, 50);
    }
    saveDownloadHistory();
  }

  function removeFromHistory(jobId: string) {
    downloadHistory = downloadHistory.filter((item) => item.jobId !== jobId);
    saveDownloadHistory();
  }

  function clearAllHistory() {
    downloadHistory = [];
    saveDownloadHistory();
  }

  function formatFileSize(bytes?: number): string {
    if (!bytes) return "";
    if (bytes < 1024) return bytes + " B";
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + " KB";
    return (bytes / (1024 * 1024)).toFixed(1) + " MB";
  }

  function formatTimeAgo(timestamp: number): string {
    const seconds = Math.floor((Date.now() - timestamp) / 1000);
    if (seconds < 60) return "剛剛";
    const minutes = Math.floor(seconds / 60);
    if (minutes < 60) return `${minutes} 分鐘前`;
    const hours = Math.floor(minutes / 60);
    if (hours < 24) return `${hours} 小時前`;
    return "超過一天";
  }

  function toggleTheme() {
    isDark = !isDark;
    if (isDark) {
      document.documentElement.classList.add("dark");
      localStorage.setItem("theme", "dark");
    } else {
      document.documentElement.classList.remove("dark");
      localStorage.setItem("theme", "light");
    }
  }

  function handleTabClick(tabKey) {
    if (activeTab === tabKey) return;
    activeTab = tabKey;
    selectedFormat = platforms[tabKey].format;
    handleClear();
  }

  function startProgressPolling(jobId) {
    if (stopPolling) stopPolling();

    stopPolling = pollJobProgress(jobId, (progress) => {
      progressState = progress;
      downloadProgress = Math.round(progress.percent);
      queueDepth = progress.queueDepth || 0;
      queuePosition = progress.queuePosition || 0;
      retryAfterSeconds = progress.retryAfterSeconds;
      attemptsRemaining = progress.attemptsRemaining;
      remediation = progress.remediation;

      let msg = progress.message || "";
      if (queueDepth > 0) {
        msg += ` [佇列: ${queuePosition}/${queueDepth}]`;
      }
      if (retryAfterSeconds) {
        msg += ` [${formatETA(retryAfterSeconds)} 後重試]`;
      }
      message = msg;

      if (progress.status === "completed") {
        overlayTitle = "下載完成!";
        downloadBtnDisabled = false;
        clearBtnDisabled = false;

        downloadFileUrl = `${API_BASE_URL}/api/downloads/${jobId}/file`;
        showDownloadButtons = true;

        const historyItem: DownloadHistoryItem = {
          jobId: jobId,
          title:
            progress.message?.replace("下載完成！", "").trim() ||
            url.split("/").pop() ||
            "Downloaded File",
          url: url,
          format: selectedFormat,
          platform: activeTab,
          downloadUrl: downloadFileUrl,
          completedAt: Date.now(),
        };
        addToDownloadHistory(historyItem);

        message = "下載完成！點擊下方按鈕下載檔案";

        setTimeout(() => {
          overlayVisible = false;
          if (stopPolling) {
            stopPolling();
            stopPolling = null;
          }
        }, 1500);
      } else if (progress.status === "failed") {
        overlayTitle = "下載失敗";
        downloadBtnDisabled = false;
        clearBtnDisabled = false;
        setTimeout(() => {
          overlayVisible = false;
          if (stopPolling) {
            stopPolling();
            stopPolling = null;
          }
        }, 2000);
      }
    });
  }

  function handleClear() {
    url = "";
    title = "";
    thumbnail = "";
    message = "";
    downloadProgress = 0;
    overlayVisible = false;
    downloadBtnDisabled = false;
    clearBtnDisabled = false;
    currentJobId = null;
    showDownloadButtons = false;
    downloadFileUrl = null;
    progressState = null;
    queueDepth = 0;
    queuePosition = 0;
    remediation = null;
    retryAfterSeconds = null;
    attemptsRemaining = null;
    if (stopPolling) {
      stopPolling();
      stopPolling = null;
    }
    isPlaylist = false;
    playlistJobId = null;
    playlistDownloading = false;
    playlistProgress = 0;
    currentVideo = null;
    completedVideos = 0;
    totalVideos = 0;
    failedVideos = [];
    // Clear Threads cookies error (keep cookies for convenience)
    threadsCookiesError = "";
  }

  function isPlaylistUrl(urlString) {
    return urlString.includes("list=");
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
    threadsCookiesError = "";

    if (activeTab === "youtube" && isPlaylistUrl(url.trim())) {
      isPlaylist = true;
      title = "YouTube 播放列表";
      return;
    }

    try {
      const urlObj = new URL(url.trim());
      const supportedDomains = [
        "youtube.com",
        "youtu.be",
        "instagram.com",
        "facebook.com",
        "x.com",
        "twitter.com",
        "threads.net",
        "threads.com",
      ];
      const isSupported = supportedDomains.some((domain) =>
        urlObj.hostname.includes(domain)
      );
      if (!isSupported) {
        message =
          "不支援的平台，請輸入 YouTube、Instagram、Facebook、X (Twitter) 或 Threads 的網址";
        return;
      }
      title = "準備下載...";
    } catch (error) {
      message = "請輸入有效的網址";
    }
  }

  async function downloadPlaylist() {
    if (!url.trim() || !isPlaylist) return;

    downloadBtnDisabled = true;
    clearBtnDisabled = true;
    message = "";
    playlistProgress = 0;
    playlistDownloading = true;
    overlayVisible = true;
    overlayTitle = "正在下載播放列表...";
    completedVideos = 0;
    currentVideo = null;
    failedVideos = [];

    try {
      const job = await submitDownload(
        url.trim(),
        selectedFormat as "mp4" | "mp3"
      );
      playlistJobId = job.jobId;

      stopPolling = pollJobProgress(job.jobId, (progress) => {
        progressState = progress;
        playlistProgress = Math.round(progress.percent);
        queueDepth = progress.queueDepth || 0;
        queuePosition = progress.queuePosition || 0;
        retryAfterSeconds = progress.retryAfterSeconds;
        attemptsRemaining = progress.attemptsRemaining;
        remediation = progress.remediation;

        overlayTitle = progress.message || "正在下載播放列表...";

        if (progress.status === "completed") {
          overlayVisible = false;
          playlistDownloading = false;
          message = "下載完成！";
          downloadBtnDisabled = false;
          clearBtnDisabled = false;
          if (stopPolling) stopPolling();
        } else if (progress.status === "failed") {
          overlayVisible = false;
          playlistDownloading = false;
          message = `Error: ${progress.message || "播放列表下載失敗"}`;
          if (remediation) {
            message += ` - ${formatRemediation(remediation)}`;
          }
          downloadBtnDisabled = false;
          clearBtnDisabled = false;
          if (stopPolling) stopPolling();
        }
      });
    } catch (error) {
      message = `Error: ${error.message}`;
      overlayVisible = false;
      playlistDownloading = false;
      downloadBtnDisabled = false;
      clearBtnDisabled = false;
    }
  }

  const handleUrlInput = debounce(handleUrlInputLogic, 500);

  /**
   * Validate Threads cookies format (Netscape cookies.txt format).
   * Returns true if valid, false otherwise.
   */
  function validateThreadsCookies(cookies: string): boolean {
    if (!cookies.trim()) return false;

    // Check for basic Netscape cookies.txt format
    // Each line should have: domain, flag, path, secure, expiration, name, value
    const lines = cookies.trim().split("\n");
    let validLines = 0;

    for (const line of lines) {
      const trimmed = line.trim();
      // Skip comments and empty lines
      if (!trimmed || trimmed.startsWith("#")) continue;

      // Check if line has roughly the right format (tab-separated values)
      const parts = trimmed.split("\t");
      if (parts.length >= 7) {
        validLines++;
      }
    }

    return validLines > 0;
  }

  async function handleDownload() {
    if (!url.trim()) return;

    // Validate Threads cookies if on Threads tab
    // Validate Threads cookies if on Threads tab
    if (activeTab === "threads") {
      // Only validate if cookies are provided (now optional)
      if (threadsCookies.trim()) {
        if (!validateThreadsCookies(threadsCookies)) {
          threadsCookiesError =
            "Cookies 格式無效，請使用 Netscape cookies.txt 格式";
          message = "Cookies 格式無效";
          return;
        }
      }
      threadsCookiesError = "";
    }

    downloadBtnDisabled = true;
    clearBtnDisabled = true;
    message = "";
    downloadProgress = 0;
    overlayTitle = "Downloading...";
    overlayVisible = true;
    showDownloadButtons = false;
    downloadFileUrl = null;

    try {
      // Encode cookies as base64 for Threads downloads
      const cookiesBase64 =
        activeTab === "threads" && threadsCookies.trim()
          ? btoa(unescape(encodeURIComponent(threadsCookies)))
          : undefined;

      const job = await submitDownload(
        url.trim(),
        selectedFormat as "mp4" | "mp3",
        cookiesBase64
      );
      currentJobId = job.jobId;
      startProgressPolling(job.jobId);
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
  class="min-h-screen bg-gray-50 dark:bg-gray-900 text-gray-900 dark:text-gray-100 transition-colors duration-300 font-sans"
>
  <!-- Navbar -->
  <nav
    class="sticky top-0 z-50 backdrop-blur-md bg-white/80 dark:bg-gray-800/80 border-b border-gray-200 dark:border-gray-700 shadow-sm"
  >
    <div class="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8">
      <div class="flex items-center justify-between h-16">
        <div class="flex items-center gap-3">
          <div
            class="w-10 h-10 bg-gradient-to-br from-blue-500 to-purple-600 rounded-xl flex items-center justify-center shadow-lg"
          >
            <svg
              class="w-6 h-6 text-white"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"
              />
            </svg>
          </div>
          <span
            class="text-xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-blue-600 to-purple-600 dark:from-blue-400 dark:to-purple-400"
          >
            MediaGrabber
          </span>
        </div>
        <button
          on:click={toggleTheme}
          class="p-2 rounded-lg bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500"
          aria-label="Toggle Dark Mode"
        >
          {#if isDark}
            <svg
              class="w-5 h-5 text-yellow-400"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z"
              />
            </svg>
          {:else}
            <svg
              class="w-5 h-5 text-gray-600"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z"
              />
            </svg>
          {/if}
        </button>
      </div>
    </div>
  </nav>

  <main class="max-w-4xl mx-auto px-4 py-12 sm:px-6 lg:px-8">
    <!-- Hero Section -->
    <div class="text-center mb-12">
      <h1 class="text-4xl font-extrabold tracking-tight sm:text-5xl mb-4">
        <span class="block text-gray-900 dark:text-white pb-4"
          >下載您喜愛的</span
        >
        <span class="block text-blue-600 dark:text-blue-400">社群媒體影片</span>
      </h1>
      <p
        class="mt-4 max-w-2xl mx-auto text-xl text-gray-500 dark:text-gray-400"
      >
        支援 YouTube, Instagram, Threads, Facebook, X (Twitter) 等平台。
      </p>
    </div>

    <!-- Main Card -->
    <div
      class="bg-white dark:bg-gray-800 rounded-2xl shadow-xl overflow-hidden border border-gray-100 dark:border-gray-700"
    >
      <!-- Platform Tabs -->
      <div
        class="flex overflow-x-auto border-b border-gray-200 dark:border-gray-700 scrollbar-hide"
      >
        {#each Object.entries(platforms) as [key, platform]}
          <button
            class="flex-1 min-w-[60px] py-4 px-3 sm:px-6 text-sm font-medium text-center transition-all duration-200 border-b-2 focus:outline-none flex items-center justify-center gap-2
            {activeTab === key
              ? 'border-blue-500 text-blue-600 dark:text-blue-400 bg-blue-50 dark:bg-blue-900/20'
              : 'border-transparent text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700/50'}"
            on:click={() => handleTabClick(key)}
            title={platform.name}
          >
            <span class="w-5 h-5 [&_svg]:w-full [&_svg]:h-full [&_path]:fill-current">{@html platform.icon}</span>
            <span class="hidden sm:inline">{platform.name}</span>
          </button>
        {/each}
      </div>

      <div class="p-6 sm:p-8 space-y-6">
        <!-- Input Area -->
        <div class="relative">
          <div
            class="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none"
          >
            <svg
              class="h-5 w-5 text-gray-400"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1"
              />
            </svg>
          </div>
          <input
            type="text"
            bind:value={url}
            on:input={handleUrlInput}
            placeholder={platforms[activeTab].placeholder}
            class="block w-full pl-12 pr-4 py-4 bg-gray-50 dark:bg-gray-700 border border-gray-200 dark:border-gray-600 rounded-xl text-gray-900 dark:text-white placeholder-gray-400 focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all text-lg"
          />
        </div>

        <!-- Format Selection (YouTube Only) -->
        {#if activeTab === "youtube"}
          <div
            class="flex items-center gap-4 p-4 bg-gray-50 dark:bg-gray-700/50 rounded-xl border border-gray-100 dark:border-gray-600"
          >
            <span class="text-sm font-medium text-gray-700 dark:text-gray-300"
              >下載格式:</span
            >
            <div class="flex gap-2">
              <label class="inline-flex items-center cursor-pointer">
                <input
                  type="radio"
                  bind:group={selectedFormat}
                  value="mp3"
                  class="form-radio text-blue-600 focus:ring-blue-500 h-4 w-4"
                />
                <span class="ml-2 text-sm text-gray-700 dark:text-gray-300"
                  >MP3 (音訊)</span
                >
              </label>
              <label class="inline-flex items-center cursor-pointer">
                <input
                  type="radio"
                  bind:group={selectedFormat}
                  value="mp4"
                  class="form-radio text-blue-600 focus:ring-blue-500 h-4 w-4"
                />
                <span class="ml-2 text-sm text-gray-700 dark:text-gray-300"
                  >MP4 (影片)</span
                >
              </label>
            </div>
          </div>
        {/if}

        <!-- Threads Cookies Input (Threads Only) -->
        {#if activeTab === "threads"}
          <div
            class="p-4 bg-amber-50 dark:bg-amber-900/20 rounded-xl border border-amber-200 dark:border-amber-700"
          >
            <div class="flex items-start gap-3 mb-3">
              <svg
                class="w-5 h-5 text-amber-500 mt-0.5 flex-shrink-0"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  stroke-width="2"
                  d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
                />
              </svg>
              <div>
                <h4
                  class="text-sm font-semibold text-amber-800 dark:text-amber-200"
                >
                  需要登入認證 (選填)
                </h4>
                <p class="text-sm text-amber-700 dark:text-amber-300 mt-1">
                  若要下載公開貼文可嘗試直接下載。如遇受限內容，請提供登入後的
                  Cookies (Netscape 格式)。
                </p>
                <details
                  class="mt-2 text-xs text-amber-600 dark:text-amber-400"
                >
                  <summary class="cursor-pointer hover:underline"
                    >如何取得 Cookies？</summary
                  >
                  <ol class="mt-2 ml-4 list-decimal space-y-1">
                    <li>安裝瀏覽器擴充套件「Get cookies.txt LOCALLY」</li>
                    <li>
                      登入 <a
                        href="https://www.threads.net"
                        target="_blank"
                        rel="noopener"
                        class="underline">threads.net</a
                      >
                      或
                      <a
                        href="https://www.instagram.com"
                        target="_blank"
                        rel="noopener"
                        class="underline">instagram.com</a
                      >
                    </li>
                    <li>點擊擴充套件圖示，選擇「Export」匯出 cookies</li>
                    <li>將匯出的內容貼上到下方輸入框</li>
                  </ol>
                </details>
              </div>
            </div>
            <div class="relative">
              <textarea
                bind:value={threadsCookies}
                placeholder="# Netscape HTTP Cookie File&#10;.threads.net&#9;TRUE&#9;/&#9;TRUE&#9;0&#9;sessionid&#9;xxxxx..."
                rows="4"
                class="block w-full px-4 py-3 bg-white dark:bg-gray-800 border rounded-lg text-sm font-mono text-gray-900 dark:text-white placeholder-gray-400 focus:ring-2 focus:ring-amber-500 focus:border-transparent transition-all resize-none
                {threadsCookiesError
                  ? 'border-red-500'
                  : 'border-amber-200 dark:border-amber-600'}"
              ></textarea>
              {#if threadsCookies.trim()}
                <button
                  on:click={() => {
                    threadsCookies = "";
                    threadsCookiesError = "";
                  }}
                  class="absolute top-2 right-2 p-1 text-gray-400 hover:text-red-500 transition-colors"
                  aria-label="Clear cookies"
                >
                  <svg
                    class="w-4 h-4"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      stroke-linecap="round"
                      stroke-linejoin="round"
                      stroke-width="2"
                      d="M6 18L18 6M6 6l12 12"
                    />
                  </svg>
                </button>
              {/if}
            </div>
            {#if threadsCookiesError}
              <p
                class="mt-2 text-sm text-red-600 dark:text-red-400 flex items-center gap-1"
              >
                <svg
                  class="w-4 h-4"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    stroke-width="2"
                    d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                  />
                </svg>
                {threadsCookiesError}
              </p>
            {/if}
          </div>
        {/if}

        <!-- Action Buttons -->
        <div class="flex gap-4">
          <button
            on:click={isPlaylist ? downloadPlaylist : handleDownload}
            disabled={downloadBtnDisabled || !url}
            class="flex-1 py-4 px-6 rounded-xl text-white font-semibold text-lg shadow-lg transform transition-all duration-200
            {downloadBtnDisabled || !url
              ? 'bg-gray-400 cursor-not-allowed opacity-70'
              : 'bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 hover:-translate-y-0.5 hover:shadow-xl active:translate-y-0'}"
          >
            {downloadBtnDisabled
              ? "處理中..."
              : isPlaylist
                ? "下載播放列表 (ZIP)"
                : "開始下載"}
          </button>
          <button
            on:click={handleClear}
            disabled={clearBtnDisabled}
            class="px-6 rounded-xl font-medium transition-colors border border-gray-200 dark:border-gray-600
            {clearBtnDisabled
              ? 'text-gray-400 cursor-not-allowed'
              : 'text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700'}"
          >
            清除
          </button>
        </div>

        <!-- Status Messages -->
        {#if message}
          <div
            class="p-4 rounded-xl bg-blue-50 dark:bg-blue-900/20 border border-blue-100 dark:border-blue-800 text-blue-700 dark:text-blue-300 text-center animate-fade-in"
          >
            {message}
          </div>
        {/if}

        <!-- Download Result -->
        {#if showDownloadButtons && downloadFileUrl}
          <div
            class="mt-6 p-6 bg-green-50 dark:bg-green-900/20 rounded-xl border border-green-100 dark:border-green-800 text-center animate-fade-in"
          >
            <h3
              class="text-lg font-semibold text-green-800 dark:text-green-300 mb-4"
            >
              準備就緒！
            </h3>
            <a
              href={downloadFileUrl}
              download
              class="inline-flex items-center justify-center px-8 py-3 border border-transparent text-base font-medium rounded-lg text-white bg-green-600 hover:bg-green-700 md:py-4 md:text-lg md:px-10 transition-colors shadow-md"
            >
              <svg
                class="w-5 h-5 mr-2"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  stroke-width="2"
                  d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"
                />
              </svg>
              下載檔案
            </a>
          </div>
        {/if}
      </div>
    </div>

    <!-- History Section -->
    {#if downloadHistory.length > 0}
      <div class="mt-12">
        <div class="flex items-center justify-between mb-6">
          <h2 class="text-2xl font-bold text-gray-900 dark:text-white">
            最近下載
          </h2>
          <button
            on:click={clearAllHistory}
            class="text-sm text-red-500 hover:text-red-600 dark:text-red-400 dark:hover:text-red-300 font-medium"
          >
            清除記錄
          </button>
        </div>

        <div class="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {#each downloadHistory as item (item.jobId)}
            <div
              class="bg-white dark:bg-gray-800 rounded-xl p-4 shadow-sm border border-gray-100 dark:border-gray-700 hover:shadow-md transition-shadow"
            >
              <div class="flex items-start justify-between mb-2">
                <span
                  class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200"
                >
                  {platforms[item.platform]?.name || item.platform}
                </span>
                <button
                  on:click={() => removeFromHistory(item.jobId)}
                  class="text-gray-400 hover:text-red-500 transition-colors"
                  aria-label="Remove from history"
                >
                  <svg
                    class="w-4 h-4"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      stroke-linecap="round"
                      stroke-linejoin="round"
                      stroke-width="2"
                      d="M6 18L18 6M6 6l12 12"
                    />
                  </svg>
                </button>
              </div>
              <h3
                class="text-sm font-medium text-gray-900 dark:text-white line-clamp-2 mb-2"
                title={item.title}
              >
                {item.title}
              </h3>
              <div
                class="flex items-center justify-between text-xs text-gray-500 dark:text-gray-400 mt-4"
              >
                <span>{formatTimeAgo(item.completedAt)}</span>
                <a
                  href={item.downloadUrl}
                  download
                  class="text-blue-600 dark:text-blue-400 hover:underline font-medium"
                >
                  再次下載
                </a>
              </div>
            </div>
          {/each}
        </div>
      </div>
    {/if}
  </main>

  <!-- Progress Overlay -->
  {#if overlayVisible}
    <div
      class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm transition-opacity"
    >
      <div
        class="bg-white dark:bg-gray-800 rounded-2xl shadow-2xl max-w-md w-full p-6 border border-gray-100 dark:border-gray-700 transform transition-all scale-100"
      >
        <div class="text-center">
          <h3 class="text-xl font-bold text-gray-900 dark:text-white mb-2">
            {overlayTitle}
          </h3>
          <p class="text-sm text-gray-500 dark:text-gray-400 mb-6">{message}</p>

          <!-- Progress Bar -->
          <div class="relative pt-1">
            <div class="flex mb-2 items-center justify-between">
              <div>
                <span
                  class="text-xs font-semibold inline-block py-1 px-2 uppercase rounded-full text-blue-600 bg-blue-200 dark:bg-blue-900 dark:text-blue-200"
                >
                  進度
                </span>
              </div>
              <div class="text-right">
                <span
                  class="text-xs font-semibold inline-block text-blue-600 dark:text-blue-400"
                >
                  {downloadProgress}%
                </span>
              </div>
            </div>
            <div
              class="overflow-hidden h-2 mb-4 text-xs flex rounded bg-blue-200 dark:bg-gray-700"
            >
              <div
                style="width: {downloadProgress}%"
                class="shadow-none flex flex-col text-center whitespace-nowrap text-white justify-center bg-blue-500 transition-all duration-500"
              ></div>
            </div>
          </div>

          {#if remediation}
            <div
              class="mt-4 p-3 bg-yellow-50 dark:bg-yellow-900/20 rounded-lg text-left"
            >
              <p
                class="text-sm text-yellow-800 dark:text-yellow-200 font-medium"
              >
                建議操作:
              </p>
              <p class="text-sm text-yellow-700 dark:text-yellow-300 mt-1">
                {remediation.message}
              </p>
            </div>
          {/if}
        </div>
      </div>
    </div>
  {/if}
</div>

<style>
  .scrollbar-hide::-webkit-scrollbar {
    display: none;
  }
  .scrollbar-hide {
    -ms-overflow-style: none;
    scrollbar-width: none;
  }

  @keyframes fade-in {
    from {
      opacity: 0;
      transform: translateY(10px);
    }
    to {
      opacity: 1;
      transform: translateY(0);
    }
  }
  .animate-fade-in {
    animation: fade-in 0.3s ease-out forwards;
  }
</style>
