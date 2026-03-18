'use client';

import { useRouter } from 'next/navigation';
import InstructorDashboardPageView from '@/components/pages/instructor/InstructorDashboardPageView';
import { useInstructorDashboardPage } from '@/hooks/useInstructorDashboardPage';

export default function InstructorDashboard() {
  const router = useRouter();
  const page = useInstructorDashboardPage(router);

  return <InstructorDashboardPageView page={page} />;
}
