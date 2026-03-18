'use client';

import { useEffect, useState } from 'react';
import {
  apiClient,
  CourseStudent,
  LectureHealthMetric,
  QueryListItem,
} from '@/lib/api';
import { summarizeQuestionTopics } from '@/lib/queryTopics';

type CourseAnalyticsOverviewProps = {
  courseId: number;
};

export default function CourseAnalyticsOverview({ courseId }: CourseAnalyticsOverviewProps) {
  const [analytics, setAnalytics] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [topConfusedLecture, setTopConfusedLecture] = useState<string | null>(null);
  const [lectureHealth, setLectureHealth] = useState<LectureHealthMetric[]>([]);
  const [courseQueries, setCourseQueries] = useState<QueryListItem[]>([]);
  const [courseQueryTotal, setCourseQueryTotal] = useState<number | null>(null);
  const [courseStudents, setCourseStudents] = useState<CourseStudent[]>([]);
  const [showQuestionDetails, setShowQuestionDetails] = useState(false);
  const [showStudentDetails, setShowStudentDetails] = useState(false);
  const [showConfusedLectures, setShowConfusedLectures] = useState(false);
  const [showAllTopics, setShowAllTopics] = useState(false);
  const [loadingQuestionDetails, setLoadingQuestionDetails] = useState(false);
  const [loadingStudentDetails, setLoadingStudentDetails] = useState(false);
  const [loadingConfusedLectureDetails, setLoadingConfusedLectureDetails] = useState(false);

  useEffect(() => {
    const loadAnalytics = async () => {
      try {
        const [data, health] = await Promise.all([
          apiClient.getCourseAnalytics(courseId),
          apiClient.getLectureHealth(courseId),
        ]);
        setAnalytics(data);
        setLectureHealth(health.lectures);
        const topLecture = health.lectures.reduce<{ lecture_name: string; query_count: number } | null>(
          (max, current) => {
            if (!max || current.query_count > max.query_count) {
              return current;
            }

            return max;
          },
          null
        );
        setTopConfusedLecture(topLecture && topLecture.query_count > 0 ? topLecture.lecture_name : null);
      } catch (error) {
        console.error('Failed to load analytics:', error);
      } finally {
        setLoading(false);
      }
    };

    void loadAnalytics();
  }, [courseId]);

  const loadQuestionDetails = async () => {
    setLoadingQuestionDetails(true);
    try {
      const response = await apiClient.getAllQueries(1000, undefined, courseId);
      setCourseQueries(response.queries);
      setCourseQueryTotal(response.total);
    } catch (error) {
      console.error('Failed to load course queries:', error);
    } finally {
      setLoadingQuestionDetails(false);
    }
  };

  const loadStudentDetails = async () => {
    setLoadingStudentDetails(true);
    try {
      const students = await apiClient.getCourseStudents(courseId);
      setCourseStudents(students);
    } catch (error) {
      console.error('Failed to load course students:', error);
    } finally {
      setLoadingStudentDetails(false);
    }
  };

  const loadConfusedLectureDetails = async () => {
    setLoadingConfusedLectureDetails(true);
    try {
      const health = await apiClient.getLectureHealth(courseId);
      setLectureHealth(health.lectures);
    } catch (error) {
      console.error('Failed to load lecture health:', error);
    } finally {
      setLoadingConfusedLectureDetails(false);
    }
  };

  if (loading) {
    return (
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
        <div className="text-center py-8">
          <svg className="w-8 h-8 animate-spin mx-auto text-primary-500" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
          </svg>
          <p className="mt-4 text-gray-500">Loading analytics...</p>
        </div>
      </div>
    );
  }

  if (!analytics) {
    return (
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
        <p className="text-gray-500">
          No questions yet. Student activity will appear once the lecture becomes active.
        </p>
      </div>
    );
  }

  const sortedStudents = [...courseStudents].sort((a, b) => b.questions_count - a.questions_count);
  const sortedConfusedLectures = [...lectureHealth].sort((a, b) => b.query_count - a.query_count);
  const rawQuestions = (analytics.top_confused_topics || []).flatMap((topic: any) =>
    topic.questions || (topic.topic ? [topic.topic] : [])
  );
  const { ignoredCount, recurringTopics, topicsAll } = summarizeQuestionTopics(rawQuestions);
  const visibleTopics = showAllTopics ? topicsAll : topicsAll.slice(0, 2);
  const remainingTopicCount = Math.max(0, topicsAll.length - visibleTopics.length);

  const handleExportQuestions = async () => {
    try {
      const blob = await apiClient.exportCourseQuestions(courseId);
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `course_${courseId}_questions.csv`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);
    } catch (error: any) {
      alert(error.response?.data?.detail || 'Failed to export questions');
    }
  };

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
      <div className="flex items-center justify-between mb-6">
        <h3 className="text-xl font-semibold text-gray-900">Course Analytics Overview</h3>
        <button onClick={handleExportQuestions} className="text-base text-gray-500 hover:text-gray-700">
          Export Questions CSV
        </button>
      </div>

      <div className="mb-6">
        <p className="text-base text-gray-600 mb-4">How are students interacting with this course?</p>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
          <button
            type="button"
            onClick={async () => {
              const next = !showQuestionDetails;
              setShowQuestionDetails(next);
              if (next) {
                await loadQuestionDetails();
              }
            }}
            className="bg-gray-50 rounded-lg p-5 border border-gray-200 text-left hover:border-gray-300 focus:outline-none focus:ring-2 focus:ring-primary-500"
          >
            <div className="flex items-center gap-2 text-sm text-gray-500 mb-1">
              <span>💬</span>
              <span>Total Questions</span>
            </div>
            <p className="text-3xl font-bold text-gray-900">{analytics.total_questions}</p>
            <p className="mt-1 text-sm text-gray-400">Tap to view</p>
          </button>
          <button
            type="button"
            onClick={async () => {
              const next = !showStudentDetails;
              setShowStudentDetails(next);
              if (next) {
                await loadStudentDetails();
              }
            }}
            className="bg-gray-50 rounded-lg p-5 border border-gray-200 text-left hover:border-gray-300 focus:outline-none focus:ring-2 focus:ring-primary-500"
          >
            <div className="flex items-center gap-2 text-sm text-gray-500 mb-1">
              <span>👥</span>
              <span>Active Students</span>
            </div>
            <p className="text-3xl font-bold text-gray-900">{analytics.active_students}</p>
            <p className="mt-1 text-sm text-gray-400">Tap to view</p>
          </button>
          <button
            type="button"
            onClick={async () => {
              const next = !showConfusedLectures;
              setShowConfusedLectures(next);
              if (next) {
                await loadConfusedLectureDetails();
              }
            }}
            className="bg-gray-50 rounded-lg p-5 border border-gray-200 text-left hover:border-gray-300 focus:outline-none focus:ring-2 focus:ring-primary-500"
          >
            <div className="flex items-center gap-2 text-sm text-gray-500 mb-1">
              <span>🧠</span>
              <span>Top Confused Lecture</span>
            </div>
            <p className="text-base font-semibold text-gray-900 line-clamp-2">{topConfusedLecture || 'No data yet'}</p>
            <p className="mt-1 text-sm text-gray-400">Tap to view</p>
          </button>
          <div className="bg-gray-50 rounded-lg p-5 border border-gray-200">
            <div className="flex items-center gap-2 text-sm text-gray-500 mb-1">
              <span>📈</span>
              <span>Trend (Last 7 days)</span>
            </div>
            <div className="flex items-center text-base">
              {analytics.trend_direction === 'up' ? (
                <span className="text-red-600 font-semibold">↑ +{analytics.trend_percentage}%</span>
              ) : analytics.trend_direction === 'down' ? (
                <span className="text-green-600 font-semibold">↓ -{analytics.trend_percentage}%</span>
              ) : (
                <span className="text-gray-600 font-semibold">→ Stable</span>
              )}
            </div>
          </div>
        </div>

        {showQuestionDetails && (
          <div className="bg-white border border-gray-200 rounded-lg p-4 mb-6">
            <div className="flex items-center justify-between mb-3">
              <h4 className="text-base font-semibold text-gray-900">All Questions</h4>
              <span className="text-sm text-gray-500">{courseQueryTotal ?? courseQueries.length} total</span>
            </div>
            {loadingQuestionDetails ? (
              <p className="text-base text-gray-500">Loading questions...</p>
            ) : courseQueries.length === 0 ? (
              <p className="text-base text-gray-500">
                No questions found. Ask a course question to populate this list.
              </p>
            ) : (
              <div className="max-h-80 overflow-y-auto space-y-3">
                {courseQueries.map((item) => (
                  <div key={item.id} className="border border-gray-100 rounded-md p-3 bg-gray-50">
                    <p className="text-base text-gray-900">{item.question}</p>
                    <p className="text-sm text-gray-500 mt-1">
                      {item.user_email || 'Anonymous'} • {item.lecture_name || 'Course'}{' '}
                      {item.created_at && `• ${new Date(item.created_at).toLocaleString()}`}
                    </p>
                  </div>
                ))}
                {courseQueryTotal && courseQueryTotal > courseQueries.length && (
                  <p className="text-sm text-gray-500">
                    Showing latest {courseQueries.length} of {courseQueryTotal} questions.
                  </p>
                )}
              </div>
            )}
          </div>
        )}

        {showStudentDetails && (
          <div className="bg-white border border-gray-200 rounded-lg p-4 mb-6">
            <div className="flex items-center justify-between mb-3">
              <h4 className="text-base font-semibold text-gray-900">Active Students</h4>
              <span className="text-sm text-gray-500">{sortedStudents.length} listed</span>
            </div>
            {loadingStudentDetails ? (
              <p className="text-base text-gray-500">Loading students...</p>
            ) : sortedStudents.length === 0 ? (
              <p className="text-base text-gray-500">
                No students found yet. Add students to view their activity.
              </p>
            ) : (
              <div className="max-h-64 overflow-y-auto space-y-2">
                {sortedStudents.map((student) => (
                  <div key={student.student_id} className="flex items-center justify-between text-base">
                    <span className="text-gray-800">{student.student_email}</span>
                    <span className="text-gray-500">
                      {student.questions_count} q{student.questions_count === 1 ? '' : 's'}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {showConfusedLectures && (
          <div className="bg-white border border-gray-200 rounded-lg p-4 mb-6">
            <div className="flex items-center justify-between mb-3">
              <h4 className="text-base font-semibold text-gray-900">Top Confused Lectures</h4>
              <span className="text-sm text-gray-500">{sortedConfusedLectures.length} listed</span>
            </div>
            {loadingConfusedLectureDetails ? (
              <p className="text-base text-gray-500">Loading lecture analytics...</p>
            ) : sortedConfusedLectures.length === 0 ? (
              <p className="text-base text-gray-500">
                No lecture analytics yet. Upload lectures or ask questions to generate data.
              </p>
            ) : (
              <div className="space-y-2">
                {sortedConfusedLectures.map((lecture, index) => (
                  <div key={lecture.lecture_id} className="flex items-center justify-between text-base">
                    <span className="text-gray-800">
                      {index + 1}. {lecture.lecture_name || 'Lecture'}
                    </span>
                    <span className="text-gray-500">
                      {lecture.query_count} q{lecture.query_count === 1 ? '' : 's'}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        <div className="bg-primary-50 border border-primary-200 rounded-lg p-4 mb-6">
          <h4 className="text-base font-semibold text-gray-900 mb-2">Course Overview</h4>
          <ul className="text-base text-gray-700 space-y-1">
            <li>• {analytics.total_questions} questions asked</li>
            <li>• {recurringTopics.length} recurring topics</li>
            {analytics.trend_direction === 'up' && (
              <li className="text-red-600">• Confusion increased this week (+{analytics.trend_percentage}%)</li>
            )}
            {analytics.trend_direction === 'down' && (
              <li className="text-green-600">• Confusion decreased this week (-{analytics.trend_percentage}%)</li>
            )}
          </ul>
        </div>

        <div>
          <h4 className="text-base font-semibold text-gray-900 mb-3">Confusion Topics</h4>
          {ignoredCount > 0 && (
            <p className="text-sm text-gray-500 mb-3">
              {ignoredCount} question{ignoredCount === 1 ? '' : 's'} ignored (non-conceptual).
            </p>
          )}
          {topicsAll.length === 0 ? (
            <p className="text-base text-gray-500">
              No recurring topics yet. Ask more questions to surface patterns.
            </p>
          ) : (
            <>
              <div className="space-y-2">
                {visibleTopics.map((topic, index) => (
                  <div key={`${topic.topic}-${index}`} className="bg-gray-50 border border-gray-200 rounded-lg p-4">
                    <div className="flex items-start justify-between mb-1">
                      <p className="text-base font-medium text-gray-900">
                        {index + 1}. {topic.topic}
                      </p>
                      <span className="text-sm text-gray-500 bg-white px-2 py-1 rounded">{topic.count} questions</span>
                    </div>
                    {topic.questions.length > 0 && (
                      <div className="mt-2 text-sm text-gray-600 space-y-1">
                        {topic.questions.slice(0, 2).map((question, questionIndex) => (
                          <p key={questionIndex} className="pl-2 border-l-2 border-gray-300">
                            "{question}"
                          </p>
                        ))}
                      </div>
                    )}
                  </div>
                ))}
              </div>
              {remainingTopicCount > 0 && !showAllTopics && (
                <button
                  type="button"
                  onClick={() => setShowAllTopics(true)}
                  className="mt-3 text-base text-gray-600 hover:text-gray-800"
                >
                  Show more (+{remainingTopicCount} remaining topics)
                </button>
              )}
              {showAllTopics && topicsAll.length > 2 && (
                <button
                  type="button"
                  onClick={() => setShowAllTopics(false)}
                  className="mt-3 text-base text-gray-600 hover:text-gray-800"
                >
                  Show less
                </button>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
