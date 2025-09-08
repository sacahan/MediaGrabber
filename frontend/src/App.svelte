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

  // --- Constants ---
  const API_BASE_URL =
    import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8080";

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
              class="block w-full px-4 py-3 bg-white/50 dark:bg-gray-700/50 border border-gray-300 dark:border-gray-600 rounded-lg shadow-sm placeholder-gray-400 dark:placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition"
              required
              bind:value={url}
              on:input={handleUrlInput}
              placeholder={platforms[activeTab].placeholder}
            />
          </div>

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
              class="block w-full px-4 py-3 bg-white/50 dark:bg-gray-700/50 border border-gray-300 dark:border-gray-600 rounded-lg shadow-sm placeholder-gray-400 dark:placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition"
              placeholder='[{"domain": ".instagram.com", ...}]'
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
            type="submit"
            class="w-full flex justify-center items-center gap-2 py-3 px-4 border border-transparent rounded-lg shadow-sm text-base font-semibold text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 transition-transform active:scale-95 disabled:opacity-50"
            disabled={downloadBtnDisabled || !url.trim()}
          >
            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"></path></svg>
            下載
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
        <div class="mt-6 p-4 rounded-lg text-center"
             class:bg-green-100={showDownloadButtons} class:text-green-800={showDownloadButtons}
             class:bg-red-100={message.toLowerCase().includes('error')} class:text-red-800={message.toLowerCase().includes('error')}>
          <p>{message}</p>
          {#if showDownloadButtons}
            <div class="mt-4 flex items-center justify-center space-x-3">
              <a
                href={downloadFileUrl}
                class="inline-block px-6 py-3 rounded-lg font-bold text-white bg-green-500 hover:bg-green-600 transition duration-300"
                > <i class="fas fa-download mr-2"></i>Download File
              </a>
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
        class="bg-white dark:bg-gray-800 rounded-lg shadow-xl p-8 text-center animate-fade-in max-w-sm w-full"
      >
        <h2 class="text-3xl font-semibold text-gray-800 dark:text-white mb-6">
          {overlayTitle}
        </h2>
        <div class="w-full mb-4">
          <div class="w-full h-3 bg-gray-300 dark:bg-gray-600 rounded-full overflow-hidden">
            <div
              class="h-full bg-blue-500 transition-all duration-500 ease-in-out"
              style="width: {downloadProgress}%;"
            ></div>
          </div>
        </div>
        <p class="text-lg font-medium text-gray-700 dark:text-gray-200 mt-2">
          {downloadProgress}%
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
    color: rgb(37 99 235);
    border-color: rgb(37 99 235);
  }
  :global(.dark) .tab-active {
    color: rgb(96 165 250);
    border-color: rgb(96 165 250);
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
