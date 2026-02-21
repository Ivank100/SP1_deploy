'use client';

import { useState, useEffect, useRef, useCallback, useMemo, Dispatch, SetStateAction } from 'react';
import { useParams, useRouter } from 'next/navigation';
import {
  apiClient,
  Lecture,
  QueryResponse,
  QueryHistoryItem,
  StudyMaterialsResponse,
  CitationSource,
  TranscriptSegment,
  API_BASE_URL,
  User,
  LectureAnalyticsResponse,
  LectureResource,
} from '@/lib/api';
import Link from 'next/link';
import Flashcards from '@/components/Flashcards';
import AudioPlayer from '@/components/AudioPlayer';
import SlideViewer, { SlideViewerRef } from '@/components/SlideViewer';

const formatTimestamp = (seconds?: number | null) => {
  if (seconds == null) return null;
  const total = Math.max(Math.floor(seconds), 0);
  const mins = Math.floor(total / 60);
  const secs = total % 60;
  const hours = Math.floor(mins / 60);
  const minutes = mins % 60;
  if (hours > 0) {
    return `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${secs
      .toString()
      .padStart(2, '0')}`;
  }
  return `${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
};

const describeSource = (source: CitationSource) => {
  if (source.page_number != null) {
    const isSlide = source.file_type === 'slides';
    const label = isSlide ? 'slide' : 'page';
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

export default function LecturePage() {
  const params = useParams();
  const router = useRouter();
  const lectureId = parseInt(params.id as string);
  const [lecture, setLecture] = useState<Lecture | null>(null);
  const [currentUser, setCurrentUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [question, setQuestion] = useState('');
  const [asking, setAsking] = useState(false);
  const [currentAnswer, setCurrentAnswer] = useState<QueryResponse | null>(null);
  const [history, setHistory] = useState<QueryHistoryItem[]>([]);
  const [materials, setMaterials] = useState<StudyMaterialsResponse | null>(null);
  const [loadingMaterials, setLoadingMaterials] = useState(true);
  const [summaryLoading, setSummaryLoading] = useState(false);
  const [keyPointsLoading, setKeyPointsLoading] = useState(false);
  const [flashcardsLoading, setFlashcardsLoading] = useState(false);
  const [showRecentQuestions, setShowRecentQuestions] = useState(true);
  const [questionFilter, setQuestionFilter] = useState<'all' | 'answered' | 'unanswered' | 'flagged' | 'hidden'>('all');
  const [questionSort, setQuestionSort] = useState<'newest' | 'oldest' | 'most_repeated'>('newest');
  const [faqQuestionIds, setFaqQuestionIds] = useState<Set<number>>(new Set());
  const [pinnedQuestionIds, setPinnedQuestionIds] = useState<Set<number>>(new Set());
  const [hiddenQuestionIds, setHiddenQuestionIds] = useState<Set<number>>(new Set());
  const [manualAnswers, setManualAnswers] = useState<Record<number, string>>({});
  const [answerDrafts, setAnswerDrafts] = useState<Record<number, string>>({});
  const [activeAnswerId, setActiveAnswerId] = useState<number | null>(null);
  const [lectureResources, setLectureResources] = useState<LectureResource[]>([]);
  const [loadingResources, setLoadingResources] = useState(false);
  const [transcript, setTranscript] = useState<TranscriptSegment[]>([]);
  const [loadingTranscript, setLoadingTranscript] = useState(false);
  const [transcribing, setTranscribing] = useState(false);
  const [transcriptionError, setTranscriptionError] = useState<string | null>(null);
  const [slides, setSlides] = useState<{ slide_number: number; text: string }[]>([]);
  const [loadingSlides, setLoadingSlides] = useState(false);
  const [lectureAnalytics, setLectureAnalytics] = useState<LectureAnalyticsResponse | null>(null);
  const [loadingAnalytics, setLoadingAnalytics] = useState(false);
  const [analyticsError, setAnalyticsError] = useState<string | null>(null);
  const [courseName, setCourseName] = useState<string | null>(null);
  const [showSummaryTool, setShowSummaryTool] = useState(true);
  const [showKeyConceptsTool, setShowKeyConceptsTool] = useState(true);
  const [showFlashcardsTool, setShowFlashcardsTool] = useState(true);
  type LecturePanel = 'all' | 'analytics' | 'management' | 'resources' | 'questions';
  const [activeLecturePanel, setActiveLecturePanel] = useState<LecturePanel>('all');
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const slideViewerRef = useRef<SlideViewerRef>(null);
  const replaceFileInputRef = useRef<HTMLInputElement>(null);

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [currentAnswer, history, scrollToBottom]);

  useEffect(() => {
    if (lecture?.file_type === 'audio' && lecture.has_transcript) {
      loadTranscript();
    } else {
      setTranscript([]);
    }
    if (lecture?.file_type === 'slides') {
      loadSlides();
    } else {
      setSlides([]);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [lecture?.file_type, lecture?.has_transcript]);

  const loadLecture = async () => {
    try {
      const data = await apiClient.getLecture(lectureId);
      setLecture(data);
      if (data.course_id) {
        const courses = await apiClient.getCourses();
        const matched = courses.courses.find((course) => course.id === data.course_id);
        setCourseName(matched?.name || null);
      }
    } catch (error) {
      console.error('Failed to load lecture:', error);
      router.push('/');
    } finally {
      setLoading(false);
    }
  };

  const loadHistory = async () => {
    try {
      const response = await apiClient.getQueryHistory(lectureId);
      const queries = response.queries;
      if (currentUser?.role === 'student' && currentUser.email) {
        setHistory(queries.filter((item) => item.user_email === currentUser.email));
      } else {
        setHistory(queries);
      }
    } catch (error) {
      console.error('Failed to load history:', error);
    }
  };

  const loadMaterials = async () => {
    try {
      setLoadingMaterials(true);
      const data = await apiClient.getStudyMaterials(lectureId);
      setMaterials(data);
    } catch (error) {
      console.error('Failed to load study materials:', error);
    } finally {
      setLoadingMaterials(false);
    }
  };

  const loadResources = useCallback(async () => {
    setLoadingResources(true);
    try {
      const data = await apiClient.getLectureResources(lectureId);
      setLectureResources(data.resources);
    } catch (error) {
      console.error('Failed to load lecture resources:', error);
    } finally {
      setLoadingResources(false);
    }
  }, [lectureId]);

  useEffect(() => {
    // Check authentication
    if (!apiClient.isAuthenticated()) {
      router.push('/auth/login');
      return;
    }

    const storedUser = apiClient.getStoredUser();
    if (storedUser) {
      setCurrentUser(storedUser);
    }

    loadLecture();
    loadHistory();
    loadMaterials();
    loadResources();
  }, [lectureId, router, loadResources]);

  const loadSlides = useCallback(async () => {
    if (lecture?.file_type !== 'slides') {
      setSlides([]);
      return;
    }
    setLoadingSlides(true);
    try {
      const data = await apiClient.getSlides(lectureId);
      setSlides(data.slides);
    } catch (error) {
      console.error('Failed to load slides:', error);
    } finally {
      setLoadingSlides(false);
    }
  }, [lecture?.file_type, lectureId]);

  const loadLectureAnalytics = useCallback(async () => {
    if (currentUser?.role !== 'instructor') {
      return;
    }
    setLoadingAnalytics(true);
    setAnalyticsError(null);
    try {
      const data = await apiClient.getLectureAnalytics(lectureId);
      setLectureAnalytics(data);
    } catch (error: any) {
      console.error('Failed to load lecture analytics:', error);
      setAnalyticsError(error.response?.data?.detail || 'Failed to load lecture analytics.');
    } finally {
      setLoadingAnalytics(false);
    }
  }, [currentUser?.role, lectureId]);

  const handleReplaceLectureFile = async (file: File) => {
    if (!file) return;
    try {
      await apiClient.replaceLectureFile(lectureId, file);
      await loadLecture();
      await loadLectureAnalytics();
      await loadHistory();
    } catch (error: any) {
      alert(error.response?.data?.detail || 'Failed to replace lecture file');
    }
  };

  const handleRenameLecture = async () => {
    if (!lecture) return;
    const nextName = prompt('Rename lecture', lecture.original_name);
    if (!nextName || !nextName.trim()) return;
    try {
      const updated = await apiClient.renameLecture(lectureId, nextName.trim());
      setLecture(updated);
    } catch (error: any) {
      alert(error.response?.data?.detail || 'Failed to rename lecture');
    }
  };

  const handleArchiveLecture = async () => {
    if (!confirm('Archive this lecture? It will be hidden from the course list.')) return;
    try {
      await apiClient.archiveLecture(lectureId);
      router.push('/');
    } catch (error: any) {
      alert(error.response?.data?.detail || 'Failed to archive lecture');
    }
  };

  const handleAddResource = async () => {
    const title = prompt('Resource title');
    if (!title || !title.trim()) return;
    const url = prompt('Resource URL');
    if (!url || !url.trim()) return;
    try {
      const resource = await apiClient.addLectureResource(lectureId, title.trim(), url.trim());
      setLectureResources((prev) => [resource, ...prev]);
    } catch (error: any) {
      alert(error.response?.data?.detail || 'Failed to add resource');
    }
  };

  const handleDeleteResource = async (resourceId: number) => {
    if (!confirm('Remove this resource?')) return;
    try {
      await apiClient.deleteLectureResource(lectureId, resourceId);
      setLectureResources((prev) => prev.filter((resource) => resource.id !== resourceId));
    } catch (error: any) {
      alert(error.response?.data?.detail || 'Failed to delete resource');
    }
  };

  useEffect(() => {
    if (currentUser?.role === 'instructor') {
      loadLectureAnalytics();
    }
  }, [currentUser?.role, loadLectureAnalytics]);

  const loadTranscript = useCallback(
    async (force = false) => {
      const isAudioLecture = lecture?.file_type === 'audio';
      if (!force && (!isAudioLecture || !lecture?.has_transcript)) {
        setTranscript([]);
        return;
      }
      setLoadingTranscript(true);
      setTranscriptionError(null);
      try {
        const data = await apiClient.getTranscript(lectureId);
        setTranscript(data.segments);
      } catch (error: any) {
        console.error('Failed to load transcript:', error);
        setTranscriptionError(error.response?.data?.detail || 'Transcript unavailable.');
      } finally {
        setLoadingTranscript(false);
      }
    },
    [lecture?.file_type, lecture?.has_transcript, lectureId]
  );

  const handleTranscribeAudio = async () => {
    setTranscribing(true);
    setTranscriptionError(null);
    try {
      await apiClient.transcribeLecture(lectureId);
      await loadLecture();
      await loadTranscript(true);
    } catch (error: any) {
      console.error('Failed to transcribe lecture:', error);
      setTranscriptionError(error.response?.data?.detail || 'Failed to transcribe audio.');
    } finally {
      setTranscribing(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!question.trim() || asking) return;

    setAsking(true);
    setCurrentAnswer(null);

    try {
      const response = await apiClient.queryLecture(lectureId, question);
      setCurrentAnswer(response);
      setQuestion('');
      await loadHistory(); // Refresh history so the new answer appears in history list
      setCurrentAnswer(null); // Avoid showing duplicate (history already contains it)
    } catch (error: any) {
      console.error('Failed to query:', error);
      alert(error.response?.data?.detail || 'Failed to get answer');
    } finally {
      setAsking(false);
    }
  };

  const handleGenerateSummary = async () => {
    setSummaryLoading(true);
    try {
      const response = await apiClient.generateSummary(lectureId);
      setMaterials((prev) => ({
        lecture_id: lectureId,
        summary: response.summary,
        key_points: prev?.key_points ?? [],
        flashcards: prev?.flashcards ?? [],
      }));
    } catch (error: any) {
      alert(error.response?.data?.detail || 'Failed to generate summary');
    } finally {
      setSummaryLoading(false);
    }
  };

  const handleGenerateKeyPoints = async () => {
    setKeyPointsLoading(true);
    try {
      const response = await apiClient.generateKeyPoints(lectureId);
      setMaterials((prev) => ({
        lecture_id: lectureId,
        summary: prev?.summary ?? null,
        key_points: response.key_points,
        flashcards: prev?.flashcards ?? [],
      }));
    } catch (error: any) {
      alert(error.response?.data?.detail || 'Failed to generate key points');
    } finally {
      setKeyPointsLoading(false);
    }
  };

  const handleGenerateFlashcards = async () => {
    setFlashcardsLoading(true);
    try {
      const response = await apiClient.generateFlashcards(lectureId);
      setMaterials((prev) => ({
        lecture_id: lectureId,
        summary: prev?.summary ?? null,
        key_points: prev?.key_points ?? [],
        flashcards: response.flashcards,
      }));
    } catch (error: any) {
      alert(error.response?.data?.detail || 'Failed to generate flashcards');
    } finally {
      setFlashcardsLoading(false);
    }
  };

  const isInstructor = currentUser?.role === 'instructor';
  const visibleHistory =
    currentUser?.role === 'student' && currentUser.email
      ? history.filter((item) => item.user_email === currentUser.email)
      : history;
  const toggleId = (setter: Dispatch<SetStateAction<Set<number>>>, id: number) => {
    setter((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  };
  const questionFrequency = visibleHistory.reduce<Record<string, number>>((acc, item) => {
    const key = item.question.trim().toLowerCase();
    acc[key] = (acc[key] || 0) + 1;
    return acc;
  }, {});

  const peakConfusedPages = useMemo(() => {
    if (!lecture || lecture.file_type !== 'pdf' || lecture.page_count <= 0) return null;
    const pageQuestions = history.filter((item) => item.page_number != null);
    if (pageQuestions.length === 0) return null;
    const BIN_COUNT = 5;
    const totalPages = lecture.page_count;
    const binSize = Math.ceil(totalPages / BIN_COUNT);
    const bins = Array.from({ length: BIN_COUNT }, (_, i) => {
      const startPage = i * binSize + 1;
      const endPage = Math.min((i + 1) * binSize, totalPages);
      return { index: i, startPage, endPage, count: 0 };
    });
    for (const q of pageQuestions) {
      const pageNumber = q.page_number ?? 1;
      const binIndex = Math.min(Math.floor((pageNumber - 1) / binSize), BIN_COUNT - 1);
      bins[binIndex].count += 1;
    }
    const peakValue = Math.max(...bins.map((bin) => bin.count));
    const peakBin = bins.find((bin) => bin.count === peakValue && peakValue > 0);
    return peakBin ? `Pages ${peakBin.startPage}-${peakBin.endPage}` : null;
  }, [lecture, history]);
  const baseHistory =
    questionFilter === 'hidden'
      ? visibleHistory
      : visibleHistory.filter((item) => !hiddenQuestionIds.has(item.id));
  const filteredHistory = baseHistory.filter((item) => {
    if (questionFilter === 'answered') {
      return Boolean(item.answer?.trim());
    }
    if (questionFilter === 'unanswered') {
      return !item.answer?.trim();
    }
    if (questionFilter === 'flagged') {
      return faqQuestionIds.has(item.id);
    }
    if (questionFilter === 'hidden') {
      return hiddenQuestionIds.has(item.id);
    }
    return true;
  });
  const sortedHistory = [...filteredHistory].sort((a, b) => {
    const pinnedDelta = Number(pinnedQuestionIds.has(b.id)) - Number(pinnedQuestionIds.has(a.id));
    if (pinnedDelta !== 0) return pinnedDelta;
    if (questionSort === 'most_repeated') {
      const countA = questionFrequency[a.question.trim().toLowerCase()] || 0;
      const countB = questionFrequency[b.question.trim().toLowerCase()] || 0;
      const countDelta = countB - countA; // higher count first
      if (countDelta !== 0) return countDelta;
    }
    const timeA = a.created_at ? new Date(a.created_at).getTime() : 0;
    const timeB = b.created_at ? new Date(b.created_at).getTime() : 0;
    if (questionSort === 'oldest') {
      return timeA - timeB; // older (smaller timestamp) first
    }
    return timeB - timeA; // newest first (default)
  });

  const renderFrequencyPolygon = () => {
    if (loadingAnalytics) {
      return <p className="text-base text-gray-500">Loading lecture timeline...</p>;
    }
    if (analyticsError) {
      return <p className="text-base text-red-600">{analyticsError}</p>;
    }
    if (!lecture || lecture.file_type !== 'pdf') {
      return (
        <p className="text-base text-gray-500">
          Document-position heatmap is available for PDF lectures.
        </p>
      );
    }
    if (lecture.page_count <= 0) {
      return (
        <p className="text-base text-gray-500">
          Lecture pages are not available yet.
        </p>
      );
    }
    const pageQuestions = history.filter((item) => item.page_number != null);
    if (pageQuestions.length === 0) {
      return (
        <p className="text-base text-gray-500">
          No page-linked questions yet. Ask questions to build the document-position heatmap.
        </p>
      );
    }

    const BIN_COUNT = 5;
    const totalPages = lecture.page_count;
    const binSize = Math.ceil(totalPages / BIN_COUNT);
    const bins = Array.from({ length: BIN_COUNT }, (_, i) => {
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
      const binIndex = Math.min(Math.floor((pageNumber - 1) / binSize), BIN_COUNT - 1);
      bins[binIndex].count += 1;
    }

    const maxValue = Math.max(1, ...bins.map((bin) => bin.count));
    const peakValue = Math.max(...bins.map((bin) => bin.count));
    const formatRangeLabel = (bin: (typeof bins)[number]) =>
      `Pages ${bin.startPage}-${bin.endPage}`;

    return (
      <div>
        <div className="flex items-end gap-2">
          {bins.map((bin, idx) => {
            const intensity = bin.count / maxValue;
            const isPeak = bin.count === peakValue && peakValue > 0;
            return (
              <div key={`heat-bin-${idx}`} className="flex-1 flex flex-col items-center">
                <div
                  className={`w-full h-10 rounded-md border ${isPeak ? 'border-primary-600' : 'border-gray-200'}`}
                  style={{ backgroundColor: `rgba(37, 99, 235, ${0.15 + 0.75 * intensity})` }}
                  title={`${formatRangeLabel(bin)} • ${bin.count} questions`}
                />
                <span className="mt-2 text-sm text-gray-500">
                  {formatRangeLabel(bin)}
                </span>
                <span className="text-sm text-gray-400">{bin.count}</span>
              </div>
            );
          })}
        </div>
      </div>
    );
  };

  const formatHistoryTime = (value: string) => {
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return value;
    return date.toLocaleString();
  };

  const normalizedApiBase = API_BASE_URL.replace(/\/$/, '');
  const audioSourceUrl =
    lecture?.file_type === 'audio'
      ? `${normalizedApiBase}/${lecture.file_path.replace(/^\/+/, '')}`
      : '';

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <svg className="w-8 h-8 animate-spin mx-auto text-primary-500" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
          </svg>
          <p className="mt-4 text-gray-500">Loading lecture...</p>
        </div>
      </div>
    );
  }

  if (!lecture) {
    return null;
  }

  if (lecture.status !== 'completed') {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="w-16 h-16 bg-yellow-100 rounded-full flex items-center justify-center mx-auto mb-4">
            <svg className="w-8 h-8 text-yellow-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
          <h2 className="text-2xl font-bold text-gray-900 mb-2">Lecture is Processing</h2>
          <p className="text-gray-600 mb-4">Please wait while we process your lecture.</p>
          <p className="text-sm text-gray-500">Status: {lecture.status}</p>
          <Link
            href="/"
            className="mt-6 inline-block text-primary-600 hover:text-primary-700 font-medium"
          >
            ← Back to Lectures
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <div className="flex items-center space-x-4">
              {lecture?.course_id ? (
                  <Link
                  href={`/courses/${lecture.course_id}`}
                  className="text-base font-medium text-gray-700 hover:text-primary-600"
                >
                  ← Back to Course
                </Link>
              ) : (
              <Link
                href="/"
                className="text-base font-medium text-gray-700 hover:text-primary-600"
              >
                ← Back to Courses
              </Link>
              )}
            </div>
            {currentUser ? (
              <div className="flex items-center space-x-3">
                <div className="flex flex-col items-end">
                <span className="text-base font-medium text-gray-900">{currentUser.email}</span>
                <span className="text-sm text-gray-500 capitalize">{currentUser.role}</span>
                </div>
                <button
                  onClick={() => {
                    apiClient.logout();
                    router.push('/auth/login');
                  }}
                  className="px-4 py-2 text-base font-medium text-white bg-primary-600 hover:bg-primary-700 rounded-md transition-colors"
                >
                  Logout
                </button>
              </div>
            ) : null}
          </div>
        </div>
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold text-gray-900">{lecture.original_name}</h1>
              <p className="text-base text-gray-500">
                {lecture.file_type === 'audio'
                  ? 'Audio lecture'
                  : lecture.file_type === 'slides'
                  ? `${lecture.page_count} slides`
                  : `${lecture.page_count} pages`}
              </p>
            </div>
          </div>
        </div>
      </header>

      <div className="sticky top-16 z-10 bg-white/95 backdrop-blur border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-2 text-base text-gray-600 flex items-center gap-2 min-w-0">
          <span className="font-medium text-gray-900 truncate max-w-[45%]">
            {courseName || (lecture.course_id ? `Course ${lecture.course_id}` : 'Course')}
          </span>
          <span className="text-gray-400">→</span>
          <span className="text-gray-700 truncate">{lecture.original_name}</span>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 flex max-w-7xl mx-auto w-full">
        {isInstructor ? (
          <div className="flex-1 flex w-full">
            {/* Left Menu - Instructor */}
            <aside className="bg-white border-r border-gray-200 w-64 min-w-64 p-5 h-fit sticky top-[7.5rem]">
              <h4 className="text-base font-semibold text-gray-900 mb-4">Navigation</h4>
              <div className="space-y-2">
                {(['all', 'analytics', 'management', 'resources', 'questions'] as const).map((panel) => (
                  <button
                    key={panel}
                    onClick={() => setActiveLecturePanel(panel)}
                    className={`w-full px-4 py-3 text-base rounded-lg border text-left transition ${
                      activeLecturePanel === panel
                        ? 'bg-primary-600 text-white border-primary-600'
                        : 'bg-white text-gray-700 border-gray-200 hover:border-gray-300'
                    }`}
                  >
                    {panel === 'all'
                      ? 'All'
                      : panel === 'analytics'
                      ? 'Lecture Analytics'
                      : panel === 'management'
                      ? 'Lecture Management'
                      : panel === 'resources'
                      ? 'Lecture Resources'
                      : 'Recent Questions'}
                  </button>
                ))}
              </div>
            </aside>
            <div className="flex-1 flex flex-col min-w-0">
        {/* Chat Area */}
        <div className="flex-1 flex flex-col">
          {lecture.file_type === 'slides' && (
            <div className="px-4 sm:px-6 lg:px-8 pt-6">
              <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 mb-6">
                <div className="flex items-center justify-between mb-4">
                  <div>
                    <h3 className="text-xl font-semibold text-gray-900">Slide Viewer</h3>
                    <p className="text-base text-gray-500">
                      Browse slides and see the extracted text for each slide.
                    </p>
                  </div>
                  {loadingSlides && (
                    <div className="flex items-center space-x-2 text-sm text-gray-500">
                      <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                      </svg>
                      <span>Loading slides...</span>
                    </div>
                  )}
                </div>
                <SlideViewer ref={slideViewerRef} slides={slides} />
              </div>
            </div>
          )}
          {lecture.file_type === 'audio' && (
            <div className="px-4 sm:px-6 lg:px-8 pt-6">
              <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 mb-6">
                <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 mb-4">
                  <div>
                    <h3 className="text-xl font-semibold text-gray-900">Audio Playback & Transcript</h3>
                    <p className="text-base text-gray-500">
                      Listen to the lecture and jump to specific segments via the transcript.
                    </p>
                  </div>
                  <button
                    onClick={handleTranscribeAudio}
                    disabled={transcribing}
                    className="px-4 py-2 bg-primary-600 text-white rounded-lg text-base font-medium hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {transcribing
                      ? 'Transcribing...'
                      : lecture.has_transcript
                      ? 'Regenerate Transcript'
                      : 'Transcribe Audio'}
                  </button>
                </div>
                {transcriptionError && (
                  <div className="mb-4 text-base text-red-600 bg-red-50 border border-red-200 rounded-lg p-3">
                    {transcriptionError}
                  </div>
                )}
                {audioSourceUrl ? (
                  <>
                    {lecture.has_transcript && loadingTranscript ? (
                      <div className="flex items-center space-x-2 text-sm text-gray-500">
                        <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                        </svg>
                        <span>Loading transcript...</span>
                      </div>
                    ) : (
                      <AudioPlayer
                        sourceUrl={audioSourceUrl}
                        segments={lecture.has_transcript ? transcript : []}
                      />
                    )}
                    {!lecture.has_transcript && !transcribing && (
                      <p className="text-base text-gray-500 mt-4">
                        Transcript not generated yet. Run transcription to enable timestamped search.
                      </p>
                    )}
                  </>
                ) : (
                  <p className="text-base text-gray-500">Audio file unavailable.</p>
                )}
              </div>
            </div>
          )}
            <div className="flex-1 overflow-y-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6">
              {(activeLecturePanel === 'all' || activeLecturePanel === 'analytics') && (
              <>
              <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
                <div className="flex items-center justify-between mb-4">
                  <div>
                    <h2 className="text-2xl font-bold text-gray-900">Lecture Analytics</h2>
                    <p className="text-base text-gray-500">Engagement and question activity for this lecture.</p>
                  </div>
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                  <div className="bg-gray-50 border border-gray-200 rounded-lg p-5">
                    <p className="text-sm text-gray-500 mb-1">Total Questions</p>
                    <p className="text-3xl font-bold text-gray-900">
                      {lectureAnalytics?.total_questions ?? 0}
                    </p>
                  </div>
                  <div className="bg-gray-50 border border-gray-200 rounded-lg p-5">
                    <p className="text-sm text-gray-500 mb-1">Active Students</p>
                    <p className="text-3xl font-bold text-gray-900">
                      {lectureAnalytics?.active_students ?? 0}
                    </p>
                  </div>
                  <div className="bg-gray-50 border border-gray-200 rounded-lg p-5">
                    <p className="text-sm text-gray-500 mb-1">Peak Confused Lecture Pages</p>
                    <p className="text-xl font-semibold text-gray-900">
                      {peakConfusedPages ?? lectureAnalytics?.peak_confusion_range ?? 'N/A'}
                    </p>
                  </div>
                  <div className="bg-gray-50 border border-gray-200 rounded-lg p-5">
                    <p className="text-sm text-gray-500 mb-1">Top Confused Question</p>
                    <p className="text-base font-semibold text-gray-900 line-clamp-3">
                      {lectureAnalytics?.top_confused_question || 'N/A'}
                    </p>
                  </div>
                </div>
              </div>

              <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
                <div className="flex items-center justify-between mb-4">
                  <div>
                    <h3 className="text-xl font-semibold text-gray-900">Lecture Timeline / Heatmap</h3>
                    <p className="text-base text-gray-500">
                      Confusion intensity across different parts of the lecture material.
                    </p>
                  </div>
                </div>
                {renderFrequencyPolygon()}
              </div>
              </>
              )}

              {(activeLecturePanel === 'all' || activeLecturePanel === 'management') && (
                  <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
                    <h3 className="text-xl font-semibold text-gray-900 mb-4">Lecture Management</h3>
                    <div className="space-y-3 text-base text-gray-700">
                      <div className="flex items-center justify-between">
                        <span>Visibility</span>
                        <span className="font-medium">
                          {(lecture?.status as string) === 'archived'
                            ? 'Archived'
                            : (lecture?.status as string) === 'completed'
                            ? 'Published'
                            : 'Draft'}
                        </span>
                      </div>
                      <div className="flex items-center justify-between">
                        <span>Release time</span>
                        <span className="font-medium">{lecture?.created_at ? formatHistoryTime(lecture.created_at) : 'N/A'}</span>
                      </div>
                      <div className="flex items-center justify-between">
                        <span>Allowed access</span>
                        <span className="font-medium">Everyone</span>
                      </div>
                      <div className="flex items-center justify-between">
                        <span>Download enabled</span>
                        <span className="font-medium">{lecture?.file_path ? 'Yes' : 'No'}</span>
                      </div>
                    </div>
                    <div className="mt-4 grid grid-cols-1 gap-2">
                      <button
                        type="button"
                        onClick={() => replaceFileInputRef.current?.click()}
                        className="px-4 py-3 text-base border border-gray-300 rounded-lg hover:bg-gray-50"
                      >
                        Replace PDF
                      </button>
                      <button
                        type="button"
                        onClick={handleRenameLecture}
                        className="px-4 py-3 text-base border border-gray-300 rounded-lg hover:bg-gray-50"
                      >
                        Rename lecture
                      </button>
                    </div>
                    <input
                      ref={replaceFileInputRef}
                      type="file"
                      accept=".pdf"
                      className="hidden"
                      onChange={(e) => {
                        const file = e.target.files?.[0];
                        if (file) {
                          handleReplaceLectureFile(file);
                        }
                        e.currentTarget.value = '';
                      }}
                    />
                  </div>
              )}

              {(activeLecturePanel === 'all' || activeLecturePanel === 'resources') && (
                  <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
                    <h3 className="text-xl font-semibold text-gray-900 mb-4">Lecture Resources</h3>
                    <div className="space-y-3 text-base text-gray-700">
                      <div>
                        <p className="text-sm text-gray-500 mb-1">Primary file</p>
                        <p className="font-medium text-base">{lecture?.original_name || 'Untitled lecture'}</p>
                        <div className="mt-2 flex flex-wrap gap-2">
                          <a
                            href={lecture?.file_path ? `${normalizedApiBase}/${lecture.file_path.replace(/^\/+/, '')}` : '#'}
                            target="_blank"
                            rel="noreferrer"
                            className="px-4 py-2 text-base border border-gray-300 rounded-lg hover:bg-gray-50"
                          >
                            Preview
                          </a>
                          <a
                            href={lecture?.file_path ? `${normalizedApiBase}/${lecture.file_path.replace(/^\/+/, '')}` : '#'}
                            download
                            className="px-4 py-2 text-base border border-gray-300 rounded-lg hover:bg-gray-50"
                          >
                            Download
                          </a>
                          <button
                            type="button"
                            onClick={() => replaceFileInputRef.current?.click()}
                            className="px-4 py-2 text-base border border-gray-300 rounded-lg hover:bg-gray-50"
                          >
                            Replace
                          </button>
                        </div>
                      </div>
                      <div className="border-t border-gray-200 pt-3">
                        <p className="text-sm text-gray-500 mb-2">Additional materials</p>
                        {loadingResources ? (
                          <p className="text-base text-gray-500">Loading resources...</p>
                        ) : lectureResources.length === 0 ? (
                          <p className="text-base text-gray-500">No additional resources yet.</p>
                        ) : (
                          <div className="space-y-2">
                            {lectureResources.map((resource) => (
                              <div key={resource.id} className="flex items-center justify-between gap-2 text-base">
                                <a
                                  href={resource.url}
                                  target="_blank"
                                  rel="noreferrer"
                                  className="text-primary-600 hover:text-primary-700 truncate"
                                  title={resource.title}
                                >
                                  {resource.title}
                                </a>
                                <button
                                  type="button"
                                  onClick={() => handleDeleteResource(resource.id)}
                                  className="text-base text-red-600 hover:text-red-700"
                                >
                                  Remove
                                </button>
                              </div>
                            ))}
                          </div>
                        )}
                        <button
                          type="button"
                          onClick={handleAddResource}
                          className="mt-3 px-4 py-2 text-base border border-gray-300 rounded-lg hover:bg-gray-50"
                        >
                          Add resource
                        </button>
                      </div>
                    </div>
                  </div>
              )}

              {(activeLecturePanel === 'all' || activeLecturePanel === 'questions') && (
              <div className={`rounded-xl shadow-sm border ${showRecentQuestions ? 'bg-white border-gray-200' : 'bg-gray-50 border-gray-200'}`}>
                <button
                  onClick={() => setShowRecentQuestions(!showRecentQuestions)}
                  className="w-full px-6 py-4 flex items-center justify-between text-left"
                >
                  <div>
                    <h3 className="text-xl font-semibold text-gray-900">Recent Questions</h3>
                    <p className="text-base text-gray-500">Latest questions submitted for this lecture.</p>
                  </div>
                  <span className="text-base text-gray-600">{showRecentQuestions ? '−' : '+'}</span>
                </button>
                {showRecentQuestions && (
                  <div className="px-6 pb-6 space-y-4">
                    <div className="flex flex-wrap items-center justify-between gap-3">
                      <div className="flex flex-wrap items-center gap-2">
                        {(['all', 'answered', 'unanswered', 'flagged'] as const).map((filter) => (
                          <button
                            key={filter}
                            type="button"
                            onClick={() => setQuestionFilter(filter)}
                            className={`px-4 py-2 text-base rounded-full border ${
                              questionFilter === filter
                                ? 'bg-primary-600 text-white border-primary-600'
                                : 'bg-white text-gray-700 border-gray-200'
                            }`}
                          >
                            {filter === 'all' ? 'All' : filter === 'answered' ? 'Answered' : filter === 'unanswered' ? 'Unanswered' : 'Flagged'}
                          </button>
                        ))}
                        <button
                          type="button"
                          onClick={() => setQuestionFilter('hidden')}
                          className={`px-4 py-2 text-base rounded-full border ${
                            questionFilter === 'hidden'
                              ? 'bg-primary-600 text-white border-primary-600'
                              : 'bg-white text-gray-700 border-gray-200'
                          }`}
                        >
                          Hidden
                        </button>
                      </div>
                      <div className="flex items-center gap-2 text-base text-gray-500">
                        <span>Sort</span>
                        <select
                          value={questionSort}
                          onChange={(e) => setQuestionSort(e.target.value as 'newest' | 'oldest' | 'most_repeated')}
                          className="px-3 py-2 text-base border border-gray-300 rounded-lg"
                        >
                          <option value="newest">Newest</option>
                          <option value="oldest">Oldest</option>
                          <option value="most_repeated">Most repeated</option>
                        </select>
                      </div>
                    </div>
                    {sortedHistory.length === 0 ? (
                      <p className="text-base text-gray-500">
                        No questions match this filter yet.
                      </p>
                    ) : (
                      <div className="space-y-3">
                        {sortedHistory.map((item) => {
                          const isAnswered = Boolean(item.answer?.trim());
                          const isFlagged = faqQuestionIds.has(item.id);
                          const isPinned = pinnedQuestionIds.has(item.id);
                          return (
                            <div key={item.id} className="border border-gray-200 rounded-lg p-4 space-y-3">
                              <div className="flex flex-wrap items-start justify-between gap-3">
                                <div>
                                  <p className="text-base text-gray-800 font-medium">{item.question}</p>
                                  <div className="mt-1 flex flex-wrap items-center gap-2 text-sm text-gray-500">
                                    <span>{item.user_email || 'Student'}</span>
                                    <span>•</span>
                                    <span>{formatHistoryTime(item.created_at)}</span>
                                  </div>
                                  <div className="mt-2 flex flex-wrap items-center gap-2">
                                    <span className={`px-2 py-0.5 rounded-full text-sm border ${isAnswered ? 'bg-green-50 text-green-700 border-green-100' : 'bg-gray-50 text-gray-600 border-gray-200'}`}>
                                      {isAnswered ? 'Answered' : 'Unanswered'}
                                    </span>
                                    {isFlagged && (
                                      <span className="px-2 py-0.5 rounded-full text-sm border bg-amber-50 text-amber-700 border-amber-200">
                                        FAQ
                                      </span>
                                    )}
                                    {isPinned && (
                                      <span className="px-2 py-0.5 rounded-full text-sm border bg-blue-50 text-blue-700 border-blue-200">
                                        Pinned
                                      </span>
                                    )}
                                  </div>
                                </div>
                                <div className="flex flex-wrap items-center gap-2">
                                  <button
                                    type="button"
                                    onClick={() => {
                                      setActiveAnswerId(item.id);
                                      setAnswerDrafts((prev) => ({
                                        ...prev,
                                        [item.id]: prev[item.id] ?? manualAnswers[item.id] ?? item.answer ?? '',
                                      }));
                                    }}
                                    className="px-4 py-2 text-base border border-gray-300 rounded-lg hover:bg-gray-50"
                                  >
                                    Answer
                                  </button>
                                  <button
                                    type="button"
                                    onClick={() => toggleId(setFaqQuestionIds, item.id)}
                                    className="px-4 py-2 text-base border border-gray-300 rounded-lg hover:bg-gray-50"
                                  >
                                    {isFlagged ? 'Unmark FAQ' : 'Mark FAQ'}
                                  </button>
                                  <button
                                    type="button"
                                    onClick={() => toggleId(setPinnedQuestionIds, item.id)}
                                    className="px-4 py-2 text-base border border-gray-300 rounded-lg hover:bg-gray-50"
                                  >
                                    {isPinned ? 'Unpin' : 'Pin'}
                                  </button>
                                  <button
                                    type="button"
                                    onClick={() => toggleId(setHiddenQuestionIds, item.id)}
                                    className="px-4 py-2 text-base border border-gray-300 rounded-lg hover:bg-gray-50"
                                  >
                                    {hiddenQuestionIds.has(item.id) ? 'Unhide' : 'Hide'}
                                  </button>
                                </div>
                              </div>
                              {item.answer && (
                                <p className="text-base text-gray-600 line-clamp-3">{item.answer}</p>
                              )}
                              {manualAnswers[item.id] && (
                                <div className="text-base text-blue-700 bg-blue-50 border border-blue-100 rounded-md p-3">
                                  <p className="text-sm uppercase text-blue-500 mb-1">Instructor note</p>
                                  <p className="whitespace-pre-wrap">{manualAnswers[item.id]}</p>
                                </div>
                              )}
                              {activeAnswerId === item.id && (
                                <div className="border border-gray-200 rounded-lg p-3 bg-gray-50">
                                  <textarea
                                    value={answerDrafts[item.id] ?? ''}
                                    onChange={(e) =>
                                      setAnswerDrafts((prev) => ({ ...prev, [item.id]: e.target.value }))
                                    }
                                    rows={3}
                                    className="w-full px-4 py-3 text-base border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                                    placeholder="Write an instructor note or answer..."
                                  />
                                  <div className="mt-2 flex items-center gap-2">
                                    <button
                                      type="button"
                                      onClick={() => {
                                        const nextValue = (answerDrafts[item.id] ?? '').trim();
                                        setManualAnswers((prev) => {
                                          const next = { ...prev };
                                          if (nextValue) {
                                            next[item.id] = nextValue;
                                          } else {
                                            delete next[item.id];
                                          }
                                          return next;
                                        });
                                        setActiveAnswerId(null);
                                      }}
                                      className="px-4 py-2 text-base bg-primary-600 text-white rounded-lg hover:bg-primary-700"
                                    >
                                      Save
                                    </button>
                                    <button
                                      type="button"
                                      onClick={() => setActiveAnswerId(null)}
                                      className="px-4 py-2 text-base border border-gray-300 rounded-lg hover:bg-gray-50"
                                    >
                                      Cancel
                                    </button>
                                  </div>
                                </div>
                              )}
                            </div>
                          );
                        })}
                      </div>
                    )}
                  </div>
                )}
              </div>
              )}
            </div>
            </div>
            </div>
          </div>
          ) : (
            <div className="flex-1 flex">
              <aside className="w-80 border-r border-gray-200 bg-white p-4 space-y-4">
                <div>
                  <h3 className="text-xl font-semibold text-gray-900">Study Tools</h3>
                  <p className="text-sm text-gray-500">Generate learning aids for this lecture.</p>
                </div>

                <div className={`rounded-xl shadow-sm border ${showSummaryTool ? 'bg-white border-gray-200' : 'bg-gray-50 border-gray-200'}`}>
                  <button
                    onClick={() => setShowSummaryTool(!showSummaryTool)}
                    className="w-full px-4 py-3 flex items-center justify-between text-left"
                  >
                    <div>
                      <h4 className="text-base font-semibold text-gray-900">Lecture Summary</h4>
                      <p className="text-sm text-gray-500">Concise overview of the lecture.</p>
                    </div>
                    <span className="text-sm text-gray-600">{showSummaryTool ? 'Collapse' : 'Expand'}</span>
                  </button>
                  {showSummaryTool && (
                    <div className="px-4 pb-4 space-y-3">
                      <button
                        onClick={handleGenerateSummary}
                        className="w-full px-4 py-2 bg-primary-600 text-white rounded-lg text-base font-medium hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed"
                        disabled={summaryLoading}
                      >
                        {summaryLoading ? 'Generating...' : materials?.summary ? 'Regenerate' : 'Generate'}
                      </button>
                      {loadingMaterials ? (
                        <p className="text-sm text-gray-500">Loading...</p>
                      ) : materials?.summary ? (
                        <p className="text-base text-gray-700 whitespace-pre-wrap">{materials.summary}</p>
                      ) : (
                        <p className="text-sm text-gray-500">No summary yet.</p>
                      )}
                    </div>
                  )}
                </div>

                <div className={`rounded-xl shadow-sm border ${showKeyConceptsTool ? 'bg-white border-gray-200' : 'bg-gray-50 border-gray-200'}`}>
                  <button
                    onClick={() => setShowKeyConceptsTool(!showKeyConceptsTool)}
                    className="w-full px-4 py-3 flex items-center justify-between text-left"
                  >
                    <div>
                      <h4 className="text-base font-semibold text-gray-900">Key Points</h4>
                      <p className="text-sm text-gray-500">Exam-focused highlights.</p>
                    </div>
                    <span className="text-sm text-gray-600">{showKeyConceptsTool ? 'Collapse' : 'Expand'}</span>
                  </button>
                  {showKeyConceptsTool && (
                    <div className="px-4 pb-4 space-y-3">
                      <button
                        onClick={handleGenerateKeyPoints}
                        className="w-full px-4 py-2 bg-primary-600 text-white rounded-lg text-base font-medium hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed"
                        disabled={keyPointsLoading}
                      >
                        {keyPointsLoading ? 'Generating...' : materials?.key_points?.length ? 'Regenerate' : 'Generate'}
                      </button>
                      {loadingMaterials ? (
                        <p className="text-sm text-gray-500">Loading...</p>
                      ) : materials?.key_points && materials.key_points.length > 0 ? (
                        <ul className="list-disc pl-4 space-y-1 text-base text-gray-700">
                          {materials.key_points.map((point, idx) => (
                            <li key={idx}>{point}</li>
                          ))}
                        </ul>
                      ) : (
                        <p className="text-sm text-gray-500">No key points yet.</p>
                      )}
                    </div>
                  )}
                </div>

                <div className={`rounded-xl shadow-sm border ${showFlashcardsTool ? 'bg-white border-gray-200' : 'bg-gray-50 border-gray-200'}`}>
                  <button
                    onClick={() => setShowFlashcardsTool(!showFlashcardsTool)}
                    className="w-full px-4 py-3 flex items-center justify-between text-left"
                  >
                    <div>
                      <h4 className="text-base font-semibold text-gray-900">Flashcards</h4>
                      <p className="text-sm text-gray-500">Auto-generated study cards.</p>
                    </div>
                    <span className="text-sm text-gray-600">{showFlashcardsTool ? 'Collapse' : 'Expand'}</span>
                  </button>
                  {showFlashcardsTool && (
                    <div className="px-4 pb-4 space-y-3">
                      <button
                        onClick={handleGenerateFlashcards}
                        className="w-full px-4 py-2 bg-primary-600 text-white rounded-lg text-base font-medium hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed"
                        disabled={flashcardsLoading}
                      >
                        {flashcardsLoading ? 'Generating...' : materials?.flashcards?.length ? 'Regenerate 5 Cards' : 'Generate 5 Cards'}
                      </button>
                      {loadingMaterials ? (
                        <p className="text-sm text-gray-500">Loading...</p>
                      ) : (
                        <Flashcards flashcards={materials?.flashcards ?? []} />
                      )}
                    </div>
                  )}
                </div>
              </aside>

              <div className="flex-1 flex flex-col">
                {/* Messages */}
                <div className="flex-1 overflow-y-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6">
                  {visibleHistory.length === 0 && !currentAnswer && (
                    <div className="text-center py-12">
                      <div className="w-16 h-16 bg-primary-100 rounded-full flex items-center justify-center mx-auto mb-4">
                        <svg className="w-8 h-8 text-primary-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
                        </svg>
                      </div>
                      <h2 className="text-2xl font-bold text-gray-900 mb-2">Ask a Question</h2>
                      <p className="text-lg text-gray-600">Start a conversation about this lecture</p>
                    </div>
                  )}

                  {/* History */}
                  {visibleHistory.map((item) => (
                    <div key={item.id} className="space-y-2">
                      <div className="flex items-start space-x-3">
                        <div className="flex-shrink-0 w-8 h-8 bg-gray-200 rounded-full flex items-center justify-center">
                          <svg className="w-5 h-5 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                          </svg>
                        </div>
                        <div className="flex-1">
                          <p className="text-base font-medium text-gray-900">{item.question}</p>
                        </div>
                      </div>
                      <div className="flex items-start space-x-3 ml-11">
                        <div className="flex-shrink-0 w-8 h-8 bg-primary-100 rounded-full flex items-center justify-center">
                          <span className="text-primary-600 font-bold text-sm">L</span>
                        </div>
                        <div className="flex-1">
                          <div className="prose prose-base max-w-none">
                            <p className="text-base text-gray-700 whitespace-pre-wrap">{item.answer}</p>
                          </div>
                        </div>
                      </div>
                    </div>
                  ))}

                  {/* Current Answer */}
                  {currentAnswer && (
                    <div className="space-y-2">
                      <div className="flex items-start space-x-3">
                        <div className="flex-shrink-0 w-8 h-8 bg-gray-200 rounded-full flex items-center justify-center">
                          <svg className="w-5 h-5 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                          </svg>
                        </div>
                        <div className="flex-1">
                          <p className="text-sm font-medium text-gray-900">{question}</p>
                        </div>
                      </div>
                      <div className="flex items-start space-x-3 ml-11">
                        <div className="flex-shrink-0 w-8 h-8 bg-primary-100 rounded-full flex items-center justify-center">
                          <span className="text-primary-600 font-bold text-sm">L</span>
                        </div>
                        <div className="flex-1">
                          <div className="prose prose-base max-w-none">
                            <p className="text-base text-gray-700 whitespace-pre-wrap">{currentAnswer.answer}</p>
                            {currentAnswer.citation && (
                              <p className="mt-2 text-sm text-primary-600 font-medium">
                                {currentAnswer.citation}
                              </p>
                            )}
                            {currentAnswer.sources && currentAnswer.sources.length > 0 && (
                              <div className="mt-3">
                                <p className="text-sm font-semibold text-gray-900">Sources</p>
                                <div className="mt-1 space-y-1">
                                  {currentAnswer.sources.map((source, index) => {
                                    const isSlideSource = source.file_type === 'slides' && source.page_number != null;
                                    const handleSourceClick = () => {
                                      if (isSlideSource && slideViewerRef.current) {
                                        slideViewerRef.current.jumpToSlide(source.page_number!);
                                      }
                                    };
                                    return (
                                      <div
                                        key={`${source.lecture_id}-${index}`}
                                        className={`text-sm text-gray-600 ${
                                          isSlideSource ? 'cursor-pointer hover:text-primary-600 hover:underline' : ''
                                        }`}
                                        onClick={isSlideSource ? handleSourceClick : undefined}
                                        title={isSlideSource ? 'Click to jump to slide' : undefined}
                                      >
                                        <span className="font-medium text-primary-600">
                                          {source.lecture_name || 'Lecture'}
                                        </span>
                                        {describeSource(source) && `, ${describeSource(source)}`}
                                      </div>
                                    );
                                  })}
                                </div>
                              </div>
                            )}
                          </div>
                        </div>
                      </div>
                    </div>
                  )}

                  {asking && (
                    <div className="flex items-start space-x-3 ml-11">
                      <div className="flex-shrink-0 w-8 h-8 bg-primary-100 rounded-full flex items-center justify-center">
                        <span className="text-primary-600 font-bold text-sm">L</span>
                      </div>
                      <div className="flex-1">
                        <div className="flex items-center space-x-2 text-gray-500">
                          <svg className="w-5 h-5 animate-spin" fill="none" viewBox="0 0 24 24">
                            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                          </svg>
                          <span>Thinking...</span>
                        </div>
                      </div>
                    </div>
                  )}

                  <div ref={messagesEndRef} />
                </div>

                {/* Input Area */}
                <div className="border-t border-gray-200 bg-white px-4 sm:px-6 lg:px-8 py-4">
                  <form onSubmit={handleSubmit} className="max-w-4xl mx-auto">
                    <div className="flex items-end space-x-4">
                      <div className="flex-1">
                        <textarea
                          value={question}
                          onChange={(e) => setQuestion(e.target.value)}
                          placeholder="Ask a question about this lecture..."
                          rows={1}
                          className="w-full px-4 py-3 text-base border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent resize-none"
                          onKeyDown={(e) => {
                            if (e.key === 'Enter' && !e.shiftKey) {
                              e.preventDefault();
                              handleSubmit(e);
                            }
                          }}
                          disabled={asking}
                        />
                        <p className="mt-2 text-sm text-gray-500">
                          Ask questions about unclear concepts, examples, or exam-related topics.
                        </p>
                      </div>
                      <button
                        type="submit"
                        disabled={!question.trim() || asking}
                        className="px-4 py-2.5 bg-primary-700 text-white rounded-lg text-base font-semibold shadow-sm hover:bg-primary-800 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                      >
                        Ask
                      </button>
                    </div>
                  </form>
                </div>
              </div>
            </div>
          )}
        </div>
    </div>
  );
}

