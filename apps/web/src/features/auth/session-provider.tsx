"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { usePathname } from "next/navigation";
import { createContext, useCallback, useContext, useEffect, useMemo, type ReactNode } from "react";

import {
  ApiRequestError,
  getMe,
  refreshSession,
  signOut as signOutRequest,
  type Account,
} from "@/features/auth/api";

const ACCOUNT_QUERY = ["account", "me"] as const;

type SessionStatus = "loading" | "anonymous" | "authenticated";

interface SessionValue {
  status: SessionStatus;
  account: Account | null;
  /** True while a fresh account read is in flight. Roles can change after an approval. */
  refreshing: boolean;
  refreshAccount: () => Promise<void>;
  signOut: () => Promise<void>;
}

const SessionContext = createContext<SessionValue | null>(null);

async function loadAccount(): Promise<Account | null> {
  try {
    return await getMe();
  } catch (error) {
    const status = error instanceof ApiRequestError ? error.problem.status : 0;
    if (status !== 401) throw error;
  }
  const session = await refreshSession();
  if (!session) return null;
  return getMe();
}

export function SessionProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient();
  const pathname = usePathname();
  const query = useQuery({
    queryKey: ACCOUNT_QUERY,
    queryFn: loadAccount,
    retry: false,
    staleTime: 60_000,
  });

  useEffect(() => {
    void queryClient.invalidateQueries({ queryKey: ACCOUNT_QUERY });
  }, [pathname, queryClient]);

  const refreshAccount = useCallback(async () => {
    await queryClient.invalidateQueries({ queryKey: ACCOUNT_QUERY });
  }, [queryClient]);

  const signOut = useCallback(async () => {
    await signOutRequest();
    queryClient.setQueryData(ACCOUNT_QUERY, null);
  }, [queryClient]);

  const value = useMemo<SessionValue>(() => {
    const account = query.data ?? null;
    const status: SessionStatus = query.isPending
      ? "loading"
      : account
        ? "authenticated"
        : "anonymous";
    return { status, account, refreshing: query.isFetching, refreshAccount, signOut };
  }, [query.data, query.isFetching, query.isPending, refreshAccount, signOut]);

  return <SessionContext.Provider value={value}>{children}</SessionContext.Provider>;
}

export function useSession(): SessionValue {
  const value = useContext(SessionContext);
  if (!value) {
    throw new Error("useSession must be used inside SessionProvider");
  }
  return value;
}
