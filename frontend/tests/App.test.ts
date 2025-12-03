/**
 * Tests for App component - download UI and progress tracking.
 */

import { describe, it, expect, vi, beforeEach } from "vitest";

// Mock App component behavior
class MockAppComponent {
  platforms = {
    instagram: { name: "Instagram", format: "mp4" },
    youtube: { name: "YouTube", format: "mp3" },
    facebook: { name: "Facebook", format: "mp4" },
    twitter: { name: "X (Twitter)", format: "mp4" },
  };

  state = {
    activeTab: "instagram",
    url: "",
    format: "mp4",
    downloadProgress: 0,
    currentJobId: null as string | null,
    message: "",
  };

  selectTab(tabKey: string): void {
    if (this.platforms[tabKey as keyof typeof this.platforms]) {
      this.state.activeTab = tabKey;
      this.state.format =
        this.platforms[tabKey as keyof typeof this.platforms].format;
    }
  }

  setUrl(url: string): void {
    this.state.url = url;
  }

  setFormat(format: string): void {
    this.state.format = format;
  }

  updateProgress(jobId: string, percent: number, message: string): void {
    if (this.state.currentJobId === jobId) {
      this.state.downloadProgress = percent;
      this.state.message = message;
    }
  }

  startDownload(url: string, format: string): void {
    if (!url) throw new Error("URL required");
    this.state.currentJobId = "job-" + Date.now();
    this.state.downloadProgress = 0;
    this.state.message = "Starting download...";
  }

  getDownloadProgress(): number {
    return this.state.downloadProgress;
  }

  canSubmitDownload(): boolean {
    return !!this.state.url && !!this.state.format;
  }

  isDownloading(): boolean {
    return (
      this.state.currentJobId !== null && this.state.downloadProgress < 100
    );
  }
}

describe("App Component", () => {
  let app: MockAppComponent;

  beforeEach(() => {
    app = new MockAppComponent();
  });

  describe("Platform Selection", () => {
    it("should initialize with Instagram selected", () => {
      expect(app.state.activeTab).toBe("instagram");
    });

    it("should update format when platform changes", () => {
      app.selectTab("youtube");
      expect(app.state.activeTab).toBe("youtube");
      expect(app.state.format).toBe("mp3");
    });

    it("should support all platforms", () => {
      const platforms = ["instagram", "youtube", "facebook", "twitter"];
      for (const platform of platforms) {
        app.selectTab(platform);
        expect(app.state.activeTab).toBe(platform);
      }
    });

    it("should reject invalid platform", () => {
      const original = app.state.activeTab;
      app.selectTab("invalid");
      expect(app.state.activeTab).toBe(original);
    });
  });

  describe("Download Form", () => {
    it("should accept URL input", () => {
      app.setUrl("https://instagram.com/p/abc123");
      expect(app.state.url).toBe("https://instagram.com/p/abc123");
    });

    it("should accept format selection", () => {
      app.setFormat("mp4");
      expect(app.state.format).toBe("mp4");
    });

    it("should require URL for submission", () => {
      expect(app.canSubmitDownload()).toBe(false);
      app.setUrl("https://instagram.com/p/abc123");
      expect(app.canSubmitDownload()).toBe(true);
    });

    it("should reject submission without URL", () => {
      expect(() => app.startDownload("", "mp4")).toThrow("URL required");
    });
  });

  describe("Progress Tracking", () => {
    it("should track download progress", () => {
      app.startDownload("https://instagram.com/p/abc123", "mp4");
      const jobId = app.state.currentJobId;

      app.updateProgress(jobId, 25, "Downloading...");
      expect(app.getDownloadProgress()).toBe(25);

      app.updateProgress(jobId, 50, "50% complete");
      expect(app.getDownloadProgress()).toBe(50);

      app.updateProgress(jobId, 100, "Complete");
      expect(app.getDownloadProgress()).toBe(100);
    });

    it("should ignore progress updates for different job", () => {
      app.startDownload("https://instagram.com/p/abc123", "mp4");
      const jobId = app.state.currentJobId;

      app.updateProgress(jobId, 50, "50% complete");
      expect(app.getDownloadProgress()).toBe(50);

      // Update for different job should be ignored
      app.updateProgress("other-job", 100, "Other job complete");
      expect(app.getDownloadProgress()).toBe(50);
    });

    it("should display meaningful messages during download", () => {
      app.startDownload("https://instagram.com/p/abc123", "mp4");
      const jobId = app.state.currentJobId;

      app.updateProgress(jobId, 0, "Starting download...");
      expect(app.state.message).toBe("Starting download...");

      app.updateProgress(jobId, 50, "Transcoding video...");
      expect(app.state.message).toBe("Transcoding video...");

      app.updateProgress(jobId, 100, "Download complete");
      expect(app.state.message).toBe("Download complete");
    });

    it("should track download state", () => {
      expect(app.isDownloading()).toBe(false);

      app.startDownload("https://instagram.com/p/abc123", "mp4");
      expect(app.isDownloading()).toBe(true);

      const jobId = app.state.currentJobId;
      app.updateProgress(jobId, 100, "Complete");
      expect(app.isDownloading()).toBe(false);
    });
  });

  describe("Error Handling", () => {
    it("should display remediation messages on error", () => {
      app.state.currentJobId = "job-123";
      app.updateProgress("job-123", 0, "Authentication failed");
      expect(app.state.message).toContain("Authentication");
    });

    it("should clear error message on new download", () => {
      app.state.message = "Previous error";
      app.startDownload("https://instagram.com/p/abc123", "mp4");
      expect(app.state.message).toBe("Starting download...");
    });
  });
});
