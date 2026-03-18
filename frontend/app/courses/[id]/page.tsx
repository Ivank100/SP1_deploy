'use client';

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
