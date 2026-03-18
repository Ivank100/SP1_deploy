/**
 * This file holds small formatting helpers used across the frontend.
 * It keeps repeated text, date, and display formatting logic out of UI components.
 */
import { CitationSource } from '@/lib/api';

export const formatTimestamp = (seconds?: number | null) => {
  if (seconds == null) return '';
  const total = Math.max(Math.floor(seconds), 0);
  const mins = Math.floor(total / 60);
  const secs = total % 60;
  const hours = Math.floor(mins / 60);
  const minutes = mins % 60;

  if (hours > 0) {
    return `${hours.toString().padStart(2, '0')}:${minutes
      .toString()
      .padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  }

  return `${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
};

export const describeSource = (source: CitationSource) => {
  if (source.page_number != null) {
    const label = source.file_type === 'slides' ? 'slide' : 'page';
    return `${label} ${source.page_number}`;
  }

  const start = formatTimestamp(source.timestamp_start ?? undefined);
  const end = formatTimestamp(source.timestamp_end ?? undefined);

  if (start && end && end !== start) {
    return `${start}-${end}`;
  }

  if (start) {
    return start;
  }

  return '';
};

export const formatDate = (dateString: string) => {
  const date = new Date(dateString);
  const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
  return `${months[date.getMonth()]} ${date.getDate()}, ${date.getFullYear()}`;
};
