'use client';

import { useState } from 'react';
import { apiClient } from '@/lib/api';

type RouterLike = {
  push: (href: string) => void;
};

export function useRegisterPage(router: RouterLike) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [role, setRole] = useState<'student' | 'instructor'>('student');
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    setError(null);

    if (password !== confirmPassword) {
      setError('Passwords do not match');
      return;
    }

    setLoading(true);

    try {
      await apiClient.register(email, password, role);
      router.push('/');
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Registration failed. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return {
    confirmPassword,
    email,
    error,
    handleSubmit,
    loading,
    password,
    role,
    setConfirmPassword,
    setEmail,
    setPassword,
    setRole,
  };
}
