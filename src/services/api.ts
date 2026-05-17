/**
 * API service — all calls go to /api/v1/*
 * In Docker Compose the nginx proxy forwards /api/* to the FastAPI backend.
 * In development, configure VITE_API_BASE in .env.local to point at localhost:8000.
 */

const BASE = (import.meta as unknown as { env: Record<string, string> }).env?.VITE_API_BASE ?? '';

async function request<T>(path: string, options?: RequestInit): Promise<T> {
    const res = await fetch(`${BASE}${path}`, options);
    if (!res.ok) {
        let detail = `HTTP ${res.status}`;
        try {
            const body = await res.json();
            detail = body.detail ?? JSON.stringify(body);
        } catch {
            detail = await res.text();
        }
        throw new Error(detail);
    }
    return res.json() as Promise<T>;
}

// ---- Types ----------------------------------------------------------------

export interface OverviewStats {
    total_calls_today: number;
    total_calls_week: number;
    total_calls_month: number;
    top_agent_today: { name: string; count: number } | null;
    active_agents_today: number;
}

export interface HourlyBucket {
    hour: number;
    calls: number;
}

export interface LeaderboardEntry {
    rank: number;
    agent_ext: string;
    agent_name: string;
    total_calls: number;
    answered_calls: number;
    missed_calls: number;
    total_talk_mins: number;
    avg_talk_mins: number;
    answer_rate_pct: number;
}

export interface ImportLog {
    id: number;
    filename: string | null;
    pbx_source: string | null;
    rows_imported: number;
    rows_skipped: number;
    status: string | null;
    error_message: string | null;
    processed_at: string | null;
}

export interface UploadResult {
    pbx_detected: string;
    rows_imported: number;
    rows_skipped: number;
    filename: string;
}

// ---- API calls ------------------------------------------------------------

export const api = {
    health: () => request<{ status: string }>('/api/v1/health'),

    overview: () => request<OverviewStats>('/api/v1/stats/overview'),

    hourly: () => request<HourlyBucket[]>('/api/v1/stats/hourly'),

    leaderboard: (period: 'daily' | 'weekly' | 'monthly') =>
        request<LeaderboardEntry[]>(`/api/v1/leaderboard/${period}`),

    imports: () => request<ImportLog[]>('/api/v1/imports'),

    upload: (file: File) => {
        const form = new FormData();
        form.append('file', file);
        return request<UploadResult>('/api/v1/upload', { method: 'POST', body: form });
    },
};
