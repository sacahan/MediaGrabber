/**
 * Downloads Service - Handles all API communication for download operations.
 *
 * Provides methods for submitting downloads, polling progress, and retrieving
 * job status. Integrates with retry policies and remediation suggestions.
 */

export interface DownloadJob {
  jobId: string;
  status: "pending" | "downloading" | "transcoding" | "completed" | "failed";
  stage?: string;
  url: string;
  format: "mp4" | "mp3";
  percent?: number;
  message?: string;
  error?: string;
  downloadUrl?: string;
  isPlaylist?: boolean;
  playlistItems?: PlaylistItem[];
}

export interface PlaylistItem {
  id: string;
  title: string;
  status: "pending" | "downloading" | "completed" | "failed";
  downloadedBytes?: number;
  totalBytes?: number;
  error?: string;
}

export interface ProgressState {
  jobId: string;
  status: "pending" | "downloading" | "transcoding" | "completed" | "failed";
  stage: string;
  percent: number;
  downloadedBytes: number;
  totalBytes: number;
  speed: number; // bytes per second
  etaSeconds: number;
  message: string;
  queueDepth: number;
  queuePosition: number;
  retryAfterSeconds?: number;
  attemptsRemaining?: number;
  remediation?: RemediationSuggestion;
}

export interface RemediationSuggestion {
  code: string;
  message: string;
  suggestedAction: string;
  category: "retry" | "user_action" | "system_issue";
}

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8080";

/**
 * Submit a new download job.
 *
 * @param url - Media URL to download
 * @param format - Output format ('mp4' or 'mp3')
 * @param cookiesBase64 - Optional base64-encoded cookies JSON
 * @returns Job object with jobId and initial status
 */
export async function submitDownload(
  url: string,
  format: "mp4" | "mp3",
  cookiesBase64?: string,
): Promise<DownloadJob> {
  const payload: Record<string, unknown> = {
    url,
    format,
  };

  if (cookiesBase64) {
    payload.cookiesBase64 = cookiesBase64;
  }

  const response = await fetch(`${API_BASE_URL}/api/downloads`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(
      error.error || `Failed to submit download: ${response.statusText}`,
    );
  }

  return response.json();
}

/**
 * Get job status and artifacts.
 *
 * @param jobId - Job ID returned from submitDownload
 * @returns Current job status with metadata
 */
export async function getJobStatus(jobId: string): Promise<DownloadJob> {
  const response = await fetch(`${API_BASE_URL}/api/downloads/${jobId}`, {
    method: "GET",
  });

  if (!response.ok) {
    throw new Error(`Failed to get job status: ${response.statusText}`);
  }

  return response.json();
}

/**
 * Poll for job progress updates.
 *
 * Fetches real-time progress including percentage, queue depth,
 * retry state, and remediation suggestions.
 *
 * @param jobId - Job ID to poll
 * @returns Current progress state
 */
export async function getJobProgress(jobId: string): Promise<ProgressState> {
  const response = await fetch(
    `${API_BASE_URL}/api/downloads/${jobId}/progress`,
    {
      method: "GET",
    },
  );

  if (!response.ok) {
    throw new Error(`Failed to get job progress: ${response.statusText}`);
  }

  return response.json();
}

/**
 * Start a long polling loop for job progress.
 *
 * Calls the callback function with each progress update until the job
 * completes or fails.
 *
 * @param jobId - Job ID to monitor
 * @param callback - Function called with each progress update
 * @param pollIntervalMs - How often to poll (default 1000ms)
 * @returns Cleanup function to stop polling
 */
export function pollJobProgress(
  jobId: string,
  callback: (progress: ProgressState) => void,
  pollIntervalMs = 1000,
): () => void {
  let isActive = true;

  async function poll() {
    try {
      const progress = await getJobProgress(jobId);
      if (isActive) {
        callback(progress);

        // Continue polling unless job is complete or failed
        if (progress.status !== "completed" && progress.status !== "failed") {
          setTimeout(poll, pollIntervalMs);
        }
      }
    } catch (error) {
      if (isActive) {
        console.error("Poll error:", error);
        // Retry after error
        setTimeout(poll, pollIntervalMs * 2);
      }
    }
  }

  poll();

  // Return cleanup function
  return () => {
    isActive = false;
  };
}

/**
 * Format remediation suggestion for display.
 *
 * @param remediation - Remediation suggestion object
 * @returns Human-readable message
 */
export function formatRemediation(remediation?: RemediationSuggestion): string {
  if (!remediation) return "";

  return `${remediation.message}\n${remediation.suggestedAction}`;
}

/**
 * Format ETA display.
 *
 * @param etaSeconds - Seconds remaining
 * @returns Human-readable ETA
 */
export function formatETA(etaSeconds: number): string {
  if (etaSeconds < 0) return "calculating...";
  if (etaSeconds < 60) return `${Math.round(etaSeconds)}s`;
  if (etaSeconds < 3600) return `${Math.round(etaSeconds / 60)}m`;
  return `${Math.round(etaSeconds / 3600)}h`;
}

/**
 * Format bytes as human-readable size.
 *
 * @param bytes - Number of bytes
 * @returns Formatted size string
 */
export function formatBytes(bytes: number): string {
  if (bytes === 0) return "0 B";
  const k = 1024;
  const sizes = ["B", "KB", "MB", "GB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return Math.round((bytes / Math.pow(k, i)) * 100) / 100 + " " + sizes[i];
}

/**
 * Format speed as human-readable throughput.
 *
 * @param bytesPerSecond - Bytes per second
 * @returns Formatted speed string
 */
export function formatSpeed(bytesPerSecond: number): string {
  return formatBytes(bytesPerSecond) + "/s";
}
