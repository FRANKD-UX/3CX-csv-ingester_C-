import React, { useEffect, useState, useCallback } from 'react';
import { RiTrophyLine, RiMedalLine, RiArrowUpLine, RiArrowDownLine, RiRefreshLine } from 'react-icons/ri';
import { api, LeaderboardEntry } from '@/services/api';

type Period = 'daily' | 'weekly' | 'monthly';
type SortKey = keyof LeaderboardEntry;
type SortDir = 'asc' | 'desc';

// --- Medal icons -----------------------------------------------------------

const Medal: React.FC<{ rank: number }> = ({ rank }) => {
    if (rank === 1) return <RiMedalLine size={18} style={{ color: '#F59E0B' }} title="Gold" />;
    if (rank === 2) return <RiMedalLine size={18} style={{ color: '#9CA3AF' }} title="Silver" />;
    if (rank === 3) return <RiMedalLine size={18} style={{ color: '#B45309' }} title="Bronze" />;
    return <span className="text-muted-foreground tabular-nums">{rank}</span>;
};

// --- Sort indicator --------------------------------------------------------

const SortIcon: React.FC<{ col: SortKey; sortKey: SortKey; sortDir: SortDir }> = ({ col, sortKey, sortDir }) => {
    if (col !== sortKey) return <RiArrowUpLine size={12} className="text-muted-foreground/30" />;
    return sortDir === 'asc'
        ? <RiArrowUpLine size={12} className="text-primary" />
        : <RiArrowDownLine size={12} className="text-primary" />;
};

// --- Rate badge ------------------------------------------------------------

