'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { apiClient, QueryClustersResponse, TrendsResponse, LectureHealthResponse, QueryListResponse, Course, Lecture } from '@/lib/api';
import Link from 'next/link';

export default function InstructorDashboard() {
  const router = useRouter();
  const [user, setUser] = useState(apiClient.getStoredUser());
  const [courses, setCourses] = useState<Course[]>([]);
  const [selectedCourseId, setSelectedCourseId] = useState<number | null>(null);
  const [lectures, setLectures] = useState<Lecture[]>([]);
  const [selectedLectureId, setSelectedLectureId] = useState<number | null>(null);
  const [clusters, setClusters] = useState<QueryClustersResponse | null>(null);
  const [trends, setTrends] = useState<TrendsResponse | null>(null);
  const [health, setHealth] = useState<LectureHealthResponse | null>(null);
  const [queries, setQueries] = useState<QueryListResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<'overview' | 'queries'>('overview');

  useEffect(() => {
    // Check authentication
    if (!apiClient.isAuthenticated()) {
      router.push('/auth/login');
      return;
    }

    loadCourses();
  }, [router]);

  useEffect(() => {
    if (selectedCourseId) {
      loadLectures();
    } else {
      setLectures([]);
      setSelectedLectureId(null);
    }
  }, [selectedCourseId]);

  useEffect(() => {
    loadData();
  }, [selectedCourseId, selectedLectureId]);

  const loadCourses = async () => {
    try {
      const coursesData = await apiClient.getCourses();
      setCourses(coursesData.courses);
      // Don't auto-select - let user choose "All Courses" or a specific course
    } catch (error) {
      console.error('Failed to load courses:', error);
    }
  };

  const loadLectures = async () => {
    if (!selectedCourseId) {
      // When "All Courses" is selected, clear lectures
      setLectures([]);
      setSelectedLectureId(null);
      return;
    }
    try {
      const lecturesData = await apiClient.getLectures(selectedCourseId);
      setLectures(lecturesData.lectures.filter(l => l.status === 'completed'));
      // Reset lecture selection when course changes
      setSelectedLectureId(null);
    } catch (error) {
      console.error('Failed to load lectures:', error);
      setLectures([]);
    }
  };

  const loadData = async () => {
    setLoading(true);
    try {
      // Only pass parameters if they are not null/undefined
      // When "All Lectures" is selected, selectedLectureId is null, so we pass undefined
      // When "All Courses" is selected, selectedCourseId is null, so we pass undefined
      const lectureIdParam = selectedLectureId !== null && selectedLectureId !== undefined ? selectedLectureId : undefined;
      const courseIdParam = selectedCourseId !== null && selectedCourseId !== undefined ? selectedCourseId : undefined;
      
      const [clustersData, trendsData, healthData, queriesData] = await Promise.all([
        apiClient.getQueryClusters(5, lectureIdParam, courseIdParam),
        apiClient.getTrends(30, 'day', courseIdParam, lectureIdParam),
        apiClient.getLectureHealth(courseIdParam, lectureIdParam),
        apiClient.getAllQueries(100, lectureIdParam, courseIdParam),
      ]);
      
      setClusters(clustersData);
      setTrends(trendsData);
      setHealth(healthData);
      setQueries(queriesData);
    } catch (error) {
      console.error('Failed to load analytics:', error);
      // Set empty data on error
      setClusters({ clusters: [], total_questions: 0 });
      setTrends({ trends: [], period: 'day', days: 30 });
      setHealth({ lectures: [], total_lectures: 0 });
      setQueries({ queries: [], total: 0 });
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <svg className="w-8 h-8 animate-spin mx-auto text-primary-500" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
          </svg>
          <p className="mt-4 text-gray-500">Loading analytics...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <div className="flex items-center space-x-4">
              <Link
                href="/"
                className="text-sm font-medium text-gray-700 hover:text-primary-600"
              >
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
                  onClick={() => {
                    apiClient.logout();
                    router.push('/auth/login');
                  }}
                  className="px-3 py-1.5 text-sm font-medium text-white bg-primary-600 hover:bg-primary-700 rounded-md transition-colors"
                >
                  Logout
                </button>
              </div>
            )}
          </div>
        </div>
      </header>

      {/* Course Selector and Tabs */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
        <div className="mb-4">
          <label htmlFor="course-select" className="block text-sm font-medium text-gray-700 mb-2">
            Select Course
          </label>
          <div className="flex flex-wrap gap-2">
            <button
              onClick={() => setSelectedCourseId(null)}
              className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
                selectedCourseId === null
                  ? 'bg-primary-600 text-white'
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              }`}
            >
              All Courses
            </button>
            {courses.map((course) => (
              <button
                key={course.id}
                onClick={() => setSelectedCourseId(course.id)}
                className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
                  selectedCourseId === course.id
                    ? 'bg-primary-600 text-white'
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                }`}
              >
                {course.name}
              </button>
            ))}
          </div>
        </div>
        
        {/* Lecture Selector */}
        {selectedCourseId && lectures.length > 0 && (
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4 mb-6">
            <h3 className="text-sm font-medium text-gray-700 mb-3">Select Lecture</h3>
            <div className="flex flex-wrap gap-2">
              <button
                onClick={() => setSelectedLectureId(null)}
                className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
                  selectedLectureId === null
                    ? 'bg-primary-600 text-white'
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                }`}
              >
                All Lectures
              </button>
              {lectures.map((lecture) => (
                <button
                  key={lecture.id}
                  onClick={() => setSelectedLectureId(lecture.id)}
                  className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
                    selectedLectureId === lecture.id
                      ? 'bg-primary-600 text-white'
                      : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
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

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {activeTab === 'overview' ? (
          <div className="space-y-8">
            {/* Query Clusters */}
            <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
              <h2 className="text-xl font-semibold text-gray-900 mb-4">Topic Clusters</h2>
              {clusters && clusters.clusters.length > 0 ? (
                <div className="space-y-4">
                  {clusters.clusters.map((cluster) => (
                    <div key={cluster.cluster_id} className="border border-gray-200 rounded-lg p-4">
                      <div className="flex items-center justify-between mb-2">
                        <h3 className="font-medium text-gray-900">{cluster.representative_question}</h3>
                        <span className="px-2 py-1 bg-primary-100 text-primary-700 text-xs font-medium rounded">
                          {cluster.count} questions
                        </span>
                      </div>
                      <p className="text-sm text-gray-600 mb-2">Sample questions:</p>
                      <ul className="list-disc pl-5 space-y-1 text-sm text-gray-500">
                        {cluster.questions.slice(0, 3).map((q, idx) => (
                          <li key={idx}>{q}</li>
                        ))}
                      </ul>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-sm text-gray-500">No query clusters available yet.</p>
              )}
            </div>

            {/* Trends */}
            <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
              <h2 className="text-xl font-semibold text-gray-900 mb-4">Query Trends (Last 30 Days)</h2>
              {trends && trends.trends.length > 0 ? (
                <div className="space-y-2">
                  {trends.trends.slice(-10).map((trend) => (
                    <div key={trend.period} className="flex items-center justify-between py-2 border-b border-gray-100">
                      <span className="text-sm text-gray-600">{trend.period}</span>
                      <span className="px-2 py-1 bg-gray-100 text-gray-700 text-xs font-medium rounded">
                        {trend.count} queries
                      </span>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-sm text-gray-500">No trend data available yet.</p>
              )}
            </div>

            {/* Lecture Health */}
            <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
              <h2 className="text-xl font-semibold text-gray-900 mb-4">Lecture Health Metrics</h2>
              {health && health.lectures.length > 0 ? (
                <div className="overflow-x-auto">
                  <table className="min-w-full divide-y divide-gray-200">
                    <thead className="bg-gray-50">
                      <tr>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Lecture</th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Queries</th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Avg Complexity</th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Top Topics</th>
                      </tr>
                    </thead>
                    <tbody className="bg-white divide-y divide-gray-200">
                      {health.lectures.map((lecture) => (
                        <tr key={lecture.lecture_id}>
                          <td className="px-4 py-3 text-sm text-gray-900">{lecture.lecture_name}</td>
                          <td className="px-4 py-3 text-sm text-gray-600">{lecture.query_count}</td>
                          <td className="px-4 py-3 text-sm text-gray-600">{lecture.avg_complexity} words</td>
                          <td className="px-4 py-3 text-sm text-gray-600">
                            {lecture.top_clusters.length > 0 ? (
                              <ul className="list-disc pl-5">
                                {lecture.top_clusters.map((c, idx) => (
                                  <li key={idx} className="truncate max-w-xs" title={c.representative_question}>
                                    {c.representative_question} ({c.count})
                                  </li>
                                ))}
                              </ul>
                            ) : (
                              <span className="text-gray-400">No clusters</span>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <p className="text-sm text-gray-500">No lecture health data available yet.</p>
              )}
            </div>
          </div>
        ) : (
          /* All Queries Tab */
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
                          {query.lecture_name && (
                            <span>From: {query.lecture_name}</span>
                          )}
                          {query.user_email && (
                            <span className="text-primary-600">Student: {query.user_email}</span>
                          )}
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

