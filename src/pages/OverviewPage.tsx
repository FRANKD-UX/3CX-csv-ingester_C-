import React, { useEffect, useState, useCallback } from 'react';
import { RiPhoneLine, RiCalendarLine, RiCalendar2Line, RiUserStarLine, RiRefreshLine, RiTeamLine } from 'react-icons/ri';
import {
    BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from 'recharts';
import { api, OverviewStats, HourlyBucket, LeaderboardEntry } from '@/services/api';

// --- Stat card ---------------------------------------------------------------

interface StatCardProps {
    icon: React.ReactNode;
    label: string;
    value: string | number;
    sub?: string;
    accent?: boolean;
}

const StatCard: React.FC<StatCardProps> = ({ icon, label, value, sub, accent }) => (
    <div className="bg-card rounded-lg border border-border shadow-card p-5 flex flex-col gap-3 h-full">
        <div className="flex items-center gap-2">
            <span className={accent ? 'text-primary' : 'text-muted-foreground'}>{icon}</span>
            <span className="text-xs font-medium text-muted-foreground uppercase tracking-wide">{label}</span>
        </div>
        <div className="min-w-0">
            <p className="text-3xl font-bold text-foreground tabular-nums truncate">{value}</p>
            {sub && <p className="text-sm text-muted-foreground mt-1 truncate text-pretty">{sub}</p>}
        </div>
    </div>
);

// --- Custom tooltip ----------------------------------------------------------

const HourlyTooltip: React.FC<{ active?: boolean; payload?: { value: number }[]; label?: number }> = ({ active, payload, label }) => {
    if (!active || !payload?.length) return null;
    const h = label ?? 0;
    const ampm = h < 12 ? 'AM' : 'PM';
    const display = h === 0 ? '12 AM' : h <= 12 ? `${h} ${ampm}` : `${h - 12} PM`;
    return (
        <div className="bg-card border border-border rounded-md px-3 py-2 shadow-md text-sm">
            <p className="font-medium text-foreground">{display}</p>
            <p className="text-muted-foreground">{payload[0].value} calls</p>
        </div>
    );
};

// --- Page -------------------------------------------------------------------

const OverviewPage: React.FC = () => {
    const [stats, setStats] = useState<OverviewStats | null>(null);
    const [hourly, setHourly] = useState<HourlyBucket[]>([]);
    const [top5, setTop5] = useState<LeaderboardEntry[]>([]);
    const [lastUpdated, setLastUpdated] = useState<Date>(new Date());
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    const fetchAll = useCallback(async () => {
        try {
            const [s, h, lb] = await Promise.all([
                api.overview(),
                api.hourly(),
                api.leaderboard('daily'),
            ]);
            setStats(s);
            setHourly(h);
            setTop5(lb.slice(0, 5));
            setLastUpdated(new Date());
            setError(null);
        } catch (e) {
            setError((e as Error).message);
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        fetchAll();
        const id = setInterval(fetchAll, 30_000);
        return () => clearInterval(id);
    }, [fetchAll]);

    const hourlyData = hourly.map((b) => ({
        hour: b.hour,
        calls: b.calls,
    }));

    const tickFormatter = (h: number) => {
        if (h % 6 !== 0) return '';
        if (h === 0) return '12a';
        if (h === 12) return '12p';
        return h < 12 ? `${h}a` : `${h - 12}p`;
    };

    return (
        <div className="space-y-6">
            {/* Page header */}
            <div className="flex items-center justify-between gap-4">
                <div>
                    <h1 className="text-xl font-bold text-foreground text-balance">Overview</h1>
                    <p className="text-sm text-muted-foreground mt-0.5">
                        Today's call activity at a glance
                    </p>
                </div>
                <div className="flex items-center gap-2 text-xs text-muted-foreground shrink-0">
                    <RiRefreshLine size={14} className={loading ? 'animate-spin text-primary' : ''} />
                    <span>Updated {lastUpdated.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}</span>
                </div>
            </div>

            {error && (
                <div className="rounded-lg border border-destructive/30 bg-destructive/10 px-4 py-3 text-sm text-destructive">
                    Backend unavailable: {error}. Cards will update when the API is reachable.
                </div>
            )}

            {/* Summary cards */}
            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4">
                <StatCard
                    icon={<RiPhoneLine size={18} />}
                    label="Calls Today"
                    value={loading ? '—' : (stats?.total_calls_today ?? 0)}
                    accent
                />
                <StatCard
                    icon={<RiCalendarLine size={18} />}
                    label="Calls This Week"
                    value={loading ? '—' : (stats?.total_calls_week ?? 0)}
                />
                <StatCard
                    icon={<RiCalendar2Line size={18} />}
                    label="Calls This Month"
                    value={loading ? '—' : (stats?.total_calls_month ?? 0)}
                />
                <StatCard
                    icon={<RiUserStarLine size={18} />}
                    label="Top Agent Today"
                    value={loading ? '—' : (stats?.top_agent_today?.name ?? '—')}
                    sub={stats?.top_agent_today ? `${stats.top_agent_today.count} answered calls` : 'No data yet'}
                    accent
                />
            </div>

            {/* Active agents badge */}
            {!loading && stats && (
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                    <RiTeamLine size={16} />
                    <span>
            <span className="font-semibold text-foreground">{stats.active_agents_today}</span> active agent{stats.active_agents_today !== 1 ? 's' : ''} today
          </span>
                </div>
            )}

            {/* Charts + table row */}
            <div className="grid grid-cols-1 xl:grid-cols-3 gap-4">
                {/* Bar chart */}
                <div className="xl:col-span-2 bg-card rounded-lg border border-border shadow-card p-5">
                    <h2 className="text-sm font-semibold text-foreground mb-4">Calls Per Hour — Today</h2>
                    <div className="w-full min-w-0 overflow-hidden" style={{ height: 220 }}>
                        <ResponsiveContainer width="100%" height="100%">
                            <BarChart data={hourlyData} margin={{ top: 4, right: 4, left: -16, bottom: 0 }}>
                                <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                                <XAxis
                                    dataKey="hour"
                                    tickFormatter={tickFormatter}
                                    tick={{ fontSize: 11, fill: 'hsl(var(--muted-foreground))' }}
                                    axisLine={{ stroke: 'hsl(var(--border))' }}
                                    tickLine={false}
                                />
                                <YAxis
                                    allowDecimals={false}
                                    tick={{ fontSize: 11, fill: 'hsl(var(--muted-foreground))' }}
                                    axisLine={false}
                                    tickLine={false}
                                />
                                <Tooltip content={<HourlyTooltip />} cursor={{ fill: 'hsl(var(--muted))' }} />
                                <Bar dataKey="calls" fill="hsl(var(--primary))" radius={[3, 3, 0, 0]} maxBarSize={28} />
                            </BarChart>
                        </ResponsiveContainer>
                    </div>
                </div>

                {/* Top 5 agents */}
                <div className="bg-card rounded-lg border border-border shadow-card p-5 flex flex-col">
                    <h2 className="text-sm font-semibold text-foreground mb-4">Top 5 Agents Today</h2>
                    {loading ? (
                        <div className="space-y-2">
                            {[...Array(5)].map((_, i) => (
                                <div key={i} className="h-8 rounded bg-muted animate-pulse" />
                            ))}
                        </div>
                    ) : top5.length === 0 ? (
                        <p className="text-sm text-muted-foreground text-center py-8">
                            No call data yet. Upload a CSV to get started.
                        </p>
                    ) : (
                        <div className="overflow-x-auto w-full max-w-full">
                            <table className="w-full text-sm min-w-0">
                                <thead>
                                <tr className="border-b border-border">
                                    <th className="text-left text-xs font-medium text-muted-foreground py-2 pr-3 whitespace-nowrap">#</th>
                                    <th className="text-left text-xs font-medium text-muted-foreground py-2 pr-3 whitespace-nowrap">Agent</th>
                                    <th className="text-right text-xs font-medium text-muted-foreground py-2 whitespace-nowrap">Answered</th>
                                </tr>
                                </thead>
                                <tbody>
                                {top5.map((agent) => (
                                    <tr key={agent.agent_ext} className="border-b border-border/50 hover:bg-muted/30 transition-colors">
                                        <td className="py-2 pr-3 text-muted-foreground font-medium whitespace-nowrap">{agent.rank}</td>
                                        <td className="py-2 pr-3 min-w-0">
                                            <p className="font-medium text-foreground truncate">{agent.agent_name || agent.agent_ext}</p>
                                            {agent.agent_name && (
                                                <p className="text-xs text-muted-foreground">Ext {agent.agent_ext}</p>
                                            )}
                                        </td>
                                        <td className="py-2 text-right font-semibold text-foreground tabular-nums whitespace-nowrap">
                                            {agent.answered_calls}
                                        </td>
                                    </tr>
                                ))}
                                </tbody>
                            </table>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
};

export default OverviewPage;
