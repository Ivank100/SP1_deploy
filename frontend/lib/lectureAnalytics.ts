'use client';

import { API_BASE_URL, Lecture, QueryHistoryItem } from '@/lib/api';

export type LectureQuestionFilter = 'all' | 'answered' | 'unanswered' | 'flagged' | 'hidden';
export type LectureQuestionSort = 'newest' | 'oldest' | 'most_repeated';

type HeatmapBin = {
  index: number;
  startPage: number;
  endPage: number;
  count: number;
};

const HEATMAP_BIN_COUNT = 5;

export function detectLectureQueryMode(value: string): 'key_points' | 'default' {
  const normalized = value.toLowerCase();
  return /(key\s*points?|main\s*points?|important\s*points?|key\s*concepts?|main\s*concepts?)/.test(normalized)
    ? 'key_points'
    : 'default';
}

export function formatHistoryTime(value: string) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return date.toLocaleString();
}

export function buildAudioSourceUrl(lecture: Lecture | null) {
  if (!lecture || lecture.file_type !== 'audio') {
    return '';
  }

  const normalizedApiBase = API_BASE_URL.replace(/\/$/, '');
  return `${normalizedApiBase}/${lecture.file_path.replace(/^\/+/, '')}`;
}

export function buildLecturePreviewUrl(lecture: Lecture | null) {
  if (!lecture?.file_path) {
    return '#';
  }

  const normalizedApiBase = API_BASE_URL.replace(/\/$/, '');
  return `${normalizedApiBase}/${lecture.file_path.replace(/^\/+/, '')}`;
}

export function getVisibleHistory(history: QueryHistoryItem[], currentUserEmail?: string | null) {
  if (!currentUserEmail) {
    return history;
  }

  return history.filter((item) => item.user_email === currentUserEmail);
}

export function getChatMessageList(history: QueryHistoryItem[]) {
  return [...history].sort((a, b) => {
    const timeA = a.created_at ? new Date(a.created_at).getTime() : 0;
    const timeB = b.created_at ? new Date(b.created_at).getTime() : 0;
    return timeA - timeB;
  });
}

export function buildQuestionFrequency(history: QueryHistoryItem[]) {
  return history.reduce<Record<string, number>>((acc, item) => {
    const key = item.question.trim().toLowerCase();
    acc[key] = (acc[key] || 0) + 1;
    return acc;
  }, {});
}

export function getFilteredAndSortedHistory(params: {
  history: QueryHistoryItem[];
  filter: LectureQuestionFilter;
  sort: LectureQuestionSort;
  hiddenQuestionIds: Set<number>;
  faqQuestionIds: Set<number>;
  pinnedQuestionIds: Set<number>;
}) {
  const {
    history,
    filter,
    sort,
    hiddenQuestionIds,
    faqQuestionIds,
    pinnedQuestionIds,
  } = params;

  const baseHistory =
    filter === 'hidden'
      ? history
      : history.filter((item) => !hiddenQuestionIds.has(item.id));

  const filteredHistory = baseHistory.filter((item) => {
    if (filter === 'answered') {
      return Boolean(item.answer?.trim());
    }
    if (filter === 'unanswered') {
      return !item.answer?.trim();
    }
    if (filter === 'flagged') {
      return faqQuestionIds.has(item.id);
    }
    if (filter === 'hidden') {
      return hiddenQuestionIds.has(item.id);
    }
    return true;
  });

  const questionFrequency = buildQuestionFrequency(history);

  return [...filteredHistory].sort((a, b) => {
    const pinnedDelta = Number(pinnedQuestionIds.has(b.id)) - Number(pinnedQuestionIds.has(a.id));
    if (pinnedDelta !== 0) {
      return pinnedDelta;
    }

    if (sort === 'most_repeated') {
      const countA = questionFrequency[a.question.trim().toLowerCase()] || 0;
      const countB = questionFrequency[b.question.trim().toLowerCase()] || 0;
      const countDelta = countB - countA;
      if (countDelta !== 0) {
        return countDelta;
      }
    }

    const timeA = a.created_at ? new Date(a.created_at).getTime() : 0;
    const timeB = b.created_at ? new Date(b.created_at).getTime() : 0;
    if (sort === 'oldest') {
      return timeA - timeB;
    }
    return timeB - timeA;
  });
}

export function getHeatmapBins(lecture: Lecture | null, history: QueryHistoryItem[]): HeatmapBin[] {
  if (!lecture || lecture.file_type !== 'pdf' || lecture.page_count <= 0) {
    return [];
  }

  const pageQuestions = history.filter((item) => item.page_number != null);
  if (pageQuestions.length === 0) {
    return [];
  }

  const totalPages = lecture.page_count;
  const binSize = Math.ceil(totalPages / HEATMAP_BIN_COUNT);
  const bins = Array.from({ length: HEATMAP_BIN_COUNT }, (_, i) => {
    const startPage = i * binSize + 1;
    const endPage = Math.min((i + 1) * binSize, totalPages);
    return {
      index: i,
      startPage,
      endPage,
      count: 0,
    };
  });

  for (const q of pageQuestions) {
    const pageNumber = q.page_number ?? 1;
    const binIndex = Math.min(Math.floor((pageNumber - 1) / binSize), HEATMAP_BIN_COUNT - 1);
    bins[binIndex].count += 1;
  }

  return bins;
}

export function formatHeatmapRange(bin: HeatmapBin) {
  return `Pages ${bin.startPage}-${bin.endPage}`;
}

export function getPeakConfusedPages(lecture: Lecture | null, history: QueryHistoryItem[]) {
  const bins = getHeatmapBins(lecture, history);
  if (bins.length === 0) {
    return null;
  }

  const peakValue = Math.max(...bins.map((bin) => bin.count));
  const peakBin = bins.find((bin) => bin.count === peakValue && peakValue > 0);
  return peakBin ? formatHeatmapRange(peakBin) : null;
}
