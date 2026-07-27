'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuthStore } from '@/stores/authStore';

export function useAuth() {
  const router = useRouter();
  const { user, isAuthenticated, isLoading, login, register, logout, fetchUser, error, clearError } =
    useAuthStore();

  useEffect(() => {
    fetchUser();
  }, [fetchUser]);

  const requireAuth = () => {
    if (!isLoading && !isAuthenticated) {
      router.push('/login');
    }
  };

  return {
    user,
    isAuthenticated,
    isLoading,
    login,
    register,
    logout,
    requireAuth,
    error,
    clearError,
  };
}
