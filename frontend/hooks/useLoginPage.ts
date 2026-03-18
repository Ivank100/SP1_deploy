'use client';

import { useState } from 'react';
import { apiClient } from '@/lib/api';

type RouterLike = {
  push: (href: string) => void;
};

export function useLoginPage(router: RouterLike) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    setError(null);
    setLoading(true);

    try {
      await apiClient.login(email, password);
      router.push('/');
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Login failed. Please check your credentials.');
    } finally {
      setLoading(false);
    }
  };

  return {
    email,
    error,
    handleSubmit,
    loading,
    password,
    setEmail,
    setPassword,
  };
}
