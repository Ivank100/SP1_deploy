'use client';

/**
 * This component renders the course detail page page UI.
 * It takes prepared page state and turns it into the visible screen layout.
 */
import FileUpload from '@/components/courses/FileUpload';
import LectureList from '@/components/lectures/LectureList';
import Link from 'next/link';
import CourseAnalyticsOverview from '@/components/courses/CourseAnalyticsOverview';
import { useCourseDetailPage } from '@/hooks/useCourseDetailPage';

type CourseDetailPageViewProps = {
  page: ReturnType<typeof useCourseDetailPage>;
};

export default function CourseDetailPageView({ page }: CourseDetailPageViewProps) {
  const {
    activeCategory,
    announcementError,
    announcements,
    avgQuestions,
    canReviewUploads,
    categoryOptions,
    collapseAskQuestions,
    collapseInstructorAnnouncements,
    collapseLectures,
    collapseManageStudents,
    collapseStudentAnnouncements,
    collapseUploadRequests,
    course,
    courseAsking,
    courseChatEndRef,
    courseChatMessages,
    courseQuestion,
    handleApproveUpload,
    handleCourseQuery,
    handleDelete,
    handleDeleteUploadRequest,
    handleLeaveCourse,
    handleLogout,
    handlePostAnnouncement,
    handleRejectUpload,
    handleUploadSuccess,
    lectureQuestionsById,
    loadAnnouncements,
    loadCourseStudents,
    loading,
    loadingMyUploadRequests,
    loadingUploadRequests,
    loadMyUploadRequests,
    loadUploadRequests,
    myUploadRequests,
    newAnnouncement,
    postingAnnouncement,
    queryError,
    refreshing,
    renderSources,
    renderStudentManagement,
    setActiveCategory,
    setCollapseAskQuestions,
    setCollapseInstructorAnnouncements,
    setCollapseLectures,
    setCollapseManageStudents,
    setCollapseStudentAnnouncements,
    setCollapseUploadRequests,
    setCourseQuestion,
    setNewAnnouncement,
    setShowAllInstructorLectures,
    setShowAllStudentLectures,
    showAllInstructor,
    showAllInstructorLectures,
    showAllStudents,
    showAllStudentLectures,
    showAnalytics,
    showAnnouncements,
    showLectures,
    showManageStudentsSection,
    showQuestions,
    showUploads,
    uploadRequests,
    user,
    visibleInstructorLectures,
    visibleStudentLectures,
    instructorLectures,
    studentLectures,
  } = page;

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <svg className="w-8 h-8 animate-spin mx-auto text-primary-500" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
          </svg>
          <p className="mt-4 text-gray-500">Loading course...</p>
        </div>
      </div>
    );
  }

  if (!course) {
    return null;
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-4">
              <Link href="/" className="text-xl font-bold text-primary-600 hover:text-primary-700">
                ← Back
              </Link>
              <div>
                <h1 className="text-2xl font-semibold text-gray-900">{course.name}</h1>
                {course.description && (
                  <p className="text-base text-gray-500">{course.description}</p>
                )}
                <p className="text-sm text-gray-400 mt-1">{course.lecture_count} lectures</p>
              </div>
            </div>
            <div className="flex items-center space-x-4">
              {user?.role === 'student' && (
                <button
                  onClick={handleLeaveCourse}
                  className="text-base text-red-600 hover:text-red-700"
                >
                  Leave course
                </button>
              )}
              <button
                onClick={handleLogout}
                className="text-base text-gray-700 hover:text-gray-900"
              >
                Logout
              </button>
              <div className="w-8 h-8 bg-primary-600 rounded-full flex items-center justify-center text-white text-sm font-medium">
                {user?.email?.charAt(0).toUpperCase() || 'U'}
              </div>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10 space-y-10">
        {/* Zone 2: Course management */}
        <div>
          <h3 className="text-2xl font-semibold text-gray-900 mb-4">Course Management</h3>
          <div className="grid grid-cols-1 lg:grid-cols-[260px_minmax(0,1fr)] gap-8">
            <aside className="bg-white border border-gray-200 rounded-xl p-5 h-fit sticky top-24">
              <h4 className="text-base font-semibold text-gray-900 mb-4">Functions</h4>
              <div className="space-y-2">
                {categoryOptions.map((category) => (
                  <button
                    key={category}
                    onClick={() => setActiveCategory(category)}
                    className={`w-full px-4 py-3 text-base rounded-lg border text-left transition ${
                      activeCategory === category
                        ? 'bg-primary-600 text-white border-primary-600'
                        : 'bg-white text-gray-700 border-gray-200 hover:border-gray-300'
                    }`}
                  >
                    {category === 'all'
                      ? 'All'
                      : category === 'analytics'
                      ? 'Course Analytics'
                      : category === 'lectures'
                      ? 'Lectures'
                      : category === 'students'
                      ? 'Manage Students'
                      : category === 'uploads'
                      ? 'Upload Requests'
                      : category === 'announcements'
                      ? 'Announcements'
                      : 'Ask Questions'}
                  </button>
                ))}
              </div>
            </aside>

            <div className="space-y-6">
              {user?.role === 'instructor' && showAnalytics && (
                <CourseAnalyticsOverview courseId={course.id} />
              )}
              {showLectures && (
                <div className={`rounded-xl shadow-sm border ${collapseLectures[course.id] ? 'bg-gray-50 border-gray-200' : 'bg-white border-gray-200'}`}>
                  <button
                    onClick={() =>
                      setCollapseLectures({ ...collapseLectures, [course.id]: !collapseLectures[course.id] })
                    }
                    className="w-full px-6 py-4 flex items-center justify-between text-left"
                  >
                    <div className="flex items-center gap-3">
                      <h3 className="text-lg font-semibold text-gray-900">Lectures</h3>
                      {refreshing && (
                        <div className="flex items-center space-x-2 text-sm text-gray-500">
                          <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                          </svg>
                        </div>
                      )}
                    </div>
                    <span className="text-base text-gray-600">
                      {collapseLectures[course.id] ? '+' : '−'}
                    </span>
                  </button>
                  {!collapseLectures[course.id] && (
                    <div className="px-6 pb-6">
                      {user?.role === 'instructor' ? (
                        <FileUpload
                          courseId={course.id}
                          onUploadSuccess={handleUploadSuccess}
                          mode="direct"
                        />
                      ) : (
                        <FileUpload
                          courseId={course.id}
                          onUploadSuccess={handleUploadSuccess}
                          mode="request"
                        />
                      )}
                      <div className="mt-4 space-y-6">
                        <div>
                          <h4 className="text-base font-semibold text-gray-900 mb-2">Instructor uploaded materials</h4>
                          {instructorLectures.length === 0 ? (
                            <p className="text-base text-gray-500">No instructor uploads yet.</p>
                          ) : (
                            <LectureList
                              lectures={visibleInstructorLectures}
                              onDelete={user?.role === 'instructor' ? handleDelete : undefined}
                              activityByLectureId={lectureQuestionsById}
                              avgQuestions={avgQuestions}
                            />
                          )}
                          {instructorLectures.length > 4 && (
                            <button
                              onClick={() =>
                                setShowAllInstructorLectures({
                                  ...showAllInstructorLectures,
                                  [course.id]: !showAllInstructor,
                                })
                              }
                              className="mt-3 text-base text-gray-600 hover:text-gray-800"
                            >
                              {showAllInstructor
                                ? 'Show less'
                                : `Show more (+${instructorLectures.length - visibleInstructorLectures.length})`}
                            </button>
                          )}
                        </div>

                        <div className="pt-4 border-t border-gray-200">
                          <h4 className="text-base font-semibold text-gray-900 mb-2">Student uploaded materials</h4>
                          {studentLectures.length === 0 ? (
                            <p className="text-base text-gray-500">No student uploads yet.</p>
                          ) : (
                            <LectureList
                              lectures={visibleStudentLectures}
                              onDelete={user?.role === 'instructor' ? handleDelete : undefined}
                              activityByLectureId={lectureQuestionsById}
                              avgQuestions={avgQuestions}
                            />
                          )}
                          {studentLectures.length > 4 && (
                            <button
                              onClick={() =>
                                setShowAllStudentLectures({
                                  ...showAllStudentLectures,
                                  [course.id]: !showAllStudents,
                                })
                              }
                              className="mt-3 text-base text-gray-600 hover:text-gray-800"
                            >
                              {showAllStudents
                                ? 'Show less'
                                : `Show more (+${studentLectures.length - visibleStudentLectures.length})`}
                            </button>
                          )}
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              )}

              {user?.role === 'instructor' && showManageStudentsSection && (
                <div className={`rounded-xl shadow-sm border ${collapseManageStudents[course.id] ? 'bg-gray-50 border-gray-200' : 'bg-white border-gray-200'}`}>
                  <button
                    onClick={async () => {
                      const nextCollapsed = !collapseManageStudents[course.id];
                      setCollapseManageStudents({ ...collapseManageStudents, [course.id]: nextCollapsed });
                      if (!nextCollapsed) {
                        await loadCourseStudents(course.id);
                        await loadAnnouncements(course.id);
                        await loadUploadRequests(course.id);
                      }
                    }}
                    className="w-full px-6 py-4 flex items-center justify-between text-left"
                  >
                    <span className="text-lg font-semibold text-gray-900">Manage Students</span>
                    <span className="text-base text-gray-600">
                      {collapseManageStudents[course.id] ? '+' : '−'}
                    </span>
                  </button>
                  {!collapseManageStudents[course.id] && (
                    <div className="px-6 pb-6">
                      {renderStudentManagement(course.id)}
                    </div>
                  )}
                </div>
              )}

              {(user?.role === 'instructor' || canReviewUploads[course.id]) && showUploads && (
                <div className={`rounded-xl shadow-sm border ${collapseUploadRequests[course.id] ? 'bg-gray-50 border-gray-200' : 'bg-white border-gray-200'}`}>
                  <button
                    onClick={() =>
                      setCollapseUploadRequests({
                        ...collapseUploadRequests,
                        [course.id]: !collapseUploadRequests[course.id],
                      })
                    }
                    className="w-full px-6 py-4 flex items-center justify-between text-left"
                  >
                    <h3 className="text-lg font-semibold text-gray-900">Upload Requests</h3>
                    <span className="text-base text-gray-600">
                      {collapseUploadRequests[course.id] ? '+' : '−'}
                    </span>
                  </button>
                  {!collapseUploadRequests[course.id] && (
                    <div className="px-6 pb-6">
                      <div className="flex items-center justify-between mb-4">
                        <div />
                        <button
                          onClick={() => loadUploadRequests(course.id)}
                          className="text-base text-gray-500 hover:text-gray-700"
                        >
                          Refresh
                        </button>
                      </div>
                      {loadingUploadRequests[course.id] ? (
                        <p className="text-base text-gray-500">Loading requests...</p>
                      ) : (uploadRequests[course.id] || []).length === 0 ? (
                        <p className="text-base text-gray-500">
                          No upload requests yet. Student submissions will appear here.
                        </p>
                      ) : (
                        <div className="space-y-3">
                          {(uploadRequests[course.id] || []).map((request) => (
                            <div key={request.id} className="border border-gray-200 rounded-lg p-3">
                              <div className="flex items-start justify-between gap-3">
                                <div className="min-w-0">
                                  <p className="text-base font-medium text-gray-900 truncate" title={request.original_name}>
                                    {request.original_name}
                                  </p>
                                  <p className="text-sm text-gray-500 truncate" title={request.student_email || 'Student'}>
                                    {request.student_email || 'Student'} • {request.file_type}
                                  </p>
                                </div>
                                <div className="flex items-center gap-2">
                                  <button
                                    onClick={() => handleApproveUpload(course.id, request.id)}
                                    className="px-4 py-2 text-sm bg-green-600 text-white rounded hover:bg-green-700"
                                  >
                                    Approve
                                  </button>
                                  <button
                                    onClick={() => handleRejectUpload(course.id, request.id)}
                                    className="px-4 py-2 text-sm bg-red-600 text-white rounded hover:bg-red-700"
                                  >
                                    Reject
                                  </button>
                                </div>
                              </div>
                              {request.created_at && (
                                <p className="text-sm text-gray-400 mt-2">
                                  Requested {new Date(request.created_at).toLocaleString()}
                                </p>
                              )}
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              )}

              {user?.role === 'student' && showUploads && (
                <div className={`rounded-xl shadow-sm border ${collapseUploadRequests[course.id] ? 'bg-gray-50 border-gray-200' : 'bg-white border-gray-200'}`}>
                  <button
                    onClick={() =>
                      setCollapseUploadRequests({
                        ...collapseUploadRequests,
                        [course.id]: !collapseUploadRequests[course.id],
                      })
                    }
                    className="w-full px-6 py-4 flex items-center justify-between text-left"
                  >
                    <h3 className="text-xl font-semibold text-gray-900">My Upload Requests</h3>
                    <span className="text-base text-gray-600">
                      {collapseUploadRequests[course.id] ? '+' : '−'}
                    </span>
                  </button>
                  {!collapseUploadRequests[course.id] && (
                    <div className="px-6 pb-6">
                      <div className="flex items-center justify-between mb-4">
                        <div />
                        <button
                          onClick={() => loadMyUploadRequests(course.id)}
                          className="text-lg text-gray-500 hover:text-gray-700"
                        >
                          Refresh
                        </button>
                      </div>
                      {loadingMyUploadRequests[course.id] ? (
                        <p className="text-lg text-gray-500">Loading requests...</p>
                      ) : (myUploadRequests[course.id] || []).length === 0 ? (
                        <p className="text-lg text-gray-500">
                          No upload requests yet. Submitted files will show here.
                        </p>
                      ) : (
                        <div className="space-y-4">
                          {(myUploadRequests[course.id] || []).map((request) => (
                            <div key={request.id} className="border border-gray-200 rounded-lg p-4">
                              <div className="flex items-start justify-between gap-3">
                                <div className="min-w-0">
                                  <p className="text-lg font-medium text-gray-900 truncate" title={request.original_name}>
                                    {request.original_name}
                                  </p>
                                  <p className="text-base text-gray-500 truncate">{request.file_type}</p>
                                </div>
                                <div className="flex items-center gap-2">
                                  <span
                                    className={`text-base px-2 py-0.5 rounded-full ${
                                      request.status === 'pending'
                                        ? 'bg-yellow-50 text-yellow-700 border border-yellow-200'
                                        : request.status === 'approved'
                                        ? 'bg-green-50 text-green-700 border border-green-200'
                                        : 'bg-red-50 text-red-700 border border-red-200'
                                    }`}
                                  >
                                    {request.status}
                                  </span>
                                  <button
                                    onClick={() => handleDeleteUploadRequest(course.id, request.id, request.status)}
                                    className={`px-3 py-1.5 text-sm rounded border ${
                                      request.status === 'pending'
                                        ? 'border-red-200 text-red-700 hover:bg-red-50'
                                        : 'border-gray-200 text-gray-700 hover:bg-gray-50'
                                    }`}
                                  >
                                    {request.status === 'pending' ? 'Cancel' : 'Remove'}
                                  </button>
                                </div>
                              </div>
                              {request.created_at && (
                                <p className="text-base text-gray-400 mt-2">
                                  Submitted {new Date(request.created_at).toLocaleString()}
                                </p>
                              )}
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              )}

              {user?.role === 'student' && showAnnouncements && (
                <div className={`rounded-xl shadow-sm border ${collapseStudentAnnouncements[course.id] ? 'bg-blue-50 border-blue-100' : 'bg-blue-50 border-blue-100'}`}>
                  <button
                    onClick={() =>
                      setCollapseStudentAnnouncements({
                        ...collapseStudentAnnouncements,
                        [course.id]: !collapseStudentAnnouncements[course.id],
                      })
                    }
                    className="w-full px-6 py-4 flex items-center justify-between text-left"
                  >
                    <div className="flex items-center gap-2">
                      <span className="text-blue-600">📢</span>
                      <h3 className="text-xl font-semibold text-gray-900">Announcements</h3>
                    </div>
                    <span className="text-base text-gray-600">
                      {collapseStudentAnnouncements[course.id] ? '+' : '−'}
                    </span>
                  </button>
                  {!collapseStudentAnnouncements[course.id] && (
                    <div className="px-6 pb-6">
                      {(announcements[course.id] || []).length === 0 ? (
                        <p className="text-lg text-gray-500">No announcements yet.</p>
                      ) : (
                        <div className="space-y-3">
                          {(announcements[course.id] || []).map((item) => (
                            <div key={item.id} className="border border-gray-200 rounded-lg p-4">
                              <p className="text-lg text-gray-800 whitespace-pre-wrap">{item.message}</p>
                              {item.created_at && (
                                <p className="text-base text-gray-400 mt-2">
                                  {new Date(item.created_at).toLocaleString()}
                                </p>
                              )}
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              )}

              {user?.role === 'student' && showQuestions && (
                <div className={`rounded-xl shadow-sm border ${collapseAskQuestions[course.id] ? 'bg-gray-50 border-gray-200' : 'bg-white border-gray-200'}`}>
                  <button
                    onClick={() =>
                      setCollapseAskQuestions({
                        ...collapseAskQuestions,
                        [course.id]: !collapseAskQuestions[course.id],
                      })
                    }
                    className="w-full px-6 py-4 flex items-center justify-between text-left"
                  >
                    <h3 className="text-lg font-semibold text-gray-900">Ask Questions</h3>
                    <span className="text-base text-gray-600">
                      {collapseAskQuestions[course.id] ? '+' : '−'}
                    </span>
                  </button>
                  {!collapseAskQuestions[course.id] && (
                    <div className="flex flex-col min-h-[320px] max-h-[560px]">
                      <div className="flex-1 overflow-y-auto px-6 py-4 space-y-4">
                        {courseChatMessages.length === 0 && !courseAsking && (
                          <div className="text-center py-8 text-gray-500">
                            <p className="text-base">Ask a question about the course content.</p>
                            <p className="text-sm mt-1">Answers will appear here in a chat thread.</p>
                          </div>
                        )}
                        {courseChatMessages.map((msg, idx) => (
                          <div key={idx} className="space-y-2">
                            <div className="flex justify-end">
                              <div className="max-w-[85%] rounded-2xl rounded-br-md bg-primary-600 text-white px-4 py-2.5">
                                <p className="text-base whitespace-pre-wrap">{msg.question}</p>
                              </div>
                            </div>
                            <div className="flex justify-start">
                              <div className="max-w-[85%] rounded-2xl rounded-bl-md bg-gray-100 text-gray-900 px-4 py-2.5 border border-gray-200">
                                {msg.answer ? (
                                  <div className="prose prose-sm max-w-none">
                                    <p className="text-base whitespace-pre-wrap">{msg.answer.answer}</p>
                                    {renderSources(msg.answer.sources)}
                                  </div>
                                ) : (
                                  <div className="flex items-center gap-2 text-gray-500">
                                    <svg className="w-5 h-5 animate-spin flex-shrink-0" fill="none" viewBox="0 0 24 24">
                                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                                    </svg>
                                    <span className="text-sm">Thinking...</span>
                                  </div>
                                )}
                              </div>
                            </div>
                          </div>
                        ))}
                        <div ref={courseChatEndRef} />
                      </div>
                      <div className="border-t border-gray-200 bg-gray-50/80 px-6 py-4">
                        {queryError && (
                          <div className="mb-3 text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg px-3 py-2">
                            {queryError}
                          </div>
                        )}
                        <form onSubmit={handleCourseQuery} className="flex gap-3 items-end">
                          <textarea
                            value={courseQuestion}
                            onChange={(e) => setCourseQuestion(e.target.value)}
                            placeholder="Ask a question about the course content..."
                            rows={2}
                            className="flex-1 px-4 py-3 text-base border border-gray-300 rounded-xl focus:ring-2 focus:ring-primary-500 focus:border-transparent resize-none bg-white"
                            disabled={courseAsking || course.lecture_count === 0}
                          />
                          <button
                            type="submit"
                            disabled={courseAsking || !courseQuestion.trim() || course.lecture_count === 0}
                            className="px-5 py-3 text-base bg-primary-600 text-white rounded-xl font-medium hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex-shrink-0"
                          >
                            {courseAsking ? '…' : 'Send'}
                          </button>
                        </form>
                        {course.lecture_count === 0 && (
                          <p className="mt-2 text-sm text-gray-500">Upload at least one lecture to ask questions.</p>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              )}

              {user?.role === 'instructor' && showAnnouncements && (
                <div className={`rounded-xl shadow-sm border ${collapseInstructorAnnouncements[course.id] ? 'bg-gray-50 border-gray-200' : 'bg-white border-gray-200'}`}>
                  <button
                    onClick={() =>
                      setCollapseInstructorAnnouncements({
                        ...collapseInstructorAnnouncements,
                        [course.id]: !collapseInstructorAnnouncements[course.id],
                      })
                    }
                    className="w-full px-6 py-4 flex items-center justify-between text-left"
                  >
                    <h4 className="text-lg font-semibold text-gray-900">Announcements</h4>
                    <span className="text-base text-gray-600">
                      {collapseInstructorAnnouncements[course.id] ? '+' : '−'}
                    </span>
                  </button>
                  {!collapseInstructorAnnouncements[course.id] && (
                    <div className="px-6 pb-6">
                      <p className="text-base text-gray-500 mb-3">
                        Use announcements to clarify confusing topics or post updates.
                      </p>
                      <div className="space-y-3">
                        <textarea
                          value={newAnnouncement[course.id] || ''}
                          onChange={(e) => setNewAnnouncement({ ...newAnnouncement, [course.id]: e.target.value })}
                          placeholder="Post an announcement to this course..."
                          rows={3}
                          className="w-full px-4 py-3 text-base border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent resize-none"
                        />
                        <div className="flex items-center justify-between">
                          {announcementError[course.id] && (
                            <p className="text-xs text-red-600">{announcementError[course.id]}</p>
                          )}
                          <button
                            onClick={() => handlePostAnnouncement(course.id)}
                            disabled={postingAnnouncement[course.id]}
                            className="ml-auto px-4 py-2 text-base bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50"
                          >
                            {postingAnnouncement[course.id] ? 'Posting...' : 'Post'}
                          </button>
                        </div>
                        <div className="space-y-2">
                          {(announcements[course.id] || []).length === 0 ? (
                            <p className="text-base text-gray-500">No announcements yet.</p>
                          ) : (
                            (announcements[course.id] || []).map((item) => (
                              <div key={item.id} className="border border-gray-200 rounded-lg p-3">
                                <p className="text-base text-gray-800 whitespace-pre-wrap">{item.message}</p>
                                {item.created_at && (
                                  <p className="text-xs text-gray-400 mt-2">
                                    {new Date(item.created_at).toLocaleString()}
                                  </p>
                                )}
                              </div>
                            ))
                          )}
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        </div>

      </main>
    </div>
  );
}
