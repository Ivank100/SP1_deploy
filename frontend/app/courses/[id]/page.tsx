'use client';

import { useState, useEffect, useRef } from 'react';
import { useRouter, useParams } from 'next/navigation';
import {
  apiClient,
  Course,
  QueryResponse,
  User,
  CourseStudent,
  UploadRequest,
  LectureHealthMetric,
} from '@/lib/api';
import FileUpload from '@/components/FileUpload';
import LectureList from '@/components/LectureList';
import Link from 'next/link';
import CourseAnalyticsOverview from '@/components/courses/CourseAnalyticsOverview';
import { describeSource } from '@/lib/formatters';
import { useCoursePage } from '@/hooks/useCoursePage';

export default function CourseDetailPage() {
  const router = useRouter();
  const params = useParams();
  const courseId = parseInt(params.id as string);
  type Category = 'all' | 'analytics' | 'lectures' | 'students' | 'uploads' | 'announcements' | 'questions';
  const instructorCategories: Category[] = ['all', 'analytics', 'lectures', 'students', 'uploads', 'announcements'];
  const studentCategories: Category[] = ['all', 'lectures', 'uploads', 'announcements', 'questions'];
  
  const { user, course, loading, refreshing, setRefreshing, loadCourse } = useCoursePage(courseId, router);
  const [activeCategory, setActiveCategory] = useState<Category>('all');
  const [courseQuestion, setCourseQuestion] = useState('');
  const [courseAsking, setCourseAsking] = useState(false);
  const [courseAnswer, setCourseAnswer] = useState<QueryResponse | null>(null);
  const [courseChatMessages, setCourseChatMessages] = useState<{ question: string; answer: QueryResponse | null }[]>([]);
  const [queryError, setQueryError] = useState<string | null>(null);
  const courseChatEndRef = useRef<HTMLDivElement>(null);
  const [courseStudents, setCourseStudents] = useState<Record<number, CourseStudent[]>>({});
  const [addingStudent, setAddingStudent] = useState<Record<number, boolean>>({});
  const [newStudentEmail, setNewStudentEmail] = useState<Record<number, string>>({});
  const [studentError, setStudentError] = useState<Record<number, string | null>>({});
  const [loadingStudents, setLoadingStudents] = useState<Record<number, boolean>>({});
  const [studentRole, setStudentRole] = useState<Record<number, 'student' | 'ta'>>({});
  const [showManageStudents, setShowManageStudents] = useState<Record<number, boolean>>({});
  const [showStudentsMore, setShowStudentsMore] = useState<Record<number, boolean>>({});
  const [announcements, setAnnouncements] = useState<Record<number, { id: number; message: string; created_at?: string | null }[]>>({});
  const [newAnnouncement, setNewAnnouncement] = useState<Record<number, string>>({});
  const [announcementError, setAnnouncementError] = useState<Record<number, string | null>>({});
  const [postingAnnouncement, setPostingAnnouncement] = useState<Record<number, boolean>>({});
  const [uploadRequests, setUploadRequests] = useState<Record<number, UploadRequest[]>>({});
  const [loadingUploadRequests, setLoadingUploadRequests] = useState<Record<number, boolean>>({});
  const [canReviewUploads, setCanReviewUploads] = useState<Record<number, boolean>>({});
  const [myUploadRequests, setMyUploadRequests] = useState<Record<number, UploadRequest[]>>({});
  const [loadingMyUploadRequests, setLoadingMyUploadRequests] = useState<Record<number, boolean>>({});
  const [showAllInstructorLectures, setShowAllInstructorLectures] = useState<Record<number, boolean>>({});
  const [showAllStudentLectures, setShowAllStudentLectures] = useState<Record<number, boolean>>({});
  const [collapseLectures, setCollapseLectures] = useState<Record<number, boolean>>({});
  const [collapseUploadRequests, setCollapseUploadRequests] = useState<Record<number, boolean>>({});
  const [collapseStudentAnnouncements, setCollapseStudentAnnouncements] = useState<Record<number, boolean>>({});
  const [collapseAskQuestions, setCollapseAskQuestions] = useState<Record<number, boolean>>({});
  const [collapseInstructorAnnouncements, setCollapseInstructorAnnouncements] = useState<Record<number, boolean>>({});
  const [collapseManageStudents, setCollapseManageStudents] = useState<Record<number, boolean>>({});
  const [lectureHealthByCourse, setLectureHealthByCourse] = useState<Record<number, LectureHealthMetric[]>>({});

  useEffect(() => {
    setCourseChatMessages([]);
    setQueryError(null);
    setCourseAnswer(null);
  }, [courseId]);

  useEffect(() => {
    if (user && courseId) {
      loadAnnouncements(courseId);
    }
  }, [user, courseId]);

  useEffect(() => {
    if (user?.role === 'student' && courseId) {
      loadMyUploadRequests(courseId);
    }
  }, [user?.role, courseId]);

  useEffect(() => {
    if (user?.role === 'instructor' && courseId) {
      apiClient
        .getLectureHealth(courseId)
        .then((response) => {
          setLectureHealthByCourse((prev) => ({ ...prev, [courseId]: response.lectures }));
        })
        .catch((error) => {
          console.error('Failed to load lecture health:', error);
        });
    }
  }, [user?.role, courseId]);

  useEffect(() => {
    if ((user?.role === 'instructor' || user?.role === 'ta') && courseId) {
      loadUploadRequests(courseId);
    }
  }, [user?.role, courseId]);

  useEffect(() => {
    if (!user?.role) return;
    const allowed = user.role === 'instructor' ? instructorCategories : studentCategories;
    if (!allowed.includes(activeCategory)) {
      setActiveCategory('all');
    }
  }, [user?.role, activeCategory, instructorCategories, studentCategories]);

  useEffect(() => {
    if (user?.role === 'instructor' && courseId) {
      loadCourseStudents(courseId);
    }
  }, [user?.role, courseId]);

  useEffect(() => {
    const interval = setInterval(() => {
      if (course) {
        const hasProcessing = course.lectures.some(lecture => lecture.status === 'processing');
        if (hasProcessing) {
          loadCourse();
        }
      }
    }, 4000);

    return () => clearInterval(interval);
  }, [course, loadCourse]);

  const handleUploadSuccess = () => {
    setRefreshing(true);
    loadCourse();
  };

  const handleDelete = async (id: number) => {
    try {
      await apiClient.deleteLecture(id);
      await loadCourse();
    } catch (error) {
      console.error('Failed to delete lecture:', error);
      alert('Failed to delete lecture');
    }
  };

  const handleLeaveCourse = async () => {
    if (!course) return;
    if (!confirm('Leave this course? You will lose access to its lectures.')) {
      return;
    }
    try {
      await apiClient.leaveCourse(course.id);
      router.push('/');
    } catch (error: any) {
      alert(error.response?.data?.detail || 'Failed to leave course');
    }
  };

  const handleCourseQuery = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!course || !courseQuestion.trim()) {
      return;
    }
    const questionText = courseQuestion.trim();
    setCourseQuestion('');
    setCourseAsking(true);
    setQueryError(null);
    setCourseAnswer(null);
    setCourseChatMessages((prev) => [...prev, { question: questionText, answer: null }]);
    try {
      const response = await apiClient.queryCourse(course.id, questionText);
      setCourseChatMessages((prev) => {
        const next = [...prev];
        next[next.length - 1] = { question: next[next.length - 1].question, answer: response };
        return next;
      });
    } catch (error: any) {
      console.error('Failed to query course:', error);
      setQueryError(error.response?.data?.detail || 'Failed to get course answer.');
      setCourseChatMessages((prev) => prev.slice(0, -1));
    } finally {
      setCourseAsking(false);
    }
  };

  useEffect(() => {
    courseChatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [courseChatMessages, courseAsking]);

  const loadCourseStudents = async (courseId: number) => {
    if (user?.role !== 'instructor') return;

    setLoadingStudents((prev) => ({ ...prev, [courseId]: true }));
    setStudentError((prev) => ({ ...prev, [courseId]: null }));
    try {
      const students = await apiClient.getCourseStudents(courseId);
      setCourseStudents((prev) => ({ ...prev, [courseId]: students }));
    } catch (error: any) {
      setStudentError((prev) => ({
        ...prev,
        [courseId]: error.response?.data?.detail || 'Failed to load students',
      }));
    } finally {
      setLoadingStudents((prev) => ({ ...prev, [courseId]: false }));
    }
  };

  const loadAnnouncements = async (courseId: number) => {
    try {
      const response = await apiClient.getAnnouncements(courseId);
      setAnnouncements((prev) => ({ ...prev, [courseId]: response.announcements }));
    } catch (error) {
      console.error('Failed to load announcements:', error);
    }
  };

  const loadUploadRequests = async (courseId: number) => {
    setLoadingUploadRequests((prev) => ({ ...prev, [courseId]: true }));
    try {
      const response = await apiClient.getUploadRequests(courseId, 'pending');
      setUploadRequests((prev) => ({ ...prev, [courseId]: response.requests }));
      setCanReviewUploads((prev) => ({ ...prev, [courseId]: true }));
    } catch (error: any) {
      if (error.response?.status === 403) {
        setCanReviewUploads((prev) => ({ ...prev, [courseId]: false }));
      } else {
        console.error('Failed to load upload requests:', error);
      }
    } finally {
      setLoadingUploadRequests((prev) => ({ ...prev, [courseId]: false }));
    }
  };

  const loadMyUploadRequests = async (courseId: number) => {
    setLoadingMyUploadRequests((prev) => ({ ...prev, [courseId]: true }));
    try {
      const response = await apiClient.getMyUploadRequests(courseId);
      setMyUploadRequests((prev) => ({ ...prev, [courseId]: response.requests }));
    } catch (error) {
      console.error('Failed to load my upload requests:', error);
    } finally {
      setLoadingMyUploadRequests((prev) => ({ ...prev, [courseId]: false }));
    }
  };

  const refreshUploadRequestState = async (courseId: number, options?: { reloadCourse?: boolean }) => {
    const tasks: Promise<unknown>[] = [loadMyUploadRequests(courseId)];
    if (user?.role === 'instructor' || user?.role === 'ta') {
      tasks.push(loadUploadRequests(courseId));
    }
    if (options?.reloadCourse) {
      tasks.push(loadCourse());
    }
    await Promise.all(tasks);
  };

  const handleAddStudent = async (courseId: number) => {
    const email = newStudentEmail[courseId]?.trim();
    if (!email) {
      setStudentError({ ...studentError, [courseId]: 'Email is required' });
      return;
    }

    setAddingStudent({ ...addingStudent, [courseId]: true });
    setStudentError({ ...studentError, [courseId]: null });
    try {
      const role = studentRole[courseId] || 'student';
      await apiClient.addStudentToCourse(courseId, email, role);
      setNewStudentEmail({ ...newStudentEmail, [courseId]: '' });
      await loadCourseStudents(courseId);
    } catch (error: any) {
      setStudentError({ ...studentError, [courseId]: error.response?.data?.detail || 'Failed to add student' });
    } finally {
      setAddingStudent({ ...addingStudent, [courseId]: false });
    }
  };

  const handleRemoveStudent = async (courseId: number, studentId: number) => {
    if (!confirm('Are you sure you want to remove this student from the course?')) {
      return;
    }

    try {
      await apiClient.removeStudentFromCourse(courseId, studentId);
      await loadCourseStudents(courseId);
    } catch (error: any) {
      alert(error.response?.data?.detail || 'Failed to remove student');
    }
  };

  const handleUpdateStudent = async (
    courseId: number,
    studentId: number,
    payload: { role?: 'student' | 'ta' }
  ) => {
    try {
      await apiClient.updateStudentAssignment(courseId, studentId, payload);
      await loadCourseStudents(courseId);
    } catch (error: any) {
      alert(error.response?.data?.detail || 'Failed to update student');
    }
  };

  const handlePostAnnouncement = async (courseId: number) => {
    const message = newAnnouncement[courseId]?.trim();
    if (!message) return;
    setPostingAnnouncement({ ...postingAnnouncement, [courseId]: true });
    setAnnouncementError({ ...announcementError, [courseId]: null });
    try {
      await apiClient.createAnnouncement(courseId, message);
      setNewAnnouncement({ ...newAnnouncement, [courseId]: '' });
      await loadAnnouncements(courseId);
    } catch (error: any) {
      setAnnouncementError({ ...announcementError, [courseId]: error.response?.data?.detail || 'Failed to post announcement' });
    } finally {
      setPostingAnnouncement({ ...postingAnnouncement, [courseId]: false });
    }
  };

  const handleApproveUpload = async (courseId: number, requestId: number) => {
    try {
      await apiClient.approveUploadRequest(courseId, requestId);
      await refreshUploadRequestState(courseId, { reloadCourse: true });
    } catch (error: any) {
      alert(error.response?.data?.detail || 'Failed to approve upload');
    }
  };

  const handleRejectUpload = async (courseId: number, requestId: number) => {
    try {
      await apiClient.rejectUploadRequest(courseId, requestId);
      await refreshUploadRequestState(courseId);
    } catch (error: any) {
      alert(error.response?.data?.detail || 'Failed to reject upload');
    }
  };

  const handleDeleteUploadRequest = async (courseId: number, requestId: number, status: string) => {
    const actionLabel = status === 'pending' ? 'cancel this upload request' : 'remove this upload request';
    if (!confirm(`Are you sure you want to ${actionLabel}?`)) {
      return;
    }

    try {
      await apiClient.deleteUploadRequest(courseId, requestId);
      await refreshUploadRequestState(courseId);
    } catch (error: any) {
      alert(error.response?.data?.detail || 'Failed to remove upload request');
    }
  };

  const renderStudentManagement = (courseId: number) => {
    const students = courseStudents[courseId] || [];
    const isLoading = loadingStudents[courseId];
    const isAdding = addingStudent[courseId];
    const error = studentError[courseId];
    const email = newStudentEmail[courseId] || '';
    const role = studentRole[courseId] || 'student';

    return (
      <div className="space-y-4">
        <div>
          <h4 className="text-base font-medium text-gray-900 mb-2">Add Student</h4>
          <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
            <input
              type="email"
              value={email}
              onChange={(e) => setNewStudentEmail({ ...newStudentEmail, [courseId]: e.target.value })}
              placeholder="student@example.com"
              className="flex-1 px-4 py-2 text-base border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
              onKeyPress={(e) => {
                if (e.key === 'Enter') {
                  e.preventDefault();
                  handleAddStudent(courseId);
                }
              }}
            />
            <select
              value={role}
              onChange={(e) => setStudentRole({ ...studentRole, [courseId]: e.target.value as 'student' | 'ta' })}
              className="px-4 py-2 text-base border border-gray-300 rounded-lg min-w-[100px]"
            >
              <option value="student">Student</option>
              <option value="ta">TA</option>
            </select>
            <button
              onClick={() => handleAddStudent(courseId)}
              disabled={isAdding}
              className="px-4 py-2 text-base bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isAdding ? 'Adding...' : 'Add'}
            </button>
          </div>
          {error && (
            <p className="mt-1 text-sm text-red-600">{error}</p>
          )}
        </div>

        <div>
          <h4 className="text-base font-medium text-gray-900 mb-2">
            Enrolled Students ({students.length})
          </h4>
          <div className="flex flex-wrap gap-2 mb-3">
            <button
              onClick={() => setShowManageStudents({ ...showManageStudents, [courseId]: true })}
              className="px-4 py-2 text-base rounded-full border border-gray-200 text-gray-700"
            >
              Manage Students
            </button>
            <button
              onClick={() => setShowStudentsMore({ ...showStudentsMore, [courseId]: true })}
              className="px-4 py-2 text-base rounded-full border border-dashed border-gray-300 text-gray-600"
            >
              Show More
            </button>
          </div>
          {isLoading ? (
            <p className="text-sm text-gray-500">Loading...</p>
          ) : students.length === 0 ? (
            <p className="text-sm text-gray-500">No students enrolled yet</p>
          ) : (
            <div className="space-y-2">
              {students.map((student, index) => (
                <div
                  key={student.student_id}
                  className="w-full flex items-center justify-between px-3 py-2 bg-white border border-gray-200 rounded text-base"
                >
                  <span className="text-gray-500 text-sm w-6">{index + 1}.</span>
                  <span className="flex-1 text-gray-800">{student.student_email}</span>
                  <span className="text-gray-500 text-sm">{student.role}</span>
                </div>
              ))}
            </div>
          )}
        </div>

        {showManageStudents[courseId] && (
          <div className="fixed inset-0 bg-black bg-opacity-40 flex items-center justify-center z-50 p-6">
            <div className="bg-white rounded-xl shadow-xl max-w-6xl w-full max-h-[90vh] overflow-y-auto p-8">
              <div className="flex items-center justify-between mb-6">
                <h4 className="text-xl font-semibold text-gray-900">Manage Students</h4>
                <button
                  onClick={() => setShowManageStudents({ ...showManageStudents, [courseId]: false })}
                  className="text-gray-400 hover:text-gray-600 text-2xl p-2"
                >
                  ✕
                </button>
              </div>
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-4 py-3 text-left text-sm font-medium text-gray-500 uppercase">#</th>
                      <th className="px-4 py-3 text-left text-sm font-medium text-gray-500 uppercase">Email</th>
                      <th className="px-4 py-3 text-left text-sm font-medium text-gray-500 uppercase">Role</th>
                      <th className="px-4 py-3 text-left text-sm font-medium text-gray-500 uppercase">Activity</th>
                      <th className="px-4 py-3" />
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                    {students.map((student, index) => (
                      <tr key={student.student_id}>
                        <td className="px-4 py-3 text-base text-gray-500">{index + 1}</td>
                        <td className="px-4 py-3 text-base text-gray-900">{student.student_email}</td>
                        <td className="px-4 py-3">
                          <select
                            value={student.role}
                            onChange={async (e) => {
                              await handleUpdateStudent(courseId, student.student_id, { role: e.target.value as 'student' | 'ta' });
                              await loadCourseStudents(courseId);
                            }}
                            className="px-3 py-2 text-base border border-gray-300 rounded-lg min-w-[100px]"
                          >
                            <option value="student">Student</option>
                            <option value="ta">TA</option>
                          </select>
                        </td>
                        <td className="px-4 py-3 text-base text-gray-600">
                          {student.questions_count} q{student.questions_count === 1 ? '' : 's'}
                          {student.last_active && (
                            <span className="block text-sm text-gray-400">
                              {new Date(student.last_active).toLocaleDateString()}
                            </span>
                          )}
                        </td>
                        <td className="px-4 py-3 text-right">
                          <button
                            onClick={() => handleRemoveStudent(courseId, student.student_id)}
                            className="text-red-600 hover:text-red-700 text-base font-medium"
                          >
                            Remove
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}

        {showStudentsMore[courseId] && (
          <div className="fixed inset-0 bg-black bg-opacity-40 flex items-center justify-center z-50 p-6">
            <div className="bg-white rounded-xl shadow-xl max-w-6xl w-full max-h-[90vh] overflow-y-auto p-8">
              <div className="flex items-center justify-between mb-6">
                <h4 className="text-xl font-semibold text-gray-900">Student Details</h4>
                <button
                  onClick={() => setShowStudentsMore({ ...showStudentsMore, [courseId]: false })}
                  className="text-gray-400 hover:text-gray-600 text-2xl p-2"
                >
                  ✕
                </button>
              </div>
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-4 py-3 text-left text-sm font-medium text-gray-500 uppercase">#</th>
                      <th className="px-4 py-3 text-left text-sm font-medium text-gray-500 uppercase">Email</th>
                      <th className="px-4 py-3 text-left text-sm font-medium text-gray-500 uppercase">Role</th>
                      <th className="px-4 py-3 text-left text-sm font-medium text-gray-500 uppercase">Activity</th>
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                    {students.map((student, index) => (
                      <tr key={student.student_id}>
                        <td className="px-4 py-3 text-base text-gray-500">{index + 1}</td>
                        <td className="px-4 py-3 text-base text-gray-900">{student.student_email}</td>
                        <td className="px-4 py-3 text-base text-gray-700">{student.role}</td>
                        <td className="px-4 py-3 text-base text-gray-600">
                          {student.questions_count} q{student.questions_count === 1 ? '' : 's'}
                          {student.last_active && (
                            <span className="block text-sm text-gray-400">
                              {new Date(student.last_active).toLocaleDateString()}
                            </span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}
      </div>
    );
  };

  const renderSources = (sources: QueryResponse['sources']) => {
    if (!sources || sources.length === 0) return null;
    return (
      <div className="mt-4">
        <p className="text-base font-semibold text-gray-900 mb-2">Sources</p>
        <div className="space-y-1">
          {sources.map((source, index) => (
            <div key={`${source.lecture_id}-${index}`} className="text-base text-gray-600">
              <span className="font-medium text-primary-600">
                {source.lecture_name || 'Lecture'}
              </span>
              {describeSource(source) && `, ${describeSource(source)}`}
            </div>
          ))}
        </div>
      </div>
    );
  };

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

  const instructorLectures = course.lectures.filter((lecture) => lecture.created_by_role === 'instructor');
  const studentLectures = course.lectures.filter((lecture) => lecture.created_by_role !== 'instructor');
  const lectureHealth = lectureHealthByCourse[course.id] || [];
  const lectureQuestionsById = lectureHealth.reduce<Record<number, number>>((acc, item) => {
    acc[item.lecture_id] = item.query_count;
    return acc;
  }, {});
  const avgQuestions =
    lectureHealth.length > 0
      ? lectureHealth.reduce((sum, item) => sum + item.query_count, 0) / lectureHealth.length
      : 0;
  const showAllInstructor = showAllInstructorLectures[course.id] ?? false;
  const showAllStudents = showAllStudentLectures[course.id] ?? false;
  const visibleInstructorLectures = showAllInstructor ? instructorLectures : instructorLectures.slice(0, 4);
  const visibleStudentLectures = showAllStudents ? studentLectures : studentLectures.slice(0, 4);
  const categoryOptions = user?.role === 'instructor' ? instructorCategories : studentCategories;
  const showLectures = activeCategory === 'all' || activeCategory === 'lectures';
  const showManageStudentsSection = activeCategory === 'all' || activeCategory === 'students';
  const showUploads = activeCategory === 'all' || activeCategory === 'uploads';
  const showAnnouncements = activeCategory === 'all' || activeCategory === 'announcements';
  const showQuestions = activeCategory === 'all' || activeCategory === 'questions';
  const showAnalytics = activeCategory === 'all' || activeCategory === 'analytics';

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
                onClick={() => {
                  apiClient.logout();
                  router.push('/auth/login');
                }}
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
