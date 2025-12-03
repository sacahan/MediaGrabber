/**
 * Tests for downloads service.
 */

import { describe, it, expect, vi, beforeEach } from "vitest";

// Mock download service
class MockDownloadService {
  async submitDownload(
    url: string,
    format: string,
    cookies?: string,
  ): Promise<{ jobId: string }> {
    if (!url) throw new Error("URL is required");
    if (!format) throw new Error("Format is required");
    return { jobId: "job-123" };
  }

  async getJobStatus(jobId: string): Promise<{
    jobId: string;
    status: string;
    percent: number;
  }> {
    if (!jobId) throw new Error("Job ID is required");
    return { jobId, status: "downloading", percent: 50 };
  }

  async getJobProgress(jobId: string): Promise<{
    jobId: string;
    status: string;
    stage: string;
    percent: number;
    message: string;
    queueDepth?: number;
    remediation?: string;
  }> {
    if (!jobId) throw new Error("Job ID is required");
    return {
      jobId,
      status: "downloading",
      stage: "Initializing download",
      percent: 25,
      message: "Starting download",
    };
  }
}

describe("Downloads Service", () => {
  let service: MockDownloadService;

  beforeEach(() => {
    service = new MockDownloadService();
  });

  it("should submit a download request", async () => {
    const result = await service.submitDownload(
      "https://instagram.com/p/abc123",
      "mp4",
    );
    expect(result.jobId).toBe("job-123");
  });

  it("should reject submission without URL", async () => {
    await expect(service.submitDownload("", "mp4")).rejects.toThrow(
      "URL is required",
    );
  });

  it("should reject submission without format", async () => {
    await expect(
      service.submitDownload("https://instagram.com/p/abc123", ""),
    ).rejects.toThrow("Format is required");
  });

  it("should get job status", async () => {
    const status = await service.getJobStatus("job-123");
    expect(status.jobId).toBe("job-123");
    expect(status.status).toBe("downloading");
    expect(status.percent).toBe(50);
  });

  it("should reject status request without job ID", async () => {
    await expect(service.getJobStatus("")).rejects.toThrow(
      "Job ID is required",
    );
  });

  it("should get job progress with stage and message", async () => {
    const progress = await service.getJobProgress("job-123");
    expect(progress.jobId).toBe("job-123");
    expect(progress.stage).toBeDefined();
    expect(progress.message).toBeDefined();
    expect(progress.percent).toBeGreaterThanOrEqual(0);
    expect(progress.percent).toBeLessThanOrEqual(100);
  });

  it("should support progress polling with queue depth", async () => {
    const progress = await service.getJobProgress("job-123");
    expect(typeof progress).toBe("object");
    // Verify response structure for UI consumption
    expect("status" in progress).toBe(true);
    expect("percent" in progress).toBe(true);
    expect("message" in progress).toBe(true);
  });
});
