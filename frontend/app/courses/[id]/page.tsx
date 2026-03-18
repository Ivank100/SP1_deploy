'use client';

/**
 * This file is the Next.js route entry for the courses/[id] page.
 * It connects route parameters and page-level wiring to the matching view logic.
 */
import { useParams, useRouter } from 'next/navigation';
import CourseDetailPageView from '@/components/pages/courses/CourseDetailPageView';
import { useCourseDetailPage } from '@/hooks/useCourseDetailPage';

export default function CourseDetailPage() {
  const router = useRouter();
  const params = useParams();
  const courseId = parseInt(params.id as string, 10);
  const page = useCourseDetailPage(courseId, router);

  return <CourseDetailPageView page={page} />;
}
