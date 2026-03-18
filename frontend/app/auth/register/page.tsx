'use client';

import { useRouter } from 'next/navigation';
import RegisterPageView from '@/components/pages/auth/RegisterPageView';
import { useRegisterPage } from '@/hooks/useRegisterPage';

export default function RegisterPage() {
  const router = useRouter();
  const page = useRegisterPage(router);

  return <RegisterPageView page={page} />;
}
