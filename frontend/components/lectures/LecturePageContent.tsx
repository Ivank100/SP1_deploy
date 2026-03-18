'use client';

/**
 * This component renders lecture-related UI for lecture page content.
 * It packages one part of the lecture experience into a reusable frontend unit.
 */
import { useMemo, useRef } from 'react';
import type { MutableRefObject, ReactNode } from 'react';
import Link from 'next/link';
import { apiClient } from '@/lib/api';
import Flashcards from '@/components/reusable/Flashcards';
import AudioPlayer from '@/components/reusable/AudioPlayer';
import SlideViewer, { SlideViewerRef } from '@/components/reusable/SlideViewer';
import { describeSource } from '@/lib/formatters';
import {
  formatHeatmapRange,
  formatHistoryTime,
  getHeatmapBins,
  getPeakConfusedPages,
  LectureQuestionSort,
} from '@/lib/lectureAnalytics';
import type { LectureQuestionsState } from '@/hooks/useLectureQuestions';
import type { LectureWorkspaceState, LecturePanel } from '@/hooks/useLectureWorkspace';

type LecturePageContentProps = {
  onLogout: () => void;
  questions: LectureQuestionsState;
  workspace: LectureWorkspaceState;
};

export default function LecturePageContent({
  onLogout,
  questions,
  workspace,
}: LecturePageContentProps) {
  const slideViewerRef = useRef<SlideViewerRef>(null);
  const replaceFileInputRef = useRef<HTMLInputElement>(null);

  const {
    activeLecturePanel,
    analyticsError,
    audioSourceUrl,
    courseName,
    currentUser,
    flashcardCount,
    flashcardsLoading,
    handleAddResource,
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
  } = workspace;

  const {
    activeAnswerId,
    answerDrafts,
    asking,
    chatMessageList,
    currentAnswer,
    faqQuestionIds,
    handleSubmit,
    hiddenQuestionIds,
    history,
    loadHistory,
    manualAnswers,
    messagesEndRef,
    pinnedQuestionIds,
    question,
    questionFilter,
    questionSort,
    setActiveAnswerId,
    setAnswerDrafts,
    setManualAnswers,
    setQuestion,
    setQuestionFilter,
  setQuestionSort,
  setShowRecentQuestions,
  showRecentQuestions,
  sortedHistory,
  toggleFaqQuestion,
    toggleHiddenQuestion,
    togglePinnedQuestion,
  } = questions;

  const heatmapBins = useMemo(() => getHeatmapBins(lecture, history), [history, lecture]);
  const peakConfusedPages = useMemo(() => getPeakConfusedPages(lecture, history), [history, lecture]);

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
          <Link href="/" className="mt-6 inline-block text-primary-600 hover:text-primary-700 font-medium">
            ← Back to Lectures
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      <header className="bg-white border-b border-gray-200 sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <div className="flex items-center space-x-4">
              {lecture.course_id ? (
                <Link href={`/courses/${lecture.course_id}`} className="text-base font-medium text-gray-700 hover:text-primary-600">
                  ← Back to Course
                </Link>
              ) : (
                <Link href="/" className="text-base font-medium text-gray-700 hover:text-primary-600">
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
                  onClick={onLogout}
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

      <div className="flex-1 flex max-w-7xl mx-auto w-full">
        {isInstructor ? (
          <div className="flex-1 flex w-full">
            <InstructorNavigation
              activeLecturePanel={activeLecturePanel}
              onChangePanel={setActiveLecturePanel}
            />
            <div className="flex-1 flex flex-col min-w-0">
              <div className="flex-1 flex flex-col">
                <LectureMediaPanel
                  audioSourceUrl={audioSourceUrl}
                  handleTranscribeAudio={handleTranscribeAudio}
                  lecture={lecture}
                  loadingSlides={loadingSlides}
                  loadingTranscript={loadingTranscript}
                  slideViewerRef={slideViewerRef}
                  slides={slides}
                  transcript={transcript}
                  transcribing={transcribing}
                  transcriptionError={transcriptionError}
                />

                <div className="flex-1 overflow-y-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6">
                  {(activeLecturePanel === 'all' || activeLecturePanel === 'analytics') && (
                    <LectureAnalyticsPanel
                      analyticsError={analyticsError}
                      heatmapBins={heatmapBins}
                      lecture={lecture}
                      lectureAnalytics={lectureAnalytics}
                      loadingAnalytics={loadingAnalytics}
                      peakConfusedPages={peakConfusedPages}
                    />
                  )}

                  {(activeLecturePanel === 'all' || activeLecturePanel === 'management') && (
                    <LectureManagementPanel
                      lecture={lecture}
                      onRenameLecture={handleRenameLecture}
                      onReplaceLectureClick={() => replaceFileInputRef.current?.click()}
                      replaceFileInput={
                        <input
                          ref={replaceFileInputRef}
                          type="file"
                          accept=".pdf"
                          className="hidden"
                          onChange={async (e) => {
                            const file = e.target.files?.[0];
                            if (file) {
                              await handleReplaceLectureFile(file);
                              await loadHistory();
                            }
                            e.currentTarget.value = '';
                          }}
                        />
                      }
                    />
                  )}

                  {(activeLecturePanel === 'all' || activeLecturePanel === 'resources') && (
                    <LectureResourcesPanel
                      lecture={lecture}
                      lecturePreviewUrl={lecturePreviewUrl}
                      lectureResources={lectureResources}
                      loadingResources={loadingResources}
                      onAddResource={handleAddResource}
                      onDeleteResource={handleDeleteResource}
                      onDownloadLecture={handleDownloadLecture}
                    />
                  )}

                  {(activeLecturePanel === 'all' || activeLecturePanel === 'questions') && (
                    <LectureQuestionsPanel
                      activeAnswerId={activeAnswerId}
                      answerDrafts={answerDrafts}
                      faqQuestionIds={faqQuestionIds}
                      hiddenQuestionIds={hiddenQuestionIds}
                      manualAnswers={manualAnswers}
                      pinnedQuestionIds={pinnedQuestionIds}
                      questionFilter={questionFilter}
                      questionSort={questionSort}
                      setActiveAnswerId={setActiveAnswerId}
                      setAnswerDrafts={setAnswerDrafts}
                      setManualAnswers={setManualAnswers}
                      setQuestionFilter={setQuestionFilter}
                      setQuestionSort={setQuestionSort}
                      setShowRecentQuestions={setShowRecentQuestions}
                      showRecentQuestions={showRecentQuestions}
                      sortedHistory={sortedHistory}
                      toggleFaqQuestion={toggleFaqQuestion}
                      toggleHiddenQuestion={toggleHiddenQuestion}
                      togglePinnedQuestion={togglePinnedQuestion}
                    />
                  )}
                </div>
              </div>
            </div>
          </div>
        ) : (
          <div className="flex-1 flex min-h-0">
            <LectureStudySidebar
              flashcardCount={flashcardCount}
              flashcardsLoading={flashcardsLoading}
              handleGenerateFlashcards={handleGenerateFlashcards}
              handleGenerateKeyPoints={handleGenerateKeyPoints}
              handleGenerateSummary={handleGenerateSummary}
              keyPointsLoading={keyPointsLoading}
              loadingMaterials={loadingMaterials}
              materials={materials}
              setFlashcardCount={setFlashcardCount}
              setShowFlashcardsTool={setShowFlashcardsTool}
              setShowKeyConceptsTool={setShowKeyConceptsTool}
              setShowSummaryTool={setShowSummaryTool}
              showFlashcardsTool={showFlashcardsTool}
              showKeyConceptsTool={showKeyConceptsTool}
              showSummaryTool={showSummaryTool}
              summaryLoading={summaryLoading}
            />

            <LectureChatPanel
              asking={asking}
              chatMessageList={chatMessageList}
              currentAnswer={currentAnswer}
              handleSubmit={handleSubmit}
              messagesEndRef={messagesEndRef}
              question={question}
              setQuestion={setQuestion}
              slideViewerRef={slideViewerRef}
            />
          </div>
        )}
      </div>
    </div>
  );
}

function InstructorNavigation({
  activeLecturePanel,
  onChangePanel,
}: {
  activeLecturePanel: LecturePanel;
  onChangePanel: (panel: LecturePanel) => void;
}) {
  return (
    <aside className="bg-white border-r border-gray-200 w-64 min-w-64 p-5 h-fit sticky top-[7.5rem]">
      <h4 className="text-base font-semibold text-gray-900 mb-4">Navigation</h4>
      <div className="space-y-2">
        {(['all', 'analytics', 'management', 'resources', 'questions'] as const).map((panel) => (
          <button
            key={panel}
            onClick={() => onChangePanel(panel)}
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
  );
}

function LectureMediaPanel({
  audioSourceUrl,
  handleTranscribeAudio,
  lecture,
  loadingSlides,
  loadingTranscript,
  slideViewerRef,
  slides,
  transcript,
  transcribing,
  transcriptionError,
}: {
  audioSourceUrl: string;
  handleTranscribeAudio: () => void;
  lecture: NonNullable<LectureWorkspaceState['lecture']>;
  loadingSlides: boolean;
  loadingTranscript: boolean;
  slideViewerRef: MutableRefObject<SlideViewerRef | null>;
  slides: LectureWorkspaceState['slides'];
  transcript: LectureWorkspaceState['transcript'];
  transcribing: boolean;
  transcriptionError: string | null;
}) {
  return (
    <>
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
            <SlideViewer
              ref={(instance) => {
                slideViewerRef.current = instance;
              }}
              slides={slides}
            />
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
                  <AudioPlayer sourceUrl={audioSourceUrl} segments={lecture.has_transcript ? transcript : []} />
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
    </>
  );
}

function LectureAnalyticsPanel({
  analyticsError,
  heatmapBins,
  lecture,
  lectureAnalytics,
  loadingAnalytics,
  peakConfusedPages,
}: {
  analyticsError: string | null;
  heatmapBins: ReturnType<typeof getHeatmapBins>;
  lecture: NonNullable<LectureWorkspaceState['lecture']>;
  lectureAnalytics: LectureWorkspaceState['lectureAnalytics'];
  loadingAnalytics: boolean;
  peakConfusedPages: string | null;
}) {
  return (
    <>
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className="text-2xl font-bold text-gray-900">Lecture Analytics</h2>
            <p className="text-base text-gray-500">Engagement and question activity for this lecture.</p>
          </div>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <MetricCard label="Total Questions" value={lectureAnalytics?.total_questions ?? 0} />
          <MetricCard label="Active Students" value={lectureAnalytics?.active_students ?? 0} />
          <MetricCard
            label="Peak Confused Lecture Pages"
            value={peakConfusedPages ?? lectureAnalytics?.peak_confusion_range ?? 'N/A'}
            compact
          />
          <MetricCard
            label="Top Confused Question"
            value={lectureAnalytics?.top_confused_question || 'N/A'}
            compact
          />
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
        <HeatmapContent
          analyticsError={analyticsError}
          heatmapBins={heatmapBins}
          lecture={lecture}
          loadingAnalytics={loadingAnalytics}
        />
      </div>
    </>
  );
}

function MetricCard({
  compact = false,
  label,
  value,
}: {
  compact?: boolean;
  label: string;
  value: ReactNode;
}) {
  return (
    <div className="bg-gray-50 border border-gray-200 rounded-lg p-5">
      <p className="text-sm text-gray-500 mb-1">{label}</p>
      <p className={compact ? 'text-base font-semibold text-gray-900 line-clamp-3' : 'text-3xl font-bold text-gray-900'}>
        {value}
      </p>
    </div>
  );
}

function HeatmapContent({
  analyticsError,
  heatmapBins,
  lecture,
  loadingAnalytics,
}: {
  analyticsError: string | null;
  heatmapBins: ReturnType<typeof getHeatmapBins>;
  lecture: NonNullable<LectureWorkspaceState['lecture']>;
  loadingAnalytics: boolean;
}) {
  if (loadingAnalytics) {
    return <p className="text-base text-gray-500">Loading lecture timeline...</p>;
  }

  if (analyticsError) {
    return <p className="text-base text-red-600">{analyticsError}</p>;
  }

  if (lecture.file_type !== 'pdf') {
    return <p className="text-base text-gray-500">Document-position heatmap is available for PDF lectures.</p>;
  }

  if (lecture.page_count <= 0) {
    return <p className="text-base text-gray-500">Lecture pages are not available yet.</p>;
  }

  if (heatmapBins.length === 0) {
    return (
      <p className="text-base text-gray-500">
        No page-linked questions yet. Ask questions to build the document-position heatmap.
      </p>
    );
  }

  const maxValue = Math.max(1, ...heatmapBins.map((bin) => bin.count));
  const peakValue = Math.max(...heatmapBins.map((bin) => bin.count));

  return (
    <div className="flex items-end gap-2">
      {heatmapBins.map((bin) => {
        const intensity = bin.count / maxValue;
        const isPeak = bin.count === peakValue && peakValue > 0;
        return (
          <div key={`heat-bin-${bin.index}`} className="flex-1 flex flex-col items-center">
            <div
              className={`w-full h-10 rounded-md border ${isPeak ? 'border-primary-600' : 'border-gray-200'}`}
              style={{ backgroundColor: `rgba(37, 99, 235, ${0.15 + 0.75 * intensity})` }}
              title={`${formatHeatmapRange(bin)} • ${bin.count} questions`}
            />
            <span className="mt-2 text-sm text-gray-500">{formatHeatmapRange(bin)}</span>
            <span className="text-sm text-gray-400">{bin.count}</span>
          </div>
        );
      })}
    </div>
  );
}

function LectureManagementPanel({
  lecture,
  onRenameLecture,
  onReplaceLectureClick,
  replaceFileInput,
}: {
  lecture: NonNullable<LectureWorkspaceState['lecture']>;
  onRenameLecture: () => void;
  onReplaceLectureClick: () => void;
  replaceFileInput: ReactNode;
}) {
  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
      <h3 className="text-xl font-semibold text-gray-900 mb-4">Lecture Management</h3>
      <div className="space-y-3 text-base text-gray-700">
        <div className="flex items-center justify-between">
          <span>Visibility</span>
          <span className="font-medium">
            {lecture.status === 'archived'
              ? 'Archived'
              : lecture.status === 'completed'
              ? 'Published'
              : 'Draft'}
          </span>
        </div>
        <div className="flex items-center justify-between">
          <span>Release time</span>
          <span className="font-medium">{lecture.created_at ? formatHistoryTime(lecture.created_at) : 'N/A'}</span>
        </div>
        <div className="flex items-center justify-between">
          <span>Allowed access</span>
          <span className="font-medium">Everyone</span>
        </div>
        <div className="flex items-center justify-between">
          <span>Download enabled</span>
          <span className="font-medium">{lecture.file_path ? 'Yes' : 'No'}</span>
        </div>
      </div>
      <div className="mt-4 grid grid-cols-1 gap-2">
        <button
          type="button"
          onClick={onReplaceLectureClick}
          className="px-4 py-3 text-base border border-gray-300 rounded-lg hover:bg-gray-50"
        >
          Replace Material
        </button>
        <button
          type="button"
          onClick={onRenameLecture}
          className="px-4 py-3 text-base border border-gray-300 rounded-lg hover:bg-gray-50"
        >
          Rename lecture
        </button>
      </div>
      {replaceFileInput}
    </div>
  );
}

function LectureResourcesPanel({
  lecture,
  lecturePreviewUrl,
  lectureResources,
  loadingResources,
  onAddResource,
  onDeleteResource,
  onDownloadLecture,
}: {
  lecture: NonNullable<LectureWorkspaceState['lecture']>;
  lecturePreviewUrl: string;
  lectureResources: LectureWorkspaceState['lectureResources'];
  loadingResources: boolean;
  onAddResource: () => void;
  onDeleteResource: (resourceId: number) => void;
  onDownloadLecture: () => void;
}) {
  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
      <h3 className="text-xl font-semibold text-gray-900 mb-4">Lecture Resources</h3>
      <div className="space-y-3 text-base text-gray-700">
        <div>
          <p className="text-sm text-gray-500 mb-1">Primary file</p>
          <p className="font-medium text-base">{lecture.original_name || 'Untitled lecture'}</p>
          <div className="mt-2 flex flex-wrap gap-2">
            <a
              href={lecturePreviewUrl}
              target="_blank"
              rel="noreferrer"
              className="px-4 py-2 text-base border border-gray-300 rounded-lg hover:bg-gray-50"
            >
              Preview
            </a>
            <button
              type="button"
              onClick={onDownloadLecture}
              disabled={!lecture.file_path}
              className="px-4 py-2 text-base border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Download
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
                    onClick={() => onDeleteResource(resource.id)}
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
            onClick={onAddResource}
            className="mt-3 px-4 py-2 text-base border border-gray-300 rounded-lg hover:bg-gray-50"
          >
            Add resource
          </button>
        </div>
      </div>
    </div>
  );
}

function LectureQuestionsPanel({
  activeAnswerId,
  answerDrafts,
  faqQuestionIds,
  hiddenQuestionIds,
  manualAnswers,
  pinnedQuestionIds,
  questionFilter,
  questionSort,
  setActiveAnswerId,
  setAnswerDrafts,
  setManualAnswers,
  setQuestionFilter,
  setQuestionSort,
  setShowRecentQuestions,
  showRecentQuestions,
  sortedHistory,
  toggleFaqQuestion,
  toggleHiddenQuestion,
  togglePinnedQuestion,
}: {
  activeAnswerId: number | null;
  answerDrafts: LectureQuestionsState['answerDrafts'];
  faqQuestionIds: LectureQuestionsState['faqQuestionIds'];
  hiddenQuestionIds: LectureQuestionsState['hiddenQuestionIds'];
  manualAnswers: LectureQuestionsState['manualAnswers'];
  pinnedQuestionIds: LectureQuestionsState['pinnedQuestionIds'];
  questionFilter: LectureQuestionsState['questionFilter'];
  questionSort: LectureQuestionsState['questionSort'];
  setActiveAnswerId: LectureQuestionsState['setActiveAnswerId'];
  setAnswerDrafts: LectureQuestionsState['setAnswerDrafts'];
  setManualAnswers: LectureQuestionsState['setManualAnswers'];
  setQuestionFilter: LectureQuestionsState['setQuestionFilter'];
  setQuestionSort: LectureQuestionsState['setQuestionSort'];
  setShowRecentQuestions: LectureQuestionsState['setShowRecentQuestions'];
  showRecentQuestions: boolean;
  sortedHistory: LectureQuestionsState['sortedHistory'];
  toggleFaqQuestion: LectureQuestionsState['toggleFaqQuestion'];
  toggleHiddenQuestion: LectureQuestionsState['toggleHiddenQuestion'];
  togglePinnedQuestion: LectureQuestionsState['togglePinnedQuestion'];
}) {
  return (
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
              {(['all', 'flagged'] as const).map((filter) => (
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
                  {filter === 'all' ? 'All' : 'Flagged'}
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
                onChange={(e) => setQuestionSort(e.target.value as LectureQuestionSort)}
                className="px-3 py-2 text-base border border-gray-300 rounded-lg"
              >
                <option value="newest">Newest</option>
                <option value="oldest">Oldest</option>
                <option value="most_repeated">Most repeated</option>
              </select>
            </div>
          </div>

          {sortedHistory.length === 0 ? (
            <p className="text-base text-gray-500">No questions match this filter yet.</p>
          ) : (
            <div className="space-y-3">
              {sortedHistory.map((item) => {
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
                      </div>
                    </div>

                    <QuestionActions
                      hiddenQuestionIds={hiddenQuestionIds}
                      isFlagged={isFlagged}
                      isPinned={isPinned}
                      itemId={item.id}
                      toggleFaqQuestion={toggleFaqQuestion}
                      toggleHiddenQuestion={toggleHiddenQuestion}
                      togglePinnedQuestion={togglePinnedQuestion}
                    />

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
                        <div className="flex items-center justify-between mb-2">
                          <span className="text-sm font-medium text-gray-700">Edit Answer</span>
                          <button
                            type="button"
                            onClick={() => setActiveAnswerId(null)}
                            className="text-sm text-gray-500 hover:text-gray-700 px-2 py-1 rounded hover:bg-gray-200"
                          >
                            Collapse
                          </button>
                        </div>
                        <textarea
                          value={answerDrafts[item.id] ?? ''}
                          onChange={(e) => {
                            setAnswerDrafts((prev) => ({ ...prev, [item.id]: e.target.value }));
                            e.target.style.height = 'auto';
                            e.target.style.height = `${e.target.scrollHeight}px`;
                          }}
                          onInput={(e) => {
                            const el = e.currentTarget;
                            el.style.height = 'auto';
                            el.style.height = `${el.scrollHeight}px`;
                          }}
                          ref={(el) => {
                            if (el) {
                              el.style.height = 'auto';
                              el.style.height = `${el.scrollHeight}px`;
                            }
                          }}
                          rows={1}
                          style={{ resize: 'none', overflow: 'hidden', minHeight: '3rem' }}
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
  );
}

function QuestionActions({
  hiddenQuestionIds,
  isFlagged,
  isPinned,
  itemId,
  toggleFaqQuestion,
  toggleHiddenQuestion,
  togglePinnedQuestion,
}: {
  hiddenQuestionIds: LectureQuestionsState['hiddenQuestionIds'];
  isFlagged: boolean;
  isPinned: boolean;
  itemId: number;
  toggleFaqQuestion: LectureQuestionsState['toggleFaqQuestion'];
  toggleHiddenQuestion: LectureQuestionsState['toggleHiddenQuestion'];
  togglePinnedQuestion: LectureQuestionsState['togglePinnedQuestion'];
}) {
  return (
    <div className="flex flex-wrap items-center gap-2">
      <button
        type="button"
        onClick={() => toggleFaqQuestion(itemId)}
        className="px-4 py-2 text-base border border-gray-300 rounded-lg hover:bg-gray-50"
      >
        {isFlagged ? 'Unmark FAQ' : 'Mark FAQ'}
      </button>
      <button
        type="button"
        onClick={() => togglePinnedQuestion(itemId)}
        className="px-4 py-2 text-base border border-gray-300 rounded-lg hover:bg-gray-50"
      >
        {isPinned ? 'Unpin' : 'Pin'}
      </button>
      <button
        type="button"
        onClick={() => toggleHiddenQuestion(itemId)}
        className="px-4 py-2 text-base border border-gray-300 rounded-lg hover:bg-gray-50"
      >
        {hiddenQuestionIds.has(itemId) ? 'Unhide' : 'Hide'}
      </button>
    </div>
  );
}

function LectureStudySidebar({
  flashcardCount,
  flashcardsLoading,
  handleGenerateFlashcards,
  handleGenerateKeyPoints,
  handleGenerateSummary,
  keyPointsLoading,
  loadingMaterials,
  materials,
  setFlashcardCount,
  setShowFlashcardsTool,
  setShowKeyConceptsTool,
  setShowSummaryTool,
  showFlashcardsTool,
  showKeyConceptsTool,
  showSummaryTool,
  summaryLoading,
}: {
  flashcardCount: number;
  flashcardsLoading: boolean;
  handleGenerateFlashcards: () => void;
  handleGenerateKeyPoints: () => void;
  handleGenerateSummary: () => void;
  keyPointsLoading: boolean;
  loadingMaterials: boolean;
  materials: LectureWorkspaceState['materials'];
  setFlashcardCount: LectureWorkspaceState['setFlashcardCount'];
  setShowFlashcardsTool: LectureWorkspaceState['setShowFlashcardsTool'];
  setShowKeyConceptsTool: LectureWorkspaceState['setShowKeyConceptsTool'];
  setShowSummaryTool: LectureWorkspaceState['setShowSummaryTool'];
  showFlashcardsTool: boolean;
  showKeyConceptsTool: boolean;
  showSummaryTool: boolean;
  summaryLoading: boolean;
}) {
  const flashcardOptions = Array.from(
    { length: apiClient.FLASHCARD_COUNT_MAX - apiClient.FLASHCARD_COUNT_MIN + 1 },
    (_, i) => i + apiClient.FLASHCARD_COUNT_MIN
  );

  return (
    <aside className="w-80 border-r border-gray-200 bg-white p-4 space-y-4 overflow-y-auto">
      <div>
        <h3 className="text-xl font-semibold text-gray-900">Study Tools</h3>
        <p className="text-sm text-gray-500">Generate learning aids for this lecture.</p>
      </div>

      <CollapsibleToolCard
        description="Concise overview of the lecture."
        onToggle={() => setShowSummaryTool(!showSummaryTool)}
        open={showSummaryTool}
        title="Lecture Summary"
      >
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
      </CollapsibleToolCard>

      <CollapsibleToolCard
        description="Exam-focused highlights."
        onToggle={() => setShowKeyConceptsTool(!showKeyConceptsTool)}
        open={showKeyConceptsTool}
        title="Key Points"
      >
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
      </CollapsibleToolCard>

      <CollapsibleToolCard
        description="Auto-generated study cards."
        onToggle={() => setShowFlashcardsTool(!showFlashcardsTool)}
        open={showFlashcardsTool}
        title="Flashcards"
      >
        <div className="flex items-center justify-between gap-2">
          <label htmlFor="flashcard-count" className="text-sm font-medium text-gray-700">
            Number of cards:
          </label>
          <select
            id="flashcard-count"
            value={flashcardCount}
            onChange={(e) => setFlashcardCount(Number(e.target.value))}
            className="rounded-md border border-gray-300 px-2 py-1 text-sm focus:ring-primary-500 focus:border-primary-500"
          >
            {flashcardOptions.map((n) => (
              <option key={n} value={n}>
                {n}
              </option>
            ))}
          </select>
        </div>
        <button
          onClick={handleGenerateFlashcards}
          className="w-full px-4 py-2 bg-primary-600 text-white rounded-lg text-base font-medium hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed"
          disabled={flashcardsLoading}
        >
          {flashcardsLoading
            ? 'Generating...'
            : materials?.flashcards?.length
            ? `Regenerate ${flashcardCount} Cards`
            : `Generate ${flashcardCount} Cards`}
        </button>
        {loadingMaterials ? (
          <p className="text-sm text-gray-500">Loading...</p>
        ) : (
          <Flashcards flashcards={materials?.flashcards ?? []} />
        )}
      </CollapsibleToolCard>
    </aside>
  );
}

function CollapsibleToolCard({
  children,
  description,
  onToggle,
  open,
  title,
}: {
  children: ReactNode;
  description: string;
  onToggle: () => void;
  open: boolean;
  title: string;
}) {
  return (
    <div className={`rounded-xl shadow-sm border ${open ? 'bg-white border-gray-200' : 'bg-gray-50 border-gray-200'}`}>
      <button onClick={onToggle} className="w-full px-4 py-3 flex items-center justify-between text-left">
        <div>
          <h4 className="text-base font-semibold text-gray-900">{title}</h4>
          <p className="text-sm text-gray-500">{description}</p>
        </div>
        <span className="text-sm text-gray-600">{open ? 'Collapse' : 'Expand'}</span>
      </button>
      {open && <div className="px-4 pb-4 space-y-3">{children}</div>}
    </div>
  );
}

function LectureChatPanel({
  asking,
  chatMessageList,
  currentAnswer,
  handleSubmit,
  messagesEndRef,
  question,
  setQuestion,
  slideViewerRef,
}: {
  asking: boolean;
  chatMessageList: LectureQuestionsState['chatMessageList'];
  currentAnswer: LectureQuestionsState['currentAnswer'];
  handleSubmit: LectureQuestionsState['handleSubmit'];
  messagesEndRef: LectureQuestionsState['messagesEndRef'];
  question: string;
  setQuestion: LectureQuestionsState['setQuestion'];
  slideViewerRef: MutableRefObject<SlideViewerRef | null>;
}) {
  return (
    <div className="flex-1 flex flex-col min-h-0 h-[calc(100vh-9rem)]">
      <div className="flex-1 min-h-0 overflow-y-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6">
        {chatMessageList.length === 0 && !currentAnswer && !asking && (
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

        {chatMessageList.map((item) => (
          <div key={item.id} className="space-y-2">
            <div className="flex items-start space-x-3">
              <ChatAvatar variant="user" />
              <div className="flex-1">
                <p className="text-base font-medium text-gray-900">{item.question}</p>
              </div>
            </div>
            <div className="flex items-start space-x-3 ml-11">
              <ChatAvatar variant="lecture" />
              <div className="flex-1">
                <div className="prose prose-base max-w-none">
                  <p className="text-base text-gray-700 whitespace-pre-wrap">{item.answer}</p>
                </div>
              </div>
            </div>
          </div>
        ))}

        {currentAnswer && (
          <div className="space-y-2">
            <div className="flex items-start space-x-3">
              <ChatAvatar variant="user" />
              <div className="flex-1">
                <p className="text-sm font-medium text-gray-900">{question}</p>
              </div>
            </div>
            <div className="flex items-start space-x-3 ml-11">
              <ChatAvatar variant="lecture" />
              <div className="flex-1">
                <div className="prose prose-base max-w-none">
                  <p className="text-base text-gray-700 whitespace-pre-wrap">{currentAnswer.answer}</p>
                  {currentAnswer.citation && (
                    <p className="mt-2 text-sm text-primary-600 font-medium">{currentAnswer.citation}</p>
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
            <ChatAvatar variant="lecture" />
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

      <div className="shrink-0 border-t border-gray-200 bg-white px-4 sm:px-6 lg:px-8 py-4">
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
                    void handleSubmit();
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
  );
}

function ChatAvatar({ variant }: { variant: 'lecture' | 'user' }) {
  if (variant === 'lecture') {
    return (
      <div className="flex-shrink-0 w-8 h-8 bg-primary-100 rounded-full flex items-center justify-center">
        <span className="text-primary-600 font-bold text-sm">L</span>
      </div>
    );
  }

  return (
    <div className="flex-shrink-0 w-8 h-8 bg-gray-200 rounded-full flex items-center justify-center">
      <svg className="w-5 h-5 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
      </svg>
    </div>
  );
}
