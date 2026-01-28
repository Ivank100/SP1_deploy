'use client';

import { useState, useEffect, useRef, useCallback } from 'react';
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
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const slideViewerRef = useRef<SlideViewerRef>(null);

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
  }, [lectureId, router]);

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
      setHistory(response.queries);
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

  const renderFrequencyPolygon = () => {
    if (loadingAnalytics) {
      return <p className="text-sm text-gray-500">Loading frequency polygon...</p>;
    }
    if (analyticsError) {
      return <p className="text-sm text-red-600">{analyticsError}</p>;
    }
    if (!lectureAnalytics || lectureAnalytics.bins.length === 0) {
      return (
        <p className="text-sm text-gray-500">
          No questions yet. Student questions will appear here once the lecture becomes active.
        </p>
      );
    }

    const bins = lectureAnalytics.bins;
    const lectureCounts = bins.map((b) => b.count);
    const courseCounts = bins.map((b) => b.course_avg ?? 0);
    const courseQuestionTotal = lectureAnalytics.course_question_total ?? 0;
    const courseLectureCount = lectureAnalytics.course_lecture_count ?? 0;
    const courseAvgEligible =
      courseQuestionTotal >= 5 || (courseLectureCount > 0 && courseQuestionTotal >= courseLectureCount);
    const maxValue = Math.max(1, ...lectureCounts, ...(courseAvgEligible ? courseCounts : []));

    const width = 640;
    const height = 220;
    const padding = 24;
    const totalPoints = bins.length + 2;
    const xStep = totalPoints > 1 ? (width - padding * 2) / (totalPoints - 1) : 0;

    const yForValue = (value: number) =>
      height - padding - (value / maxValue) * (height - padding * 2);

    const formatRangeLabel = (bin: (typeof bins)[number]) => {
      const start = bin.start_min ?? bin.start_pct;
      const end = bin.end_min ?? bin.end_pct;
      const unit = bin.start_min != null && bin.end_min != null ? 'min' : '%';
      return `${start}-${end} ${unit}`;
    };

    const lectureSeries = [
      { x: padding, y: yForValue(0), value: 0, isEndpoint: true, label: 'Before start' },
      ...bins.map((bin, idx) => ({
        x: padding + (idx + 1) * xStep,
        y: yForValue(bin.count),
        value: bin.count,
        label: formatRangeLabel(bin),
        isEndpoint: false,
      })),
      {
        x: padding + (totalPoints - 1) * xStep,
        y: yForValue(0),
        value: 0,
        isEndpoint: true,
        label: 'After end',
      },
    ];

    const courseSeries = [
      { x: padding, y: yForValue(0), value: 0, isEndpoint: true },
      ...bins.map((bin, idx) => ({
        x: padding + (idx + 1) * xStep,
        y: yForValue(bin.course_avg ?? 0),
        value: bin.course_avg ?? 0,
      })),
      {
        x: padding + (totalPoints - 1) * xStep,
        y: yForValue(0),
        value: 0,
        isEndpoint: true,
      },
    ];

    const buildSegments = (points: Array<{ x: number; y: number; value: number; isEndpoint?: boolean }>) => {
      const segments: string[] = [];
      let current: string[] = [];
      for (let i = 0; i < points.length - 1; i += 1) {
        const start = points[i];
        const end = points[i + 1];
        const connect =
          (start.value > 0 && end.value > 0) ||
          (start.isEndpoint && end.value > 0) ||
          (end.isEndpoint && start.value > 0);
        if (connect) {
          if (current.length === 0) {
            current.push(`${start.x},${start.y}`);
          }
          current.push(`${end.x},${end.y}`);
        } else if (current.length > 0) {
          segments.push(current.join(' '));
          current = [];
        }
      }
      if (current.length > 0) {
        segments.push(current.join(' '));
      }
      return segments;
    };

    const lectureSegments = buildSegments(lectureSeries);
    const courseSegments = courseAvgEligible ? buildSegments(courseSeries) : [];

    return (
      <div>
        <svg viewBox={`0 0 ${width} ${height}`} className="w-full h-56">
          <line x1={padding} y1={height - padding} x2={width - padding} y2={height - padding} stroke="#E5E7EB" strokeWidth="1" />
          <line x1={padding} y1={padding} x2={padding} y2={height - padding} stroke="#E5E7EB" strokeWidth="1" />

          {lectureSegments.map((segment, idx) => (
            <polyline
              key={`lecture-segment-${idx}`}
              fill="none"
              stroke="#2563EB"
              strokeWidth="2"
              points={segment}
            />
          ))}
          {courseAvgEligible &&
            courseSegments.map((segment, idx) => (
              <polyline
                key={`course-segment-${idx}`}
                fill="none"
                stroke="#10B981"
                strokeWidth="2"
                strokeDasharray="4 4"
                points={segment}
              />
            ))}

          {lectureSeries.map((point, idx) => {
            const isZero = point.value === 0;
            const isEndpoint = point.isEndpoint;
            const label = isEndpoint
              ? `${point.label}: 0 questions`
              : point.value > 0
                ? `${point.value} question${point.value === 1 ? '' : 's'} at ${point.label}`
                : `No data at ${point.label}`;
            const fill = isZero ? '#FFFFFF' : '#2563EB';
            const stroke = isZero ? '#94A3B8' : '#2563EB';
            return (
              <circle
                key={`lecture-point-${idx}`}
                cx={point.x}
                cy={point.y}
                r={isEndpoint ? 3 : 4}
                fill={fill}
                stroke={stroke}
                strokeWidth={isZero ? 2 : 1}
              >
                <title>{label}</title>
              </circle>
            );
          })}
        </svg>
        <div className="flex justify-between text-xs text-gray-500 mt-2">
          <span>
            {bins[0].start_min ?? bins[0].start_pct}-{bins[0].end_min ?? bins[0].end_pct}{' '}
            {bins[0].start_min != null ? 'min' : '%'}
          </span>
          <span>
            {bins[bins.length - 1].start_min ?? bins[bins.length - 1].start_pct}-
            {bins[bins.length - 1].end_min ?? bins[bins.length - 1].end_pct}{' '}
            {bins[bins.length - 1].end_min != null ? 'min' : '%'}
          </span>
        </div>
        {bins.some((bin) => bin.start_min != null && bin.end_min != null) && (
          <div
            className="mt-2 grid text-[10px] text-gray-400"
            style={{ gridTemplateColumns: `repeat(${bins.length}, minmax(0, 1fr))` }}
          >
            {bins.map((bin, idx) => {
              if (bin.start_min == null || bin.end_min == null) {
                return <span key={`bin-midpoint-${idx}`} />;
              }
              const midpoint = Math.round((bin.start_min + bin.end_min) / 2);
              return (
                <span key={`bin-midpoint-${idx}`} className="text-center">
                  {midpoint} min
                </span>
              );
            })}
          </div>
        )}
        <div className="flex items-center gap-4 mt-3 text-sm text-gray-600">
          <div className="flex items-center gap-2">
            <span className="inline-block w-3 h-0.5 bg-blue-600" />
            <span>This lecture</span>
          </div>
          {courseAvgEligible && (
            <div className="flex items-center gap-2">
              <span className="inline-block w-3 h-0.5 bg-emerald-500 border-t border-dashed border-emerald-500" />
              <span>Course average</span>
            </div>
          )}
        </div>
        {lectureAnalytics.total_questions < 3 && (
          <p className="mt-3 text-xs text-amber-600">
            Limited data — trends may not yet be representative.
          </p>
        )}
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
                  className="text-sm font-medium text-gray-700 hover:text-primary-600"
                >
                  ← Back to Course
                </Link>
              ) : (
              <Link
                href="/"
                className="text-sm font-medium text-gray-700 hover:text-primary-600"
              >
                ← Back to Courses
              </Link>
              )}
            </div>
            {currentUser ? (
              <div className="flex items-center space-x-3">
                <div className="flex flex-col items-end">
                  <span className="text-sm font-medium text-gray-900">{currentUser.email}</span>
                  <span className="text-xs text-gray-500 capitalize">{currentUser.role}</span>
                </div>
                <button
                  onClick={() => {
                    apiClient.logout();
                    router.push('/auth/login');
                  }}
                  className="px-3 py-1.5 text-sm font-medium text-white bg-primary-600 hover:bg-primary-700 rounded-md transition-colors"
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
              <h1 className="text-xl font-bold text-gray-900">{lecture.original_name}</h1>
              <p className="text-sm text-gray-500">
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
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-2 text-sm text-gray-600 flex items-center gap-2 min-w-0">
          <span className="font-medium text-gray-900 truncate max-w-[45%]">
            {courseName || (lecture.course_id ? `Course ${lecture.course_id}` : 'Course')}
          </span>
          <span className="text-gray-400">→</span>
          <span className="text-gray-700 truncate">{lecture.original_name}</span>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 flex max-w-7xl mx-auto w-full">
        {/* Chat Area */}
        <div className="flex-1 flex flex-col">
          {lecture.file_type === 'slides' && (
            <div className="px-4 sm:px-6 lg:px-8 pt-6">
              <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 mb-6">
                <div className="flex items-center justify-between mb-4">
                  <div>
                    <h3 className="text-lg font-semibold text-gray-900">Slide Viewer</h3>
                    <p className="text-sm text-gray-500">
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
                    <h3 className="text-lg font-semibold text-gray-900">Audio Playback & Transcript</h3>
                    <p className="text-sm text-gray-500">
                      Listen to the lecture and jump to specific segments via the transcript.
                    </p>
                  </div>
                  <button
                    onClick={handleTranscribeAudio}
                    disabled={transcribing}
                    className="px-4 py-2 bg-primary-600 text-white rounded-lg text-sm font-medium hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {transcribing
                      ? 'Transcribing...'
                      : lecture.has_transcript
                      ? 'Regenerate Transcript'
                      : 'Transcribe Audio'}
                  </button>
                </div>
                {transcriptionError && (
                  <div className="mb-4 text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg p-3">
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
                      <p className="text-sm text-gray-500 mt-4">
                        Transcript not generated yet. Run transcription to enable timestamped search.
                      </p>
                    )}
                  </>
                ) : (
                  <p className="text-sm text-gray-500">Audio file unavailable.</p>
                )}
              </div>
            </div>
          )}
          {isInstructor ? (
            <div className="flex-1 overflow-y-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6">
              <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
                <div className="flex items-center justify-between mb-4">
                  <div>
                    <h2 className="text-2xl font-bold text-gray-900">Lecture Analytics</h2>
                    <p className="text-sm text-gray-500">Engagement and question activity for this lecture.</p>
                  </div>
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                  <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
                    <p className="text-xs text-gray-500 mb-1">Total Questions</p>
                    <p className="text-2xl font-bold text-gray-900">
                      {lectureAnalytics?.total_questions ?? 0}
                    </p>
                  </div>
                  <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
                    <p className="text-xs text-gray-500 mb-1">Active Students</p>
                    <p className="text-2xl font-bold text-gray-900">
                      {lectureAnalytics?.active_students ?? 0}
                    </p>
                  </div>
                  <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
                    <p className="text-xs text-gray-500 mb-1">Peak Confusion Time (min)</p>
                    <p className="text-lg font-semibold text-gray-900">
                      {lectureAnalytics?.peak_confusion_range || 'N/A'}
                    </p>
                  </div>
                  <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
                    <p className="text-xs text-gray-500 mb-1">Top Confused Question</p>
                    <p className="text-sm font-semibold text-gray-900 line-clamp-3">
                      {lectureAnalytics?.top_confused_question || 'N/A'}
                    </p>
                  </div>
                </div>
              </div>

              <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
                <div className="flex items-center justify-between mb-4">
                  <div>
                    <h3 className="text-lg font-semibold text-gray-900">Questions Over Time</h3>
                    <p className="text-sm text-gray-500">
                      Helps identify when students are most confused during the lecture.
                    </p>
                  </div>
                </div>
                {renderFrequencyPolygon()}
              </div>

              <div className={`rounded-xl shadow-sm border ${showRecentQuestions ? 'bg-white border-gray-200' : 'bg-gray-50 border-gray-200'}`}>
                <button
                  onClick={() => setShowRecentQuestions(!showRecentQuestions)}
                  className="w-full px-6 py-4 flex items-center justify-between text-left"
                >
                  <div>
                    <h3 className="text-lg font-semibold text-gray-900">Recent Questions</h3>
                    <p className="text-sm text-gray-500">Latest questions submitted by students.</p>
                  </div>
                  <span className="text-sm text-gray-600">{showRecentQuestions ? '−' : '+'}</span>
                </button>
                {showRecentQuestions && (
                  <div className="px-6 pb-6">
                    {history.length === 0 ? (
                      <p className="text-sm text-gray-500">
                        No questions yet. Student questions will appear here once the lecture becomes active.
                      </p>
                    ) : (
                      <div className="space-y-3">
                        {history.map((item) => (
                          <div key={item.id} className="border border-gray-200 rounded-lg p-4">
                            <div className="flex items-center justify-between mb-2">
                              <div className="text-sm font-medium text-gray-900">
                                {item.user_email || 'Student'}
                              </div>
                              <div className="flex items-center gap-3 text-xs text-gray-500">
                                <span>{formatHistoryTime(item.created_at)}</span>
                                <span className="px-2 py-0.5 rounded-full bg-green-50 text-green-700 border border-green-100">
                                  Answered
                                </span>
                              </div>
                            </div>
                            <p className="text-sm text-gray-800 font-medium">{item.question}</p>
                            <p className="text-sm text-gray-600 mt-2 line-clamp-3">{item.answer}</p>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>
          ) : (
            <>
              {/* Messages */}
              <div className="flex-1 overflow-y-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6">
                {history.length === 0 && !currentAnswer && (
                  <div className="text-center py-12">
                    <div className="w-16 h-16 bg-primary-100 rounded-full flex items-center justify-center mx-auto mb-4">
                      <svg className="w-8 h-8 text-primary-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
                      </svg>
                    </div>
                    <h2 className="text-2xl font-bold text-gray-900 mb-2">Ask a Question</h2>
                    <p className="text-gray-600">Start a conversation about this lecture</p>
                  </div>
                )}

                {/* History */}
                {history.map((item) => (
                  <div key={item.id} className="space-y-2">
                    <div className="flex items-start space-x-3">
                      <div className="flex-shrink-0 w-8 h-8 bg-gray-200 rounded-full flex items-center justify-center">
                        <svg className="w-5 h-5 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                        </svg>
                      </div>
                      <div className="flex-1">
                        <p className="text-sm font-medium text-gray-900">{item.question}</p>
                      </div>
                    </div>
                    <div className="flex items-start space-x-3 ml-11">
                      <div className="flex-shrink-0 w-8 h-8 bg-primary-100 rounded-full flex items-center justify-center">
                        <span className="text-primary-600 font-bold text-sm">L</span>
                      </div>
                      <div className="flex-1">
                        <div className="prose prose-sm max-w-none">
                          <p className="text-gray-700 whitespace-pre-wrap">{item.answer}</p>
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
                        <div className="prose prose-sm max-w-none">
                          <p className="text-gray-700 whitespace-pre-wrap">{currentAnswer.answer}</p>
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
                        className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent resize-none"
                        onKeyDown={(e) => {
                          if (e.key === 'Enter' && !e.shiftKey) {
                            e.preventDefault();
                            handleSubmit(e);
                          }
                        }}
                        disabled={asking}
                      />
                      <p className="mt-2 text-xs text-gray-500">
                        Ask questions about unclear concepts, examples, or exam-related topics.
                      </p>
                    </div>
                    <button
                      type="submit"
                      disabled={!question.trim() || asking}
                      className="px-4 py-2.5 bg-primary-700 text-white rounded-lg text-sm font-semibold shadow-sm hover:bg-primary-800 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                    >
                      Ask
                    </button>
                  </div>
                </form>
              </div>
            </>
          )}
        </div>
      </div>

      {/* AI Teaching Tools */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-4">
        <div>
          <h3 className="text-lg font-semibold text-gray-900">AI Teaching Tools</h3>
          <p className="text-sm text-gray-500">
            Summaries and tools to help you understand this lecture faster.
          </p>
        </div>
        <div className="space-y-4">
          <div className={`rounded-xl shadow-sm border ${showSummaryTool ? 'bg-white border-gray-200' : 'bg-gray-50 border-gray-200'}`}>
            <button
              onClick={() => setShowSummaryTool(!showSummaryTool)}
              className="w-full px-5 py-4 flex items-center justify-between text-left"
            >
              <div>
                <h3 className="text-base font-semibold text-gray-900">Lecture Summary</h3>
                <p className="text-sm text-gray-500">Generate a concise overview of this lecture.</p>
              </div>
              <span className="text-sm text-gray-600">{showSummaryTool ? 'Collapse' : 'Expand'}</span>
            </button>
            {showSummaryTool && (
              <div className="px-5 pb-5">
                <div className="flex items-center justify-between mb-3">
                  <div />
                  <button
                    onClick={handleGenerateSummary}
                    className="px-4 py-2 bg-primary-600 text-white rounded-lg text-sm font-medium hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed"
                    disabled={summaryLoading}
                  >
                    {summaryLoading ? 'Generating...' : materials?.summary ? 'Regenerate' : 'Generate'}
                  </button>
                </div>
                {loadingMaterials ? (
                  <p className="text-sm text-gray-500">Loading study materials...</p>
                ) : materials?.summary ? (
                  <p className="text-gray-700 whitespace-pre-wrap">{materials.summary}</p>
                ) : (
                  <p className="text-sm text-gray-500">No summary available yet.</p>
                )}
              </div>
            )}
          </div>

          <div className={`rounded-xl shadow-sm border ${showKeyConceptsTool ? 'bg-white border-gray-200' : 'bg-gray-50 border-gray-200'}`}>
            <button
              onClick={() => setShowKeyConceptsTool(!showKeyConceptsTool)}
              className="w-full px-5 py-4 flex items-center justify-between text-left"
            >
              <div>
                <h3 className="text-base font-semibold text-gray-900">Key Concepts</h3>
                <p className="text-sm text-gray-500">Exam-focused highlights and definitions.</p>
              </div>
              <span className="text-sm text-gray-600">{showKeyConceptsTool ? 'Collapse' : 'Expand'}</span>
            </button>
            {showKeyConceptsTool && (
              <div className="px-5 pb-5">
                <div className="flex items-center justify-between mb-3">
                  <div />
                  <button
                    onClick={handleGenerateKeyPoints}
                    className="px-4 py-2 bg-primary-600 text-white rounded-lg text-sm font-medium hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed"
                    disabled={keyPointsLoading}
                  >
                    {keyPointsLoading ? 'Generating...' : materials?.key_points?.length ? 'Regenerate' : 'Generate'}
                  </button>
                </div>
                {loadingMaterials ? (
                  <p className="text-sm text-gray-500">Loading study materials...</p>
                ) : materials?.key_points && materials.key_points.length > 0 ? (
                  <ul className="list-disc pl-5 space-y-2 text-gray-700">
                    {materials.key_points.map((point, idx) => (
                      <li key={idx}>{point}</li>
                    ))}
                  </ul>
                ) : (
                  <p className="text-sm text-gray-500">Key points will appear here after generation.</p>
                )}
              </div>
            )}
          </div>

          <div className={`rounded-xl shadow-sm border ${showFlashcardsTool ? 'bg-white border-gray-200' : 'bg-gray-50 border-gray-200'}`}>
            <button
              onClick={() => setShowFlashcardsTool(!showFlashcardsTool)}
              className="w-full px-5 py-4 flex items-center justify-between text-left"
            >
              <div>
                <div className="flex items-center gap-2">
                  <h3 className="text-base font-semibold text-gray-900">Flashcards</h3>
                  <span className="text-xs px-2 py-0.5 rounded-full bg-amber-50 text-amber-700 border border-amber-200">
                    Recommended for revision
                  </span>
                </div>
                <p className="text-sm text-gray-500">Auto-generated from lecture content.</p>
              </div>
              <span className="text-sm text-gray-600">{showFlashcardsTool ? 'Collapse' : 'Expand'}</span>
            </button>
            {showFlashcardsTool && (
              <div className="px-5 pb-5">
                <div className="flex items-center justify-between mb-3">
                  <div />
                  <button
                    onClick={handleGenerateFlashcards}
                    className="px-4 py-2 bg-primary-600 text-white rounded-lg text-sm font-medium hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed"
                    disabled={flashcardsLoading}
                  >
                    {flashcardsLoading ? 'Generating...' : materials?.flashcards?.length ? 'Regenerate 10 Cards' : 'Generate 10 Cards'}
                  </button>
                </div>
                {loadingMaterials ? (
                  <p className="text-sm text-gray-500">Loading study materials...</p>
                ) : (
                  <Flashcards flashcards={materials?.flashcards ?? []} />
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

