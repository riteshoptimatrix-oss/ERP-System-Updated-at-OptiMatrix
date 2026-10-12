'use client';

import React, { createContext, useContext, useState, useEffect, useCallback, ReactNode } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import { User, ManufacturingUnit, RoleName } from '@/types/auth';
import { apiClient } from '@/services/api-client';

interface AuthContextType {
  user: User | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  isReadOnlyOwner: boolean;
  activeUnit: ManufacturingUnit;
  setActiveUnit: (unit: ManufacturingUnit) => void;
  login: (email: string, password: string) => Promise<{ success: boolean; error?: string }>;
  logout: () => Promise<void>;
  changePassword: (current_password: string, new_password: string, confirm_password: string) => Promise<{ success: boolean; error?: string }>;
  hasPermission: (module: string, action: string) => boolean;
  hasRole: (roles: RoleName | RoleName[]) => boolean;
  canAccessUnit: (unit: ManufacturingUnit) => boolean;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [activeUnit, setActiveUnitState] = useState<ManufacturingUnit>('Unit_1');
  const router = useRouter();
  const pathname = usePathname();

  const fetchCurrentUser = useCallback(async () => {
    setIsLoading(true);
    try {
      const res = await apiClient.get<User>('/api/v1/auth/me');
      if (res.data) {
        setUser(res.data);
        // Default active unit based on account type and permissions: HR is enterprise-wide
        if (res.data.role === 'HR' || res.data.account_type === 'HR') {
          setActiveUnitState('BOTH');
        } else if (res.data.allowed_units.includes('Unit_2') && !res.data.allowed_units.includes('Unit_1')) {
          setActiveUnitState('Unit_2');
        } else {
          setActiveUnitState('Unit_1');
        }
      } else {
        setUser(null);
      }
    } catch {
      setUser(null);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    let isMounted = true;

    const loadUser = async () => {
      try {
        const res = await apiClient.get<User>('/api/v1/auth/me');
        if (!isMounted) return;

        if (res.data) {
          setUser(res.data);
          if (res.data.role === 'HR' || res.data.account_type === 'HR') {
            setActiveUnitState('BOTH');
          } else if (res.data.allowed_units.includes('Unit_2') && !res.data.allowed_units.includes('Unit_1')) {
            setActiveUnitState('Unit_2');
          } else {
            setActiveUnitState('Unit_1');
          }
        } else {
          setUser(null);
        }
      } catch {
        if (isMounted) {
          setUser(null);
        }
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    };

    loadUser();

    return () => {
      isMounted = false;
    };
  }, []);

  // Route protection effect
  useEffect(() => {
    if (!isLoading) {
      const publicRoutes = ['/login'];
      const isPublic = publicRoutes.includes(pathname);

      if (!user && !isPublic) {
        router.push(`/login?redirect=${encodeURIComponent(pathname)}`);
      } else if (user) {
        if (user.must_change_password) {
          if (pathname !== '/change-password') {
            router.push('/change-password');
          }
        } else if (isPublic || pathname === '/change-password') {
          router.push('/');
        }
      }
    }
  }, [user, isLoading, pathname, router]);

  const login = async (email: string, password: string): Promise<{ success: boolean; error?: string }> => {
    setIsLoading(true);
    try {
      const res = await apiClient.post<{ user: User; csrf_token: string }>(
        '/api/v1/auth/login',
        { email, password }
      );

      if (res.data?.user) {
        setUser(res.data.user);
        if (res.data.user.allowed_units.includes('Unit_2') && !res.data.user.allowed_units.includes('Unit_1')) {
          setActiveUnitState('Unit_2');
        } else {
          setActiveUnitState('Unit_1');
        }
        setIsLoading(false);

        if (res.data.user.must_change_password) {
          router.push('/change-password');
          return { success: true };
        }

        const searchParams = typeof window !== 'undefined' ? new URLSearchParams(window.location.search) : null;
        const redirectPath = searchParams?.get('redirect');
        router.push(redirectPath && redirectPath.startsWith('/') ? redirectPath : '/');
        return { success: true };
      } else {
        setIsLoading(false);
        return {
          success: false,
          error: res.error?.message || 'Authentication failed. Please check your credentials.'
        };
      }
    } catch (err: unknown) {
      setIsLoading(false);
      const msg = err instanceof Error ? err.message : 'Login network failure';
      return { success: false, error: msg };
    }
  };

  const changePassword = async (
    current_password: string,
    new_password: string,
    confirm_password: string
  ): Promise<{ success: boolean; error?: string }> => {
    setIsLoading(true);
    try {
      const res = await apiClient.post<{ message: string; user?: User; csrf_token?: string }>(
        '/api/v1/auth/change-password',
        { current_password, new_password, confirm_password }
      );

      if (res.status === 200) {
        await fetchCurrentUser();
        setIsLoading(false);
        router.push('/');
        return { success: true };
      } else {
        setIsLoading(false);
        return {
          success: false,
          error: res.error?.message || 'Failed to change password. Please check your inputs.',
        };
      }
    } catch (err: unknown) {
      setIsLoading(false);
      const msg = err instanceof Error ? err.message : 'Network failure during password change.';
      return { success: false, error: msg };
    }
  };

  const logout = async () => {
    try {
      await apiClient.post('/api/v1/auth/logout', {});
    } finally {
      setUser(null);
      router.push('/login');
    }
  };

  const isReadOnlyOwner = user?.role === 'SUPER_ADMIN';

  const hasPermission = (module: string, action: string): boolean => {
    if (!user) return false;
    // Super Admin (Owner) executive monitoring policy:
    // Only 'read' and 'export' are permitted. All business mutations, approvals, and write operations are strictly prohibited.
    if (user.role === 'SUPER_ADMIN') {
      return action === 'read' || action === 'export';
    }
    const required = `${module}:${action}`;
    return user.permissions.includes(required);
  };

  const hasRole = (roles: RoleName | RoleName[]): boolean => {
    if (!user) return false;
    const roleList = Array.isArray(roles) ? roles : [roles];
    return roleList.includes(user.role);
  };

  const canAccessUnit = (unit: ManufacturingUnit): boolean => {
    if (!user) return false;
    if (user.role === 'SUPER_ADMIN') return true;
    if (user.allowed_units.includes('BOTH')) return true;
    return user.allowed_units.includes(unit);
  };

  const setActiveUnit = (unit: ManufacturingUnit) => {
    if (canAccessUnit(unit)) {
      setActiveUnitState(unit);
    }
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        isLoading,
        isAuthenticated: !!user,
        isReadOnlyOwner,
        activeUnit,
        setActiveUnit,
        login,
        logout,
        changePassword,
        hasPermission,
        hasRole,
        canAccessUnit,
        refreshUser: fetchCurrentUser,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
