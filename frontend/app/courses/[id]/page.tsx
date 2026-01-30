'use client';

import { useState, useEffect, useCallback } from 'react';
import { useRouter, useParams } from 'next/navigation';
import {
  apiClient,
  Course,
  QueryResponse,
  CitationSource,
  User,
  CourseStudent,
  UploadRequest,
  LectureHealthMetric,
} from '@/lib/api';
import FileUpload from '@/components/FileUpload';
import LectureList from '@/components/LectureList';
import Link from 'next/link';

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

// Course Analytics Component
function CourseAnalyticsOverview({ courseId }: { courseId: number }) {
  const [analytics, setAnalytics] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [topConfusedLecture, setTopConfusedLecture] = useState<string | null>(null);

  useEffect(() => {
    loadAnalytics();
  }, [courseId]);

  const loadAnalytics = async () => {
    try {
      const data = await apiClient.getCourseAnalytics(courseId);
      setAnalytics(data);
      const health = await apiClient.getLectureHealth(courseId);
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

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
      <h3 className="text-lg font-semibold text-gray-900 mb-6">Course Analytics Overview</h3>
      
      <div className="mb-6">
        <p className="text-sm text-gray-600 mb-4">How are students interacting with this course?</p>
        
        {/* Summary Cards */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
          <div className="bg-gray-50 rounded-lg p-4 border border-gray-200">
            <div className="flex items-center gap-2 text-xs text-gray-500 mb-1">
              <span>💬</span>
              <span>Total Questions</span>
            </div>
            <p className="text-2xl font-bold text-gray-900">{analytics.total_questions}</p>
          </div>
          <div className="bg-gray-50 rounded-lg p-4 border border-gray-200">
            <div className="flex items-center gap-2 text-xs text-gray-500 mb-1">
              <span>👥</span>
              <span>Active Students</span>
            </div>
            <p className="text-2xl font-bold text-gray-900">{analytics.active_students}</p>
          </div>
          <div className="bg-gray-50 rounded-lg p-4 border border-gray-200">
            <div className="flex items-center gap-2 text-xs text-gray-500 mb-1">
              <span>🧠</span>
              <span>Top Confused Lecture</span>
            </div>
            <p className="text-sm font-semibold text-gray-900 line-clamp-2">
              {topConfusedLecture || 'No data yet'}
            </p>
          </div>
          <div className="bg-gray-50 rounded-lg p-4 border border-gray-200">
            <div className="flex items-center gap-2 text-xs text-gray-500 mb-1">
              <span>📈</span>
              <span>Trend (Last 7 days)</span>
            </div>
            <div className="flex items-center">
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

        {/* Course Overview Summary */}
        <div className="bg-primary-50 border border-primary-200 rounded-lg p-4 mb-6">
          <h4 className="font-semibold text-gray-900 mb-2">Course Overview</h4>
          <ul className="text-sm text-gray-700 space-y-1">
            <li>• {analytics.total_questions} questions asked</li>
            <li>• {analytics.top_confused_topics?.length || 0} recurring topics</li>
            {analytics.trend_direction === 'up' && (
              <li className="text-red-600">• Confusion increased this week (+{analytics.trend_percentage}%)</li>
            )}
            {analytics.trend_direction === 'down' && (
              <li className="text-green-600">• Confusion decreased this week (-{analytics.trend_percentage}%)</li>
            )}
          </ul>
        </div>

        {/* Top Confused Topics */}
        {analytics.top_confused_topics && analytics.top_confused_topics.length > 0 && (
          <div>
            <h4 className="font-semibold text-gray-900 mb-3">Top Confused Topics</h4>
            <div className="space-y-2">
              {analytics.top_confused_topics.map((topic: any, index: number) => (
                <div key={index} className="bg-gray-50 border border-gray-200 rounded-lg p-3">
                  <div className="flex items-start justify-between mb-1">
                    <p className="font-medium text-gray-900">
                      {index + 1}. {topic.topic}
                    </p>
                    <span className="text-xs text-gray-500 bg-white px-2 py-1 rounded">
                      {topic.count} questions
                    </span>
                  </div>
                  {topic.questions && topic.questions.length > 0 && (
                    <div className="mt-2 text-xs text-gray-600 space-y-1">
                      {topic.questions.slice(0, 2).map((q: string, i: number) => (
                        <p key={i} className="pl-2 border-l-2 border-gray-300">"{q}"</p>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default function CourseDetailPage() {
  const router = useRouter();
  const params = useParams();
  const courseId = parseInt(params.id as string);
  
  const [user, setUser] = useState<User | null>(null);
  const [course, setCourse] = useState<Course | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [courseQuestion, setCourseQuestion] = useState('');
  const [courseAsking, setCourseAsking] = useState(false);
  const [courseAnswer, setCourseAnswer] = useState<QueryResponse | null>(null);
  const [queryError, setQueryError] = useState<string | null>(null);
  const [courseStudents, setCourseStudents] = useState<Record<number, CourseStudent[]>>({});
  const [addingStudent, setAddingStudent] = useState<Record<number, boolean>>({});
  const [newStudentEmail, setNewStudentEmail] = useState<Record<number, string>>({});
  const [studentError, setStudentError] = useState<Record<number, string | null>>({});
  const [loadingStudents, setLoadingStudents] = useState<Record<number, boolean>>({});
  const [sections, setSections] = useState<Record<number, { id: number; name: string }[]>>({});
  const [groupsBySection, setGroupsBySection] = useState<Record<number, { id: number; name: string }[]>>({});
  const [selectedSectionId, setSelectedSectionId] = useState<Record<number, number | null>>({});
  const [newSectionName, setNewSectionName] = useState<Record<number, string>>({});
  const [addingSection, setAddingSection] = useState<Record<number, boolean>>({});
  const [newGroupName, setNewGroupName] = useState<Record<number, string>>({});
  const [addingGroup, setAddingGroup] = useState<Record<number, boolean>>({});
  const [showAddSection, setShowAddSection] = useState<Record<number, boolean>>({});
  const [showAddGroup, setShowAddGroup] = useState<Record<number, boolean>>({});
  const [studentRole, setStudentRole] = useState<Record<number, 'student' | 'ta'>>({});
  const [newStudentGroupId, setNewStudentGroupId] = useState<Record<number, number | null>>({});
  const [showManageSections, setShowManageSections] = useState<Record<number, boolean>>({});
  const [showManageGroups, setShowManageGroups] = useState<Record<number, boolean>>({});
  const [showManageStudents, setShowManageStudents] = useState<Record<number, boolean>>({});
  const [showStudentsMore, setShowStudentsMore] = useState<Record<number, boolean>>({});
  const [showGroupsMore, setShowGroupsMore] = useState<Record<number, boolean>>({});
  const [selectedGroupDetail, setSelectedGroupDetail] = useState<Record<number, { id: number; name: string } | null>>({});
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
    if (!apiClient.isAuthenticated()) {
      router.push('/auth/login');
      return;
    }

    const storedUser = apiClient.getStoredUser();
    if (storedUser) {
      setUser(storedUser);
    } else {
      apiClient.getCurrentUser()
        .then(setUser)
        .catch(() => {
          apiClient.logout();
          router.push('/auth/login');
        });
    }
  }, [router]);

  const loadCourse = useCallback(async () => {
    try {
      const coursesResponse = await apiClient.getCourses();
      const foundCourse = coursesResponse.courses.find(c => c.id === courseId);
      if (!foundCourse) {
        router.push('/');
        return;
      }
      setCourse(foundCourse);
    } catch (error) {
      console.error('Failed to load course:', error);
      router.push('/');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [courseId, router]);

  useEffect(() => {
    if (user && courseId) {
      loadCourse();
    }
  }, [user, courseId, loadCourse]);

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
    if (user?.role === 'student' && courseId) {
      loadUploadRequests(courseId);
    }
  }, [user?.role, courseId]);

  useEffect(() => {
    if (user?.role === 'instructor' && courseId) {
      loadCourseStudents(courseId);
      loadSections(courseId);
    }
  }, [user?.role, courseId]);

  useEffect(() => {
    if (user?.role === 'instructor' && course?.id) {
      loadCourseStudents(course.id);
      loadSections(course.id);
    }
  }, [user?.role, course?.id]);

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
    setCourseAsking(true);
    setQueryError(null);
    setCourseAnswer(null);
    try {
      const response = await apiClient.queryCourse(course.id, courseQuestion);
      setCourseAnswer(response);
      setCourseQuestion('');
    } catch (error: any) {
      console.error('Failed to query course:', error);
      setQueryError(error.response?.data?.detail || 'Failed to get course answer.');
    } finally {
      setCourseAsking(false);
    }
  };

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

  const loadSections = async (courseId: number) => {
    if (user?.role !== 'instructor') return;
    try {
      const response = await apiClient.getCourseSections(courseId);
      setSections((prev) => ({ ...prev, [courseId]: response.sections }));
      setSelectedSectionId((prev) => {
        const existingSelection = prev[courseId];
        const hasSelection =
          existingSelection && response.sections.some((section) => section.id === existingSelection);
        if (hasSelection) {
          return prev;
        }
        if (response.sections.length > 0) {
          return { ...prev, [courseId]: response.sections[0].id };
        }
        return { ...prev, [courseId]: null };
      });
      for (const section of response.sections) {
        await loadGroups(courseId, section.id);
      }
    } catch (error) {
      console.error('Failed to load sections:', error);
    }
  };

  const loadGroups = async (courseId: number, sectionId: number) => {
    if (user?.role !== 'instructor') return;
    try {
      const response = await apiClient.getSectionGroups(courseId, sectionId);
      setGroupsBySection((prev) => ({ ...prev, [sectionId]: response.groups }));
    } catch (error) {
      console.error('Failed to load groups:', error);
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

  const handleAddStudent = async (courseId: number) => {
    const email = newStudentEmail[courseId]?.trim();
    if (!email) {
      setStudentError({ ...studentError, [courseId]: 'Email is required' });
      return;
    }
    const sectionId = selectedSectionId[courseId];
    if (!sectionId) {
      setStudentError({ ...studentError, [courseId]: 'Please create a section first' });
      return;
    }

    setAddingStudent({ ...addingStudent, [courseId]: true });
    setStudentError({ ...studentError, [courseId]: null });
    try {
      const role = studentRole[courseId] || 'student';
      const groupId = newStudentGroupId[courseId] ?? null;
      await apiClient.addStudentToCourse(courseId, email, sectionId, groupId, role);
      setNewStudentEmail({ ...newStudentEmail, [courseId]: '' });
      setNewStudentGroupId({ ...newStudentGroupId, [courseId]: null });
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

  const handleCreateSection = async (courseId: number) => {
    const name = newSectionName[courseId]?.trim();
    if (!name) return;
    setAddingSection({ ...addingSection, [courseId]: true });
    try {
      await apiClient.createCourseSection(courseId, name);
      setNewSectionName({ ...newSectionName, [courseId]: '' });
      await loadSections(courseId);
    } catch (error: any) {
      setStudentError({ ...studentError, [courseId]: error.response?.data?.detail || 'Failed to create section' });
    } finally {
      setAddingSection({ ...addingSection, [courseId]: false });
    }
  };

  const handleCreateGroup = async (courseId: number) => {
    const sectionId = selectedSectionId[courseId];
    const name = newGroupName[courseId]?.trim();
    if (!sectionId || !name) return;
    setAddingGroup({ ...addingGroup, [courseId]: true });
    try {
      await apiClient.createSectionGroup(courseId, sectionId, name);
      setNewGroupName({ ...newGroupName, [courseId]: '' });
      await loadGroups(courseId, sectionId);
    } catch (error: any) {
      setStudentError({ ...studentError, [courseId]: error.response?.data?.detail || 'Failed to create group' });
    } finally {
      setAddingGroup({ ...addingGroup, [courseId]: false });
    }
  };

  const handleDeleteSection = async (courseId: number, sectionId: number) => {
    try {
      await apiClient.deleteCourseSection(courseId, sectionId);
      await loadSections(courseId);
    } catch (error: any) {
      alert(error.response?.data?.detail || 'Failed to delete section');
    }
  };

  const handleDeleteGroup = async (courseId: number, sectionId: number, groupId: number) => {
    try {
      await apiClient.deleteSectionGroup(courseId, sectionId, groupId);
      await loadGroups(courseId, sectionId);
    } catch (error: any) {
      alert(error.response?.data?.detail || 'Failed to delete group');
    }
  };

  const handleUpdateStudent = async (
    courseId: number,
    studentId: number,
    payload: { role?: 'student' | 'ta'; section_id?: number; group_id?: number | null }
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

  const handleExportQuestions = async (courseId: number) => {
    try {
      const blob = await apiClient.exportCourseQuestions(courseId);
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `course_${courseId}_questions.csv`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
    } catch (error: any) {
      alert(error.response?.data?.detail || 'Failed to export questions');
    }
  };

  const handleApproveUpload = async (courseId: number, requestId: number) => {
    try {
      await apiClient.approveUploadRequest(courseId, requestId);
      await loadCourse();
      await loadUploadRequests(courseId);
      await loadMyUploadRequests(courseId);
    } catch (error: any) {
      alert(error.response?.data?.detail || 'Failed to approve upload');
    }
  };

  const handleRejectUpload = async (courseId: number, requestId: number) => {
    try {
      await apiClient.rejectUploadRequest(courseId, requestId);
      await loadUploadRequests(courseId);
      await loadMyUploadRequests(courseId);
    } catch (error: any) {
      alert(error.response?.data?.detail || 'Failed to reject upload');
    }
  };

  const renderStudentManagement = (courseId: number) => {
    const students = courseStudents[courseId] || [];
    const courseSections = sections[courseId] || [];
    const selectedSection = selectedSectionId[courseId] ?? null;
    const sectionGroups = selectedSection ? groupsBySection[selectedSection] || [] : [];
    const isLoading = loadingStudents[courseId];
    const isAdding = addingStudent[courseId];
    const error = studentError[courseId];
    const email = newStudentEmail[courseId] || '';
    const role = studentRole[courseId] || 'student';
    const filteredStudents =
      selectedSection === null
        ? students
        : students.filter((student) => student.section_id === selectedSection);
    const groupCounts = sectionGroups.reduce<Record<number, number>>((acc, group) => {
      acc[group.id] = filteredStudents.filter((student) => student.group_id === group.id).length;
      return acc;
    }, {});
    const visibleGroups = sectionGroups.slice(0, 3);
    const extraGroupCount = Math.max(0, sectionGroups.length - visibleGroups.length);

    return (
      <div className="space-y-4">
        <div>
          <h4 className="text-sm font-medium text-gray-900 mb-2">Sections</h4>
          <div className="flex flex-wrap items-center gap-2">
            <button
              onClick={() => setSelectedSectionId({ ...selectedSectionId, [courseId]: null })}
              className={`px-3 py-1.5 text-sm rounded-full border ${
                selectedSection === null ? 'bg-primary-600 text-white border-primary-600' : 'bg-white text-gray-700 border-gray-200'
              }`}
            >
              All
            </button>
            {courseSections.map((section) => (
              <button
                key={section.id}
                onClick={async () => {
                  setSelectedSectionId({ ...selectedSectionId, [courseId]: section.id });
                  await loadGroups(courseId, section.id);
                }}
                className={`px-3 py-1.5 text-sm rounded-full border ${
                  selectedSection === section.id
                    ? 'bg-primary-600 text-white border-primary-600'
                    : 'bg-white text-gray-700 border-gray-200'
                }`}
              >
                {section.name}
              </button>
            ))}
            <button
              onClick={() => setShowManageSections({ ...showManageSections, [courseId]: true })}
              className="px-3 py-1.5 text-sm rounded-full border border-dashed border-gray-300 text-gray-600"
            >
              Manage Sections
            </button>
          </div>
        </div>

        {selectedSection !== null && (
          <div>
            <h4 className="text-sm font-medium text-gray-900 mb-2">Groups</h4>
            <div className="flex flex-wrap items-center gap-2">
              {visibleGroups.map((group) => (
                <span key={group.id} className="px-3 py-1.5 text-sm rounded-full border border-gray-200 text-gray-700">
                  {group.name}
                </span>
              ))}
              {extraGroupCount > 0 && (
                <span className="px-3 py-1.5 text-sm rounded-full border border-gray-200 text-gray-600">
                  +{extraGroupCount} groups
                </span>
              )}
              {sectionGroups.length > 3 && (
                <button
                  onClick={() => setShowGroupsMore({ ...showGroupsMore, [courseId]: true })}
                  className="px-3 py-1.5 text-sm rounded-full border border-dashed border-gray-300 text-gray-600"
                >
                  Show More
                </button>
              )}
              <button
                onClick={() => setShowManageGroups({ ...showManageGroups, [courseId]: true })}
                className="px-3 py-1.5 text-sm rounded-full border border-dashed border-gray-300 text-gray-600"
              >
                Manage Groups
              </button>
            </div>
          </div>
        )}

        <div>
          <h4 className="text-sm font-medium text-gray-900 mb-2">Add Student</h4>
          <div className="flex flex-col gap-2 sm:flex-row">
            <input
              type="email"
              value={email}
              onChange={(e) => setNewStudentEmail({ ...newStudentEmail, [courseId]: e.target.value })}
              placeholder="student@example.com"
              className="flex-1 px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
              onKeyPress={(e) => {
                if (e.key === 'Enter') {
                  e.preventDefault();
                  handleAddStudent(courseId);
                }
              }}
            />
            <button
              onClick={() => handleAddStudent(courseId)}
              disabled={isAdding}
              className="px-4 py-2 text-sm bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isAdding ? 'Adding...' : 'Add'}
            </button>
          </div>
          {selectedSection === null && (
            <p className="mt-1 text-xs text-gray-500">Select a section to auto-assign new students.</p>
          )}
          {error && (
            <p className="mt-1 text-xs text-red-600">{error}</p>
          )}
        </div>

        <div>
          <h4 className="text-sm font-medium text-gray-900 mb-2">
            Enrolled Students ({filteredStudents.length})
          </h4>
          <div className="flex flex-wrap gap-2 mb-3">
            <button
              onClick={() => setShowManageStudents({ ...showManageStudents, [courseId]: true })}
              className="px-3 py-1.5 text-sm rounded-full border border-gray-200 text-gray-700"
            >
              Manage Students
            </button>
            <button
              onClick={() => setShowStudentsMore({ ...showStudentsMore, [courseId]: true })}
              className="px-3 py-1.5 text-sm rounded-full border border-dashed border-gray-300 text-gray-600"
            >
              Show More
            </button>
          </div>
          {isLoading ? (
            <p className="text-xs text-gray-500">Loading...</p>
          ) : filteredStudents.length === 0 ? (
            <p className="text-xs text-gray-500">No students enrolled yet</p>
          ) : (
            <div className="space-y-2">
              {filteredStudents.map((student, index) => (
                <div
                  key={student.student_id}
                  className="w-full flex items-center justify-between px-3 py-2 bg-white border border-gray-200 rounded text-sm"
                >
                  <span className="text-gray-500 text-xs w-6">{index + 1}.</span>
                  <span className="flex-1 text-gray-800">{student.student_email}</span>
                  <span className="text-gray-500 text-xs">
                    {student.section_name || 'No section'}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>

        {showManageSections[courseId] && (
          <div className="fixed inset-0 bg-black bg-opacity-40 flex items-center justify-center z-50 p-4">
            <div className="bg-white rounded-xl shadow-xl max-w-lg w-full p-6">
              <div className="flex items-center justify-between mb-4">
                <h4 className="text-lg font-semibold text-gray-900">Manage Sections</h4>
                <button
                  onClick={() => setShowManageSections({ ...showManageSections, [courseId]: false })}
                  className="text-gray-400 hover:text-gray-600"
                >
                  ✕
                </button>
              </div>
              <div className="space-y-3">
                {courseSections.map((section) => (
                  <div key={section.id} className="flex items-center justify-between border border-gray-200 rounded-lg p-3">
                    <span className="text-sm text-gray-800">{section.name}</span>
                    <button
                      onClick={() => handleDeleteSection(courseId, section.id)}
                      className="text-xs text-red-600 hover:text-red-700"
                    >
                      Remove
                    </button>
                  </div>
                ))}
                {courseSections.length === 0 && (
                  <p className="text-sm text-gray-500">No sections yet.</p>
                )}
                <div className="border-t border-gray-200 pt-3 space-y-2">
                  <input
                    type="text"
                    value={newSectionName[courseId] || ''}
                    onChange={(e) => setNewSectionName({ ...newSectionName, [courseId]: e.target.value })}
                    placeholder="Section name (e.g. 541)"
                    className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg"
                  />
                  <button
                    onClick={() => handleCreateSection(courseId)}
                    disabled={addingSection[courseId]}
                    className="px-4 py-2 text-sm bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50"
                  >
                    {addingSection[courseId] ? 'Creating...' : 'Create Section'}
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}

        {showManageGroups[courseId] && selectedSection !== null && (
          <div className="fixed inset-0 bg-black bg-opacity-40 flex items-center justify-center z-50 p-4">
            <div className="bg-white rounded-xl shadow-xl max-w-lg w-full p-6">
              <div className="flex items-center justify-between mb-4">
                <h4 className="text-lg font-semibold text-gray-900">Manage Groups</h4>
                <button
                  onClick={() => setShowManageGroups({ ...showManageGroups, [courseId]: false })}
                  className="text-gray-400 hover:text-gray-600"
                >
                  ✕
                </button>
              </div>
              <div className="space-y-3">
                {sectionGroups.map((group) => (
                  <div key={group.id} className="flex items-center justify-between border border-gray-200 rounded-lg p-3">
                    <span className="text-sm text-gray-800">{group.name}</span>
                    <button
                      onClick={() => handleDeleteGroup(courseId, selectedSection, group.id)}
                      className="text-xs text-red-600 hover:text-red-700"
                    >
                      Remove
                    </button>
                  </div>
                ))}
                {sectionGroups.length === 0 && (
                  <p className="text-sm text-gray-500">No groups yet.</p>
                )}
                <div className="border-t border-gray-200 pt-3 space-y-2">
                  <input
                    type="text"
                    value={newGroupName[courseId] || ''}
                    onChange={(e) => setNewGroupName({ ...newGroupName, [courseId]: e.target.value })}
                    placeholder="Group name (e.g. Group A)"
                    className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg"
                  />
                  <button
                    onClick={() => handleCreateGroup(courseId)}
                    disabled={addingGroup[courseId]}
                    className="px-4 py-2 text-sm bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50"
                  >
                    {addingGroup[courseId] ? 'Creating...' : 'Create Group'}
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}

        {showGroupsMore[courseId] && selectedSection !== null && (
          <div className="fixed inset-0 bg-black bg-opacity-40 flex items-center justify-center z-50 p-4">
            <div className="bg-white rounded-xl shadow-xl max-w-3xl w-full p-6">
              <div className="flex items-center justify-between mb-4">
                <h4 className="text-lg font-semibold text-gray-900">Groups</h4>
                <button
                  onClick={() => setShowGroupsMore({ ...showGroupsMore, [courseId]: false })}
                  className="text-gray-400 hover:text-gray-600"
                >
                  ✕
                </button>
              </div>
              <div className="space-y-2">
                {sectionGroups.map((group) => (
                  <button
                    key={group.id}
                    onClick={() => setSelectedGroupDetail({ ...selectedGroupDetail, [courseId]: { id: group.id, name: group.name } })}
                    className="w-full flex items-center justify-between px-3 py-2 border border-gray-200 rounded text-sm hover:border-primary-300"
                  >
                    <span className="text-gray-800">{group.name}</span>
                    <span className="text-gray-500 text-xs">({groupCounts[group.id] || 0})</span>
                  </button>
                ))}
                {sectionGroups.length === 0 && (
                  <p className="text-sm text-gray-500">No groups yet.</p>
                )}
              </div>
            </div>
          </div>
        )}

        {selectedGroupDetail[courseId] && selectedSection !== null && (
          <div className="fixed inset-0 bg-black bg-opacity-40 flex items-center justify-center z-50 p-4">
            <div className="bg-white rounded-xl shadow-xl max-w-3xl w-full p-6">
              <div className="flex items-center justify-between mb-4">
                <h4 className="text-lg font-semibold text-gray-900">
                  {selectedGroupDetail[courseId]!.name}
                </h4>
                <button
                  onClick={() => setSelectedGroupDetail({ ...selectedGroupDetail, [courseId]: null })}
                  className="text-gray-400 hover:text-gray-600"
                >
                  ✕
                </button>
              </div>
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">#</th>
                      <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">Name</th>
                      <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">ID</th>
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                    {filteredStudents
                      .filter((student) => student.group_id === selectedGroupDetail[courseId]!.id)
                      .map((student, index) => (
                        <tr key={student.student_id}>
                          <td className="px-3 py-2 text-sm text-gray-500">{index + 1}</td>
                          <td className="px-3 py-2 text-sm text-gray-900">{student.student_email}</td>
                          <td className="px-3 py-2 text-sm text-gray-600">{student.student_id}</td>
                        </tr>
                      ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}

        {showManageStudents[courseId] && (
          <div className="fixed inset-0 bg-black bg-opacity-40 flex items-center justify-center z-50 p-4">
            <div className="bg-white rounded-xl shadow-xl max-w-4xl w-full p-6">
              <div className="flex items-center justify-between mb-4">
                <h4 className="text-lg font-semibold text-gray-900">Manage Students</h4>
                <button
                  onClick={() => setShowManageStudents({ ...showManageStudents, [courseId]: false })}
                  className="text-gray-400 hover:text-gray-600"
                >
                  ✕
                </button>
              </div>
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">#</th>
                      <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">Email</th>
                      <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">Section</th>
                      <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">Group</th>
                      <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">Role</th>
                      <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">Activity</th>
                      <th className="px-3 py-2" />
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                    {filteredStudents.map((student, index) => (
                      <tr key={student.student_id}>
                        <td className="px-3 py-2 text-sm text-gray-500">{index + 1}</td>
                        <td className="px-3 py-2 text-sm text-gray-900">{student.student_email}</td>
                        <td className="px-3 py-2">
                          <select
                            value={student.section_id ?? ''}
                            onChange={async (e) => {
                              const nextSectionId = Number(e.target.value);
                              await handleUpdateStudent(courseId, student.student_id, { section_id: nextSectionId, group_id: null });
                              await loadGroups(courseId, nextSectionId);
                              await loadCourseStudents(courseId);
                            }}
                            className="px-2 py-1 text-sm border border-gray-300 rounded"
                          >
                            {courseSections.map((section) => (
                              <option key={section.id} value={section.id}>
                                {section.name}
                              </option>
                            ))}
                          </select>
                        </td>
                        <td className="px-3 py-2">
                          <select
                            value={student.group_id ?? ''}
                            onChange={async (e) => {
                              await handleUpdateStudent(courseId, student.student_id, {
                                group_id: e.target.value ? Number(e.target.value) : null,
                              });
                              await loadCourseStudents(courseId);
                            }}
                            className="px-2 py-1 text-sm border border-gray-300 rounded"
                          >
                            <option value="">None</option>
                            {(groupsBySection[student.section_id || 0] || []).map((group) => (
                              <option key={group.id} value={group.id}>
                                {group.name}
                              </option>
                            ))}
                          </select>
                        </td>
                        <td className="px-3 py-2">
                          <select
                            value={student.role}
                            onChange={async (e) => {
                              await handleUpdateStudent(courseId, student.student_id, { role: e.target.value as 'student' | 'ta' });
                              await loadCourseStudents(courseId);
                            }}
                            className="px-2 py-1 text-sm border border-gray-300 rounded"
                          >
                            <option value="student">Student</option>
                            <option value="ta">TA</option>
                          </select>
                        </td>
                        <td className="px-3 py-2 text-sm text-gray-600">
                          {student.questions_count} q{student.questions_count === 1 ? '' : 's'}
                          {student.last_active && (
                            <span className="block text-xs text-gray-400">
                              {new Date(student.last_active).toLocaleDateString()}
                            </span>
                          )}
                        </td>
                        <td className="px-3 py-2 text-right">
                          <button
                            onClick={() => handleRemoveStudent(courseId, student.student_id)}
                            className="text-red-600 hover:text-red-700 text-xs font-medium"
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
          <div className="fixed inset-0 bg-black bg-opacity-40 flex items-center justify-center z-50 p-4">
            <div className="bg-white rounded-xl shadow-xl max-w-5xl w-full p-6">
              <div className="flex items-center justify-between mb-4">
                <h4 className="text-lg font-semibold text-gray-900">Student Details</h4>
                <button
                  onClick={() => setShowStudentsMore({ ...showStudentsMore, [courseId]: false })}
                  className="text-gray-400 hover:text-gray-600"
                >
                  ✕
                </button>
              </div>
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">#</th>
                      <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">Email</th>
                      <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">Section</th>
                      <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">Group</th>
                      <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">Role</th>
                      <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">Activity</th>
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                    {filteredStudents.map((student, index) => (
                      <tr key={student.student_id}>
                        <td className="px-3 py-2 text-sm text-gray-500">{index + 1}</td>
                        <td className="px-3 py-2 text-sm text-gray-900">{student.student_email}</td>
                        <td className="px-3 py-2 text-sm text-gray-700">{student.section_name || 'No section'}</td>
                        <td className="px-3 py-2 text-sm text-gray-700">{student.group_name || 'None'}</td>
                        <td className="px-3 py-2 text-sm text-gray-700">{student.role}</td>
                        <td className="px-3 py-2 text-sm text-gray-600">
                          {student.questions_count} q{student.questions_count === 1 ? '' : 's'}
                          {student.last_active && (
                            <span className="block text-xs text-gray-400">
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
        <p className="text-sm font-semibold text-gray-900 mb-2">Sources</p>
        <div className="space-y-1">
          {sources.map((source, index) => (
            <div key={`${source.lecture_id}-${index}`} className="text-sm text-gray-600">
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
                <h1 className="text-xl font-semibold text-gray-900">{course.name}</h1>
                {course.description && (
                  <p className="text-sm text-gray-500">{course.description}</p>
                )}
                <p className="text-xs text-gray-400 mt-1">{course.lecture_count} lectures</p>
              </div>
            </div>
            <div className="flex items-center space-x-4">
              {user?.role === 'instructor' && (
                <Link
                  href="/instructor"
                  className="text-sm text-gray-700 hover:text-gray-900"
                >
                  Analytics
                </Link>
              )}
              {user?.role === 'student' && (
                <button
                  onClick={handleLeaveCourse}
                  className="text-sm text-red-600 hover:text-red-700"
                >
                  Leave course
                </button>
              )}
              <button
                onClick={() => {
                  apiClient.logout();
                  router.push('/auth/login');
                }}
                className="text-sm text-gray-700 hover:text-gray-900"
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
        {/* Zone 1: Instructor overview */}
        {user?.role === 'instructor' && (
          <div className="bg-gray-50 border border-gray-200 rounded-2xl p-6 space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-2xl font-semibold text-gray-900">{course.name}</h2>
                {course.description && (
                  <p className="text-sm text-gray-600 mt-1">{course.description}</p>
                )}
              </div>
              <span className="px-3 py-1 text-xs font-medium rounded-full bg-green-50 text-green-700 border border-green-100">
                Active
              </span>
            </div>
            <CourseAnalyticsOverview courseId={course.id} />
          </div>
        )}

        {/* Zone 2: Course management */}
        <div>
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Course Management</h3>
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
            {/* Left Sidebar - Lectures */}
            <div className="space-y-6">
              <div className={`rounded-xl shadow-sm border ${collapseLectures[course.id] ? 'bg-gray-50 border-gray-200' : 'bg-white border-gray-200'}`}>
                <button
                  onClick={() =>
                    setCollapseLectures({ ...collapseLectures, [course.id]: !collapseLectures[course.id] })
                  }
                  className="w-full px-6 py-4 flex items-center justify-between text-left"
                >
                  <div className="flex items-center gap-3">
                    <h3 className="text-base font-semibold text-gray-900">Lectures</h3>
                    {refreshing && (
                      <div className="flex items-center space-x-2 text-sm text-gray-500">
                        <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                        </svg>
                      </div>
                    )}
                  </div>
                  <span className="text-sm text-gray-600">
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
                        <h4 className="text-sm font-semibold text-gray-900 mb-2">Instructor uploaded materials</h4>
                        {instructorLectures.length === 0 ? (
                          <p className="text-sm text-gray-500">No instructor uploads yet.</p>
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
                            className="mt-3 text-sm text-gray-600 hover:text-gray-800"
                          >
                            {showAllInstructor
                              ? 'Show less'
                              : `Show more (+${instructorLectures.length - visibleInstructorLectures.length})`}
                          </button>
                        )}
                      </div>

                      <div className="pt-4 border-t border-gray-200">
                        <h4 className="text-sm font-semibold text-gray-900 mb-2">Student uploaded materials</h4>
                        {studentLectures.length === 0 ? (
                          <p className="text-sm text-gray-500">No student uploads yet.</p>
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
                            className="mt-3 text-sm text-gray-600 hover:text-gray-800"
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
            </div>

            {user?.role === 'instructor' && (
              <div className={`rounded-xl shadow-sm border ${collapseManageStudents[course.id] ? 'bg-gray-50 border-gray-200' : 'bg-white border-gray-200'}`}>
                <button
                  onClick={async () => {
                    const nextCollapsed = !collapseManageStudents[course.id];
                    setCollapseManageStudents({ ...collapseManageStudents, [course.id]: nextCollapsed });
                    if (!nextCollapsed) {
                      await loadCourseStudents(course.id);
                      await loadSections(course.id);
                      await loadAnnouncements(course.id);
                      await loadUploadRequests(course.id);
                      const sectionId = selectedSectionId[course.id];
                      if (sectionId) {
                        await loadGroups(course.id, sectionId);
                      }
                    }
                  }}
                  className="w-full px-6 py-4 flex items-center justify-between text-left"
                >
                  <span className="text-base font-semibold text-gray-900">Manage Students</span>
                  <span className="text-sm text-gray-600">
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

            {(user?.role === 'instructor' || canReviewUploads[course.id]) && (
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
                  <h3 className="text-base font-semibold text-gray-900">Upload Requests</h3>
                  <span className="text-sm text-gray-600">
                    {collapseUploadRequests[course.id] ? '+' : '−'}
                  </span>
                </button>
                {!collapseUploadRequests[course.id] && (
                  <div className="px-6 pb-6">
                    <div className="flex items-center justify-between mb-4">
                      <div />
                      <button
                        onClick={() => loadUploadRequests(course.id)}
                        className="text-sm text-gray-500 hover:text-gray-700"
                      >
                        Refresh
                      </button>
                    </div>
                    {loadingUploadRequests[course.id] ? (
                      <p className="text-sm text-gray-500">Loading requests...</p>
                    ) : (uploadRequests[course.id] || []).length === 0 ? (
                      <p className="text-sm text-gray-500">
                        No upload requests yet. Student submissions will appear here.
                      </p>
                    ) : (
                      <div className="space-y-3">
                        {(uploadRequests[course.id] || []).map((request) => (
                          <div key={request.id} className="border border-gray-200 rounded-lg p-3">
                            <div className="flex items-start justify-between gap-3">
                              <div className="min-w-0">
                                <p className="text-sm font-medium text-gray-900 truncate" title={request.original_name}>
                                  {request.original_name}
                                </p>
                                <p className="text-xs text-gray-500 truncate" title={request.student_email || 'Student'}>
                                  {request.student_email || 'Student'} • {request.file_type}
                                </p>
                              </div>
                              <div className="flex items-center gap-2">
                                <button
                                  onClick={() => handleApproveUpload(course.id, request.id)}
                                  className="px-3 py-1 text-xs bg-green-600 text-white rounded hover:bg-green-700"
                                >
                                  Approve
                                </button>
                                <button
                                  onClick={() => handleRejectUpload(course.id, request.id)}
                                  className="px-3 py-1 text-xs bg-red-600 text-white rounded hover:bg-red-700"
                                >
                                  Reject
                                </button>
                              </div>
                            </div>
                            {request.created_at && (
                              <p className="text-xs text-gray-400 mt-2">
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

            {user?.role === 'student' && (
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
                  <h3 className="text-base font-semibold text-gray-900">My Upload Requests</h3>
                  <span className="text-sm text-gray-600">
                    {collapseUploadRequests[course.id] ? '+' : '−'}
                  </span>
                </button>
                {!collapseUploadRequests[course.id] && (
                  <div className="px-6 pb-6">
                    <div className="flex items-center justify-between mb-4">
                      <div />
                      <button
                        onClick={() => loadMyUploadRequests(course.id)}
                        className="text-sm text-gray-500 hover:text-gray-700"
                      >
                        Refresh
                      </button>
                    </div>
                    {loadingMyUploadRequests[course.id] ? (
                      <p className="text-sm text-gray-500">Loading requests...</p>
                    ) : (myUploadRequests[course.id] || []).length === 0 ? (
                      <p className="text-sm text-gray-500">
                        No upload requests yet. Submitted files will show here.
                      </p>
                    ) : (
                      <div className="space-y-3">
                        {(myUploadRequests[course.id] || []).map((request) => (
                          <div key={request.id} className="border border-gray-200 rounded-lg p-3">
                            <div className="flex items-start justify-between gap-3">
                              <div className="min-w-0">
                                <p className="text-sm font-medium text-gray-900 truncate" title={request.original_name}>
                                  {request.original_name}
                                </p>
                                <p className="text-xs text-gray-500 truncate">{request.file_type}</p>
                              </div>
                              <span
                                className={`text-xs px-2 py-0.5 rounded-full ${
                                  request.status === 'pending'
                                    ? 'bg-yellow-50 text-yellow-700 border border-yellow-200'
                                    : request.status === 'approved'
                                    ? 'bg-green-50 text-green-700 border border-green-200'
                                    : 'bg-red-50 text-red-700 border border-red-200'
                                }`}
                              >
                                {request.status}
                              </span>
                            </div>
                            {request.created_at && (
                              <p className="text-xs text-gray-400 mt-2">
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

            
          </div>

          {/* Main Content - Chat or Analytics */}
          <div className="lg:col-span-2 space-y-8">
            {user?.role === 'instructor' ? (
              <div className="text-sm text-gray-500">
                Analytics summary shown above.
              </div>
            ) : (
              <div className="space-y-6">
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
                      <h3 className="text-base font-semibold text-gray-900">Announcements</h3>
                    </div>
                    <span className="text-sm text-gray-600">
                      {collapseStudentAnnouncements[course.id] ? '+' : '−'}
                    </span>
                  </button>
                  {!collapseStudentAnnouncements[course.id] && (
                    <div className="px-6 pb-6">
                      {(announcements[course.id] || []).length === 0 ? (
                        <p className="text-sm text-gray-500">No announcements yet.</p>
                      ) : (
                        <div className="space-y-2">
                          {(announcements[course.id] || []).map((item) => (
                            <div key={item.id} className="border border-gray-200 rounded-lg p-3">
                              <p className="text-sm text-gray-800 whitespace-pre-wrap">{item.message}</p>
                              {item.created_at && (
                                <p className="text-xs text-gray-400 mt-2">
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
                    <h3 className="text-base font-semibold text-gray-900">Ask Questions</h3>
                    <span className="text-sm text-gray-600">
                      {collapseAskQuestions[course.id] ? '+' : '−'}
                    </span>
                  </button>
                  {!collapseAskQuestions[course.id] && (
                    <div className="px-6 pb-6">
                      <form onSubmit={handleCourseQuery} className="space-y-4">
                        <div>
                          <textarea
                            value={courseQuestion}
                            onChange={(e) => setCourseQuestion(e.target.value)}
                            placeholder="Ask a question about the course content..."
                            rows={4}
                            className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent resize-none"
                            disabled={courseAsking || course.lecture_count === 0}
                          />
                          {course.lecture_count === 0 && (
                            <p className="mt-2 text-sm text-gray-500">
                              Upload at least one lecture to ask questions.
                            </p>
                          )}
                        </div>
                        {queryError && (
                          <div className="text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg p-2">
                            {queryError}
                          </div>
                        )}
                        <button
                          type="submit"
                          disabled={courseAsking || !courseQuestion.trim() || course.lecture_count === 0}
                          className="w-full px-4 py-2 bg-primary-600 text-white rounded-lg font-medium hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                        >
                          {courseAsking ? 'Asking...' : 'Ask Question'}
                        </button>
                      </form>

                      {courseAnswer && (
                        <div className="mt-6 pt-6 border-t border-gray-200">
                          <div className="prose max-w-none">
                            <p className="text-gray-800 whitespace-pre-wrap">{courseAnswer.answer}</p>
                            {renderSources(courseAnswer.sources)}
                          </div>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Zone 3: Communication & exports */}
        {user?.role === 'instructor' && (
          <div>
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Communication & Data</h3>
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
                <h4 className="text-base font-semibold text-gray-900">Announcements</h4>
                <span className="text-sm text-gray-600">
                  {collapseInstructorAnnouncements[course.id] ? '+' : '−'}
                </span>
              </button>
              {!collapseInstructorAnnouncements[course.id] && (
                <div className="px-6 pb-6">
                  <div className="flex items-center justify-between mb-2">
                    <div />
                    <button
                      onClick={() => handleExportQuestions(course.id)}
                      className="text-sm text-gray-500 hover:text-gray-700"
                    >
                      Export Questions CSV
                    </button>
                  </div>
                  <p className="text-sm text-gray-500 mb-3">
                    Use announcements to clarify confusing topics or post updates.
                  </p>
                  <div className="space-y-3">
                    <textarea
                      value={newAnnouncement[course.id] || ''}
                      onChange={(e) => setNewAnnouncement({ ...newAnnouncement, [course.id]: e.target.value })}
                      placeholder="Post an announcement to this course..."
                      rows={3}
                      className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent resize-none"
                    />
                    <div className="flex items-center justify-between">
                      {announcementError[course.id] && (
                        <p className="text-xs text-red-600">{announcementError[course.id]}</p>
                      )}
                      <button
                        onClick={() => handlePostAnnouncement(course.id)}
                        disabled={postingAnnouncement[course.id]}
                        className="ml-auto px-4 py-2 text-sm bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50"
                      >
                        {postingAnnouncement[course.id] ? 'Posting...' : 'Post'}
                      </button>
                    </div>
                    <div className="space-y-2">
                      {(announcements[course.id] || []).length === 0 ? (
                        <p className="text-sm text-gray-500">No announcements yet.</p>
                      ) : (
                        (announcements[course.id] || []).map((item) => (
                          <div key={item.id} className="border border-gray-200 rounded-lg p-3">
                            <p className="text-sm text-gray-800 whitespace-pre-wrap">{item.message}</p>
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
          </div>
        )}
      </main>
    </div>
  );
}

