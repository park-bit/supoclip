import { ApiRequestError, parseApiError } from "@/lib/api-error";

export const EXPORT_PRESETS = [
  { id: "tiktok", label: "TikTok", width: 1080, height: 1920, bitrate: 10_000_000 },
  { id: "reels", label: "Reels", width: 1080, height: 1920, bitrate: 12_000_000 },
  { id: "shorts", label: "Shorts", width: 1080, height: 1920, bitrate: 10_000_000 },
] as const;

export function getClipUrl(videoUrl: string, version?: string) {
  const url = videoUrl.startsWith("/api/") ? videoUrl : `/api${videoUrl}`;
  return version ? `${url}${url.includes("?") ? "&" : "?"}v=${encodeURIComponent(version)}` : url;
}

export async function requestAction(url: string, method: string, body?: unknown) {
  const response = await fetch(url, {
    method,
    ...(body === undefined ? {} : {
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }),
  });
  if (!response.ok) {
    throw new ApiRequestError(await parseApiError(response, "Could not save changes. Please try again."));
  }
  return response;
}

export function downloadBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  // Give the browser time to begin the download before releasing the URL.
  window.setTimeout(() => URL.revokeObjectURL(url), 30_000);
}

export interface DriveSaveResult {
  success: boolean;
  file_id: string;
  name: string;
  web_view_link: string;
}

export function sanitizeTitleForFilename(title: string | null | undefined, maxChars = 150): string {
  if (!title) return "video";
  let cleaned = title.trim();
  if (cleaned.toLowerCase().endsWith(".mp4")) {
    cleaned = cleaned.slice(0, -4).trim();
  }
  // Replace path or separator characters with a dash
  cleaned = cleaned.replace(/[/\\|:]/g, " - ");
  // Remove filesystem-illegal characters and control characters
  cleaned = cleaned.replace(/[\x00-\x1f\x7f*?"<>~#%&{}`@!$+=]/g, "");
  // Collapse multiple spaces or dashes
  cleaned = cleaned.replace(/\s+/g, " ");
  cleaned = cleaned.replace(/-{2,}/g, "-");
  cleaned = cleaned.replace(/^[ .-_]+|[ .-_]+$/g, "");
  if (!cleaned) return "video";
  return cleaned.slice(0, maxChars).replace(/[ .-_]+$/, "");
}

export function formatClipFilename(
  videoTitle: string | null | undefined,
  clipNumber: number | string,
  preset?: string | null,
  ext = ".mp4"
): string {
  const cleanTitle = sanitizeTitleForFilename(videoTitle);
  const num = typeof clipNumber === "number" ? clipNumber : (parseInt(String(clipNumber), 10) || 1);
  let base = `${cleanTitle}_${num}`;
  if (preset && preset.toLowerCase() !== "original" && preset.toLowerCase() !== "none") {
    const cleanPreset = preset.toLowerCase().replace(/[^a-z0-9_-]/g, "");
    if (cleanPreset) {
      base = `${base}_${cleanPreset}`;
    }
  }
  const cleanExt = ext.startsWith(".") ? ext : `.${ext}`;
  return `${base}${cleanExt}`;
}

export async function saveClipToDrive(
  taskId: string,
  clipId: string,
  exportId?: string,
): Promise<DriveSaveResult> {
  const url = `/api/tasks/${taskId}/clips/${clipId}/save-to-drive`;
  const response = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(exportId ? { export_id: exportId } : {}),
  });
  if (!response.ok) {
    let message = "Failed to save to Google Drive.";
    try {
      const data = await response.json();
      message = data.detail || data.error || message;
    } catch {
      // ignore
    }
    throw new Error(message);
  }
  return response.json();
}
