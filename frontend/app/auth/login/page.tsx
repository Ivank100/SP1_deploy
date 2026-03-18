'use client';

import { useRouter } from 'next/navigation';
import LoginPageView from '@/components/pages/auth/LoginPageView';
import { useLoginPage } from '@/hooks/useLoginPage';

export default function LoginPage() {
  const router = useRouter();
  const page = useLoginPage(router);

  return <LoginPageView page={page} />;
}
