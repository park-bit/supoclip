/**
 * Parse human timestamp input (HH:MM:SS, MM:SS, or seconds) to seconds.
 */
export function parseTimestampToSeconds(value: string | null | undefined): number | null {
  if (!value) return null;
  const text = value.trim();
  if (!text) return null;

  if (!text.includes(":")) {
    const num = Number(text);
    return Number.isFinite(num) && num >= 0 ? num : null;
  }

  const parts = text.split(":");
  if (parts.length === 2) {
    const minutes = Number(parts[0]);
    const seconds = Number(parts[1]);
    if (Number.isFinite(minutes) && Number.isFinite(seconds) && minutes >= 0 && seconds >= 0 && seconds < 60) {
      return minutes * 60 + seconds;
    }
  } else if (parts.length === 3) {
    const hours = Number(parts[0]);
    const minutes = Number(parts[1]);
    const seconds = Number(parts[2]);
    if (
      Number.isFinite(hours) &&
      Number.isFinite(minutes) &&
      Number.isFinite(seconds) &&
      hours >= 0 &&
      minutes >= 0 &&
      minutes < 60 &&
      seconds >= 0 &&
      seconds < 60
    ) {
      return hours * 3600 + minutes * 60 + seconds;
    }
  }

  return null;
}