const RateBadge: React.FC<{ pct: number }> = ({ pct }) => {
    const color = pct >= 80 ? 'text-green-700 bg-green-50 border-green-200'
        : pct >= 60 ? 'text-yellow-700 bg-yellow-50 border-yellow-200'
            : 'text-red-700 bg-red-50 border-red-200';
    return (
        <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium border ${color}`}>
      {pct.toFixed(1)}%
    </span>
    );
};

// --- Page ------------------------------------------------------------------

const LeaderboardPage: React.FC = () => {
    const [period, setPeriod] = useState<Period>('daily');
    const [data, setData] = useState<LeaderboardEntry[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [lastUpdated, setLastUpdated] = useState<Date>(new Date());
    const [sortKey, setSortKey] = useState<SortKey>('rank');
    const [sortDir, setSortDir] = useState<SortDir>('asc');

    const fetchData = useCallback(async () => {
        setLoading(true);
        try {
            const rows = await api.leaderboard(period);
            setData(rows);
            setLastUpdated(new Date());
            setError(null);
        } catch (e) {
            setError((e as Error).message);
        } finally {
            setLoading(false);
        }
    }, [period]);

    useEffect(() => {
        fetchData();
        const id = setInterval(fetchData, 60_000);
        return () => clearInterval(id);
    }, [fetchData]);

    const handleSort = (key: SortKey) => {
        if (sortKey === key) {
            setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'));
        } else {
            setSortKey(key);
            setSortDir('asc');
        }
    };

    const sorted = [...data].sort((a, b) => {
        const av = a[sortKey];
        const bv = b[sortKey];
        const cmp = typeof av === 'string' ? av.localeCompare(bv as string) : (av as number) - (bv as number);
        return sortDir === 'asc' ? cmp : -cmp;
    });

    const columns: { key: SortKey; label: string; align?: 'right' | 'left' }[] = [
        { key: 'rank', label: 'Rank', align: 'left' },
        { key: 'agent_name', label: 'Agent', align: 'left' },
        { key: 'total_calls', label: 'Total Calls', align: 'right' },
        { key: 'answered_calls', label: 'Answered', align: 'right' },
        { key: 'missed_calls', label: 'Missed', align: 'right' },
        { key: 'avg_talk_mins', label: 'Avg Talk', align: 'right' },
        { key: 'answer_rate_pct', label: 'Answer Rate', align: 'right' },
    ];

    const PERIODS: { value: Period; label: string }[] = [
        { value: 'daily', label: 'Daily' },
        { value: 'weekly', label: 'Weekly' },
        { value: 'monthly', label: 'Monthly' },
    ];

    return (
        <div className="space-y-6">
            {/* Header */}
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                <div>
                    <h1 className="text-xl font-bold text-foreground flex items-center gap-2 text-balance">
                        <RiTrophyLine size={20} className="text-primary shrink-0" />
                        Leaderboard
                    </h1>
                    <p className="text-sm text-muted-foreground mt-0.5">Agent performance rankings</p>
                </div>
                <div className="flex items-center gap-3 shrink-0">
                    <div className="flex items-center gap-1 text-xs text-muted-foreground">
                        <RiRefreshLine size={13} className={loading ? 'animate-spin text-primary' : ''} />
                        <span className="hidden sm:inline">
              {lastUpdated.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
            </span>
                    </div>
                    {/* Period toggle */}
                    <div className="flex items-center rounded-lg border border-border overflow-hidden">
                        {PERIODS.map((p) => (
                            <button
                                key={p.value}
                                onClick={() => setPeriod(p.value)}
                                className={[
                                    'px-3 py-1.5 text-sm font-medium transition-colors duration-150',
                                    period === p.value
                                        ? 'bg-primary text-primary-foreground'
                                        : 'bg-card text-muted-foreground hover:bg-muted hover:text-foreground',
                                ].join(' ')}
                            >
                                {p.label}
                            </button>
                        ))}
                    </div>
                </div>
            </div>

            {error && (
                <div className="rounded-lg border border-destructive/30 bg-destructive/10 px-4 py-3 text-sm text-destructive">
                    {error}
                </div>
            )}

            {/* Table */}
            <div className="bg-card rounded-lg border border-border shadow-card">
                <div className="w-full max-w-full overflow-x-auto">
                    <table className="w-full text-sm">
                        <thead>
                        <tr className="border-b border-border bg-muted/40">
                            {columns.map((col) => (
                                <th
                                    key={col.key}
                                    onClick={() => handleSort(col.key)}
                                    className={[
                                        'px-4 py-3 text-xs font-semibold text-muted-foreground uppercase tracking-wide cursor-pointer select-none whitespace-nowrap',
                                        col.align === 'right' ? 'text-right' : 'text-left',
                                        'hover:text-foreground transition-colors',
                                    ].join(' ')}
                                >
                    <span className="inline-flex items-center gap-1">
                      {col.label}
                        <SortIcon col={col.key} sortKey={sortKey} sortDir={sortDir} />
                    </span>
                                </th>
                            ))}
                        </tr>
                        </thead>
                        <tbody>
                        {loading ? (
                            [...Array(5)].map((_, i) => (
                                <tr key={i} className="border-b border-border/50">
                                    {columns.map((c) => (
                                        <td key={c.key} className="px-4 py-3">
                                            <div className="h-4 rounded bg-muted animate-pulse" />
                                        </td>
                                    ))}
                                </tr>
                            ))
                        ) : sorted.length === 0 ? (
                            <tr>
                                <td colSpan={columns.length} className="px-4 py-12 text-center text-muted-foreground text-sm">
                                    No agent data for this period. Upload a CSV file to populate the leaderboard.
                                </td>
                            </tr>
                        ) : (
                            sorted.map((entry, idx) => (
                                <tr
                                    key={entry.agent_ext}
                                    className={[
                                        'border-b border-border/50 hover:bg-muted/30 transition-colors',
                                        idx % 2 === 1 ? 'bg-muted/10' : '',
                                    ].join(' ')}
                                >
                                    <td className="px-4 py-3 whitespace-nowrap">
                                        <div className="flex items-center gap-1.5">
                                            <Medal rank={entry.rank} />
                                        </div>
                                    </td>
                                    <td className="px-4 py-3 min-w-0">
                                        <p className="font-medium text-foreground truncate">
                                            {entry.agent_name || entry.agent_ext}
                                        </p>
                                        {entry.agent_name && (
                                            <p className="text-xs text-muted-foreground">Ext {entry.agent_ext}</p>
                                        )}
                                    </td>
                                    <td className="px-4 py-3 text-right tabular-nums font-medium text-foreground whitespace-nowrap">
                                        {entry.total_calls}
                                    </td>
                                    <td className="px-4 py-3 text-right tabular-nums text-foreground whitespace-nowrap">
                                        <span className="text-green-700 font-medium">{entry.answered_calls}</span>
                                    </td>
                                    <td className="px-4 py-3 text-right tabular-nums text-foreground whitespace-nowrap">
                                        <span className="text-red-600">{entry.missed_calls}</span>
                                    </td>
                                    <td className="px-4 py-3 text-right tabular-nums text-foreground whitespace-nowrap">
                                        {entry.avg_talk_mins.toFixed(1)} min
                                    </td>
                                    <td className="px-4 py-3 text-right whitespace-nowrap">
                                        <RateBadge pct={entry.answer_rate_pct} />
                                    </td>
                                </tr>
                            ))
                        )}
                        </tbody>
                    </table>
                </div>
                {sorted.length > 0 && (
                    <div className="px-4 py-2 border-t border-border text-xs text-muted-foreground">
                        Showing {sorted.length} agent{sorted.length !== 1 ? 's' : ''} · Auto-refreshes every 60s
                    </div>
                )}
            </div>
        </div>
    );
};

export default LeaderboardPage;
