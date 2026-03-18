'use client';

/**
 * This hook manages state and actions for the lecture workspace workflow.
 * It loads data, tracks UI state, and returns handlers used by page components.
 */
import { useCallback, useEffect, useMemo, useState } from 'react';
import {
  LectureAnalyticsResponse,
  LectureResource,
  StudyMaterialsResponse,
  TranscriptSegment,
} from '@/lib/api';
import { apiClient } from '@/lib/api';
import { buildAudioSourceUrl, buildLecturePreviewUrl } from '@/lib/lectureAnalytics';
import { useLecturePage } from '@/hooks/useLecturePage';

type RouterLike = {
  push: (href: string) => void;
};

export type LecturePanel = 'all' | 'analytics' | 'management' | 'resources' | 'questions';

export function useLectureWorkspace(lectureId: number, router: RouterLike) {
  const { lecture, setLecture, currentUser, loading, courseName, loadLecture } = useLecturePage(lectureId, router);

  const [materials, setMaterials] = useState<StudyMaterialsResponse | null>(null);
  const [loadingMaterials, setLoadingMaterials] = useState(true);
  const [summaryLoading, setSummaryLoading] = useState(false);
  const [keyPointsLoading, setKeyPointsLoading] = useState(false);
  const [flashcardsLoading, setFlashcardsLoading] = useState(false);
  const [flashcardCount, setFlashcardCount] = useState(5);

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

  const [showSummaryTool, setShowSummaryTool] = useState(true);
  const [showKeyConceptsTool, setShowKeyConceptsTool] = useState(true);
  const [showFlashcardsTool, setShowFlashcardsTool] = useState(true);
  const [activeLecturePanel, setActiveLecturePanel] = useState<LecturePanel>('all');

  const loadMaterials = useCallback(async () => {
    try {
      setLoadingMaterials(true);
      const data = await apiClient.getStudyMaterials(lectureId);
      setMaterials(data);
    } catch (error) {
      console.error('Failed to load study materials:', error);
    } finally {
      setLoadingMaterials(false);
    }
  }, [lectureId]);

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

  useEffect(() => {
    void loadMaterials();
    void loadResources();
  }, [loadMaterials, loadResources]);

  useEffect(() => {
    if (lecture?.file_type === 'audio' && lecture.has_transcript) {
      void loadTranscript();
    } else {
      setTranscript([]);
    }

    if (lecture?.file_type === 'slides') {
      void loadSlides();
    } else {
      setSlides([]);
    }
  }, [lecture?.file_type, lecture?.has_transcript, loadSlides, loadTranscript]);

  useEffect(() => {
    if (currentUser?.role === 'instructor') {
      void loadLectureAnalytics();
    }
  }, [currentUser?.role, loadLectureAnalytics]);

  const handleReplaceLectureFile = useCallback(
    async (file: File) => {
      if (!file) {
        return;
      }

      try {
        await apiClient.replaceLectureFile(lectureId, file);
        await loadLecture();
        await loadLectureAnalytics();
      } catch (error: any) {
        alert(error.response?.data?.detail || 'Failed to replace lecture file');
      }
    },
    [lectureId, loadLecture, loadLectureAnalytics]
  );

  const handleRenameLecture = useCallback(async () => {
    if (!lecture) {
      return;
    }

    const nextName = prompt('Rename lecture', lecture.original_name);
    if (!nextName || !nextName.trim()) {
      return;
    }

    try {
      const updated = await apiClient.renameLecture(lectureId, nextName.trim());
      setLecture(updated);
    } catch (error: any) {
      alert(error.response?.data?.detail || 'Failed to rename lecture');
    }
  }, [lecture, lectureId, setLecture]);

  const handleArchiveLecture = useCallback(async () => {
    if (!confirm('Archive this lecture? It will be hidden from the course list.')) {
      return;
    }

    try {
      await apiClient.archiveLecture(lectureId);
      router.push('/');
    } catch (error: any) {
      alert(error.response?.data?.detail || 'Failed to archive lecture');
    }
  }, [lectureId, router]);

  const handleAddResource = useCallback(async () => {
    const title = prompt('Resource title');
    if (!title || !title.trim()) {
      return;
    }

    const url = prompt('Resource URL');
    if (!url || !url.trim()) {
      return;
    }

    try {
      const resource = await apiClient.addLectureResource(lectureId, title.trim(), url.trim());
      setLectureResources((prev) => [resource, ...prev]);
    } catch (error: any) {
      alert(error.response?.data?.detail || 'Failed to add resource');
    }
  }, [lectureId]);

  const handleDeleteResource = useCallback(async (resourceId: number) => {
    if (!confirm('Remove this resource?')) {
      return;
    }

    try {
      await apiClient.deleteLectureResource(lectureId, resourceId);
      setLectureResources((prev) => prev.filter((resource) => resource.id !== resourceId));
    } catch (error: any) {
      alert(error.response?.data?.detail || 'Failed to delete resource');
    }
  }, [lectureId]);

  const handleDownloadLecture = useCallback(async () => {
    if (!lecture?.file_path) {
      return;
    }

    try {
      const blob = await apiClient.downloadLectureFile(lectureId);
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = lecture.original_name || 'lecture';
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (error: any) {
      alert(error.response?.data?.detail || 'Failed to download lecture');
    }
  }, [lecture, lectureId]);

  const handleTranscribeAudio = useCallback(async () => {
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
  }, [lectureId, loadLecture, loadTranscript]);

  const handleGenerateSummary = useCallback(async () => {
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
  }, [lectureId]);

  const handleGenerateKeyPoints = useCallback(async () => {
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
  }, [lectureId]);

  const handleGenerateFlashcards = useCallback(async () => {
    setFlashcardsLoading(true);
    try {
      const regenerate = (materials?.flashcards?.length ?? 0) > 0;
      const response = await apiClient.generateFlashcards(lectureId, regenerate, flashcardCount);
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
  }, [flashcardCount, lectureId, materials?.flashcards?.length]);

  const isInstructor = currentUser?.role === 'instructor';
  const audioSourceUrl = useMemo(() => buildAudioSourceUrl(lecture), [lecture]);
  const lecturePreviewUrl = useMemo(() => buildLecturePreviewUrl(lecture), [lecture]);

  return {
    activeLecturePanel,
    analyticsError,
    audioSourceUrl,
    courseName,
    currentUser,
    flashcardCount,
    flashcardsLoading,
    handleAddResource,
    handleArchiveLecture,
    handleDeleteResource,
    handleDownloadLecture,
    handleGenerateFlashcards,
    handleGenerateKeyPoints,
    handleGenerateSummary,
    handleRenameLecture,
    handleReplaceLectureFile,
    handleTranscribeAudio,
    isInstructor,
    keyPointsLoading,
    lecture,
    lectureAnalytics,
    lecturePreviewUrl,
    lectureResources,
    loading,
    loadingAnalytics,
    loadingMaterials,
    loadingResources,
    loadingSlides,
    loadingTranscript,
    materials,
    setActiveLecturePanel,
    setFlashcardCount,
    setShowFlashcardsTool,
    setShowKeyConceptsTool,
    setShowSummaryTool,
    showFlashcardsTool,
    showKeyConceptsTool,
    showSummaryTool,
    slides,
    summaryLoading,
    transcript,
    transcribing,
    transcriptionError,
  };
}

export type LectureWorkspaceState = ReturnType<typeof useLectureWorkspace>;
