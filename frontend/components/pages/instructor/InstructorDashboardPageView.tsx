'use client';

/**
 * This component renders the instructor dashboard page page UI.
 * It takes prepared page state and turns it into the visible screen layout.
 */
import Link from 'next/link';
import RecurringTopicsCard from '@/components/instructor/RecurringTopicsCard';
import { useInstructorDashboardPage } from '@/hooks/useInstructorDashboardPage';

type InstructorDashboardPageViewProps = {
  page: ReturnType<typeof useInstructorDashboardPage>;
};

export default function InstructorDashboardPageView({ page }: InstructorDashboardPageViewProps) {
  const {
    activeStudentsLast7Days,
    activeTab,
    courses,
    handleLogout,
    health,
    lectures,
    lecturesWithQuestions,
    loading,
    mostConfusingLecture,
    queries,
    queriesList,
    selectedCourseId,
    selectedLectureId,
    setActiveTab,
    setSelectedCourseId,
    setSelectedLectureId,
    setShowAllRecurringTopics,
    showAllRecurringTopics,
    topLecturesByConfusion,
    topStudents,
    totalQuestions,
    user,
  } = page;

  const renderLectureBars = (showAll: boolean) => {
    if (!health?.lectures?.length) {
      return <p className="text-sm text-gray-500">No lecture data available yet.</p>;
    }

    const items = [...health.lectures]
      .sort((a, b) => b.query_count - a.query_count)
      .slice(0, showAll ? health.lectures.length : 8);
    const maxValue = Math.max(1, ...items.map((lecture) => lecture.query_count));

    return (
      <div className={`space-y-3 ${showAll ? 'max-h-80 overflow-y-auto pr-1' : ''}`}>
        {items.map((lecture) => (
          <div key={lecture.lecture_id} className="flex items-center gap-3">
            <div className={`${showAll ? 'w-56' : 'w-48'} text-sm text-gray-700 truncate`} title={lecture.lecture_name}>
              {lecture.lecture_name || 'Lecture'}
            </div>
            <div className="flex-1 bg-gray-100 rounded-full h-3">
              <div
                className="bg-primary-500 h-3 rounded-full"
                style={{ width: `${(lecture.query_count / maxValue) * 100}%` }}
              />
            </div>
            <div className="text-sm text-gray-600 w-12 text-right">{lecture.query_count}</div>
          </div>
        ))}
      </div>
    );
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <svg className="w-8 h-8 animate-spin mx-auto text-primary-500" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
          </svg>
          <p className="mt-4 text-gray-500">Loading analytics...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white border-b border-gray-200 sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <div className="flex items-center space-x-4">
              <Link href="/" className="text-sm font-medium text-gray-700 hover:text-primary-600">
                ← Back to Courses
              </Link>
              <h1 className="text-xl font-bold text-gray-900">Instructor Analytics</h1>
            </div>
            {user && (
              <div className="flex items-center space-x-3">
                <div className="flex flex-col items-end">
                  <span className="text-sm font-medium text-gray-900">{user.email}</span>
                  <span className="text-xs text-gray-500 capitalize">{user.role}</span>
                </div>
                <button
                  onClick={handleLogout}
                  className="px-3 py-1.5 text-sm font-medium text-white bg-primary-600 hover:bg-primary-700 rounded-md transition-colors"
                >
                  Logout
                </button>
              </div>
            )}
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
        <div className="mb-4">
          <label htmlFor="course-select" className="block text-sm font-medium text-gray-700 mb-2">
            Select Course
          </label>
          <div className="flex flex-wrap gap-2">
            <button
              onClick={() => setSelectedCourseId(null)}
              className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
                selectedCourseId === null ? 'bg-primary-600 text-white' : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              }`}
            >
              All Courses
            </button>
            {courses.map((course) => (
              <button
                key={course.id}
                onClick={() => setSelectedCourseId(course.id)}
                className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
                  selectedCourseId === course.id ? 'bg-primary-600 text-white' : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                }`}
              >
                {course.name}
              </button>
            ))}
          </div>
        </div>

        {selectedCourseId && lectures.length > 0 && (
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4 mb-6">
            <h3 className="text-sm font-medium text-gray-700 mb-3">Select Lecture</h3>
            <div className="flex flex-wrap gap-2">
              <button
                onClick={() => setSelectedLectureId(null)}
                className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
                  selectedLectureId === null ? 'bg-primary-600 text-white' : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                }`}
              >
                All Lectures
              </button>
              {lectures.map((lecture) => (
                <button
                  key={lecture.id}
                  onClick={() => setSelectedLectureId(lecture.id)}
                  className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
                    selectedLectureId === lecture.id ? 'bg-primary-600 text-white' : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                  }`}
                >
                  {lecture.original_name}
                </button>
              ))}
            </div>
          </div>
        )}

        <div className="border-b border-gray-200">
          <nav className="-mb-px flex space-x-8">
            <button
              onClick={() => setActiveTab('overview')}
              className={`py-2 px-1 border-b-2 font-medium text-sm ${
                activeTab === 'overview'
                  ? 'border-primary-500 text-primary-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              Overview
            </button>
            <button
              onClick={() => setActiveTab('queries')}
              className={`py-2 px-1 border-b-2 font-medium text-sm ${
                activeTab === 'queries'
                  ? 'border-primary-500 text-primary-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              All Queries
            </button>
          </nav>
        </div>
      </div>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {activeTab === 'overview' ? (
          <div className="space-y-8">
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-5">
                <p className="text-xs text-gray-500 mb-1">Total Questions (course)</p>
                <p className="text-2xl font-bold text-gray-900">{totalQuestions}</p>
              </div>
              <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-5">
                <p className="text-xs text-gray-500 mb-1">Active Students (last 7 days)</p>
                <p className="text-2xl font-bold text-gray-900">{activeStudentsLast7Days}</p>
              </div>
              <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-5">
                <p className="text-xs text-gray-500 mb-1">Most Confusing Lecture</p>
                <p className="text-sm font-semibold text-gray-900 line-clamp-2">
                  {mostConfusingLecture?.lecture_name || 'N/A'}
                </p>
                <p className="text-xs text-gray-500 mt-1">
                  {mostConfusingLecture ? `${mostConfusingLecture.query_count} questions` : ''}
                </p>
              </div>
              <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-5">
                <p className="text-xs text-gray-500 mb-1">Lectures with questions</p>
                <p className="text-2xl font-bold text-gray-900">{lecturesWithQuestions}</p>
                <p className="text-xs text-gray-500 mt-1">of {health?.lectures?.length ?? 0} lectures</p>
              </div>
            </div>

            <RecurringTopicsCard
              questions={queriesList.map((query) => query.question || '')}
              showAll={showAllRecurringTopics}
              onToggleShowAll={setShowAllRecurringTopics}
            />

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
                <h2 className="text-xl font-semibold text-gray-900 mb-4">Questions per Lecture</h2>
                {renderLectureBars(false)}
              </div>
              <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
                <h2 className="text-xl font-semibold text-gray-900 mb-4">Questions per Lecture (all)</h2>
                {renderLectureBars(true)}
              </div>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
                <h2 className="text-xl font-semibold text-gray-900 mb-4">Top 5 Lectures by Confusion</h2>
                {topLecturesByConfusion.length > 0 ? (
                  <div className="space-y-3">
                    {topLecturesByConfusion.map((lecture, index) => (
                      <div key={lecture.lecture_id} className="flex items-center justify-between">
                        <div className="text-sm text-gray-700 truncate">
                          {index + 1}. {lecture.lecture_name}
                        </div>
                        <span className="text-sm text-gray-500">{lecture.query_count} questions</span>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-sm text-gray-500">No lecture data available yet.</p>
                )}
              </div>

              <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
                <h2 className="text-xl font-semibold text-gray-900 mb-4">Most Active Students</h2>
                {topStudents.length > 0 ? (
                  <div className="space-y-3">
                    {topStudents.map(([student, count], index) => (
                      <div key={student} className="flex items-center justify-between">
                        <div className="text-sm text-gray-700 truncate">
                          {index + 1}. {student}
                        </div>
                        <span className="text-sm text-gray-500">{count} questions</span>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-sm text-gray-500">No student activity yet.</p>
                )}
              </div>
            </div>
          </div>
        ) : (
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
            <h2 className="text-xl font-semibold text-gray-900 mb-4">All Student Queries</h2>
            {queries && queries.queries.length > 0 ? (
              <div className="space-y-4">
                {queries.queries.map((query) => (
                  <div key={query.id} className="border border-gray-200 rounded-lg p-4">
                    <div className="flex items-start justify-between mb-2">
                      <div className="flex-1">
                        <p className="font-medium text-gray-900">{query.question}</p>
                        <div className="flex items-center gap-3 mt-1 text-sm text-gray-500">
                          {query.lecture_name && <span>From: {query.lecture_name}</span>}
                          {query.user_email && <span className="text-primary-600">Student: {query.user_email}</span>}
                        </div>
                      </div>
                      {query.created_at && (
                        <span className="text-xs text-gray-400 ml-4">
                          {new Date(query.created_at).toLocaleDateString()}
                        </span>
                      )}
                    </div>
                    <p className="text-sm text-gray-700 mt-2 whitespace-pre-wrap">{query.answer}</p>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-sm text-gray-500">No queries found.</p>
            )}
          </div>
        )}
      </main>
    </div>
  );
}
