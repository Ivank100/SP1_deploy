'use client';

import Link from 'next/link';
import { Lecture, User } from '@/lib/api';

type LecturePageHeaderProps = {
  courseName: string | null;
  currentUser: User | null;
  lecture: Lecture;
  onLogout: () => void;
};

export default function LecturePageHeader({
  courseName,
  currentUser,
  lecture,
  onLogout,
}: LecturePageHeaderProps) {
  return (
    <>
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
    </>
  );
}
