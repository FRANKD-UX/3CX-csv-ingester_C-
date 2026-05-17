import React, { useEffect, useState, useCallback } from 'react';
import { RiHistoryLine, RiRefreshLine, RiErrorWarningLine } from 'react-icons/ri';
import { api, ImportLog } from '@/services/api';

// --- Status badge ----------------------------------------------------------

const StatusBadge: React.FC<{ status: string | null }> = ({ status }) => {
    if (status === 'success') {
        return (
            <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-green-50 text-green-700 border border-green-200">
        success
      </span>
        );
    }
    if (status === 'error') {
        return (
            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium bg-red-50 text-red-700 border border-red-200">
        <RiErrorWarningLine size={11} />
        error
      </span>
        );
    }
    if (status === 'pending') {
        return (
            <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-yellow-50 text-yellow-700 border border-yellow-200">
        pending
      </span>
        );
    }
    return <span className="text-muted-foreground text-xs">—</span>;
};

// --- Date formatting -------------------------------------------------------

function formatDate(iso: string | null): string {
    if (!iso) return '—';
    try {
        return new Date(iso).toLocaleString(undefined, {
            month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit',
        });
    } catch {
        return iso;
    }
}

function shortName(filename: string | null): string {
    if (!filename) return '—';
    // Show just the filename, not full path
    return filename.split(/[\\/]/).pop() ?? filename;
}

// --- Page ------------------------------------------------------------------

const HistoryPage: React.FC = () => {
    const [logs, setLogs] = useState<ImportLog[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [lastUpdated, setLastUpdated] = useState<Date>(new Date());
    const [expandedId, setExpandedId] = useState<number | null>(null);

    const fetchLogs = useCallback(async () => {
        try {
            const data = await api.imports();
            setLogs(data);
            setLastUpdated(new Date());
            setError(null);
        } catch (e) {
            setError((e as Error).message);
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        fetchLogs();
        const id = setInterval(fetchLogs, 30_000);
        return () => clearInterval(id);
    }, [fetchLogs]);

    const toggleExpand = (id: number) => setExpandedId((prev) => (prev === id ? null : id));

    return (
        <div className="space-y-6">
            {/* Header */}
            <div className="flex items-center justify-between gap-4">
                <div>
                    <h1 className="text-xl font-bold text-foreground flex items-center gap-2 text-balance">
                        <RiHistoryLine size={20} className="text-primary shrink-0" />
                        Import History
                    </h1>
                    <p className="text-sm text-muted-foreground mt-0.5">Last 20 file imports</p>
                </div>
                <div className="flex items-center gap-2 text-xs text-muted-foreground shrink-0">
                    <RiRefreshLine size={13} className={loading ? 'animate-spin text-primary' : ''} />
                    <span className="hidden sm:inline">
            {lastUpdated.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
          </span>
                    <button
                        onClick={fetchLogs}
                        className="ml-1 px-2 py-1 rounded text-xs border border-border bg-card hover:bg-muted transition-colors text-foreground"
                    >
                        Refresh
                    </button>
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
                            <th className="text-left px-4 py-3 text-xs font-semibold text-muted-foreground uppercase tracking-wide whitespace-nowrap">Filename</th>
                            <th className="text-left px-4 py-3 text-xs font-semibold text-muted-foreground uppercase tracking-wide whitespace-nowrap">PBX Detected</th>
                            <th className="text-right px-4 py-3 text-xs font-semibold text-muted-foreground uppercase tracking-wide whitespace-nowrap">Rows In</th>
                            <th className="text-right px-4 py-3 text-xs font-semibold text-muted-foreground uppercase tracking-wide whitespace-nowrap">Skipped</th>
                            <th className="text-left px-4 py-3 text-xs font-semibold text-muted-foreground uppercase tracking-wide whitespace-nowrap">Status</th>
                            <th className="text-left px-4 py-3 text-xs font-semibold text-muted-foreground uppercase tracking-wide whitespace-nowrap">Time</th>
                        </tr>
                        </thead>
                        <tbody>
                        {loading ? (
                            [...Array(5)].map((_, i) => (
                                <tr key={i} className="border-b border-border/50">
                                    {[...Array(6)].map((__, j) => (
                                        <td key={j} className="px-4 py-3">
                                            <div className="h-4 rounded bg-muted animate-pulse" />
                                        </td>
                                    ))}
                                </tr>
                            ))
                        ) : logs.length === 0 ? (
                            <tr>
                                <td colSpan={6} className="px-4 py-12 text-center text-muted-foreground text-sm">
                                    No imports yet. Upload a CSV file to see history here.
                                </td>
                            </tr>
                        ) : (
                            logs.map((log, idx) => (
                                <React.Fragment key={log.id}>
                                    <tr
                                        className={[
                                            'border-b border-border/50 transition-colors',
                                            idx % 2 === 1 ? 'bg-muted/10' : '',
                                            log.error_message ? 'cursor-pointer hover:bg-muted/30' : 'hover:bg-muted/20',
                                        ].join(' ')}
                                        onClick={() => log.error_message && toggleExpand(log.id)}
                                    >
                                        <td className="px-4 py-3 min-w-0 max-w-[200px]">
                                            <p className="font-medium text-foreground truncate" title={log.filename ?? ''}>
                                                {shortName(log.filename)}
                                            </p>
                                        </td>
                                        <td className="px-4 py-3 whitespace-nowrap">
                                            {log.pbx_source ? (
                                                <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-primary/10 text-primary">
                            {log.pbx_source}
                          </span>
                                            ) : (
                                                <span className="text-muted-foreground">—</span>
                                            )}
                                        </td>
                                        <td className="px-4 py-3 text-right tabular-nums font-medium text-foreground whitespace-nowrap">
                                            {log.rows_imported}
                                        </td>
                                        <td className="px-4 py-3 text-right tabular-nums text-muted-foreground whitespace-nowrap">
                                            {log.rows_skipped}
                                        </td>
                                        <td className="px-4 py-3 whitespace-nowrap">
                                            <StatusBadge status={log.status} />
                                        </td>
                                        <td className="px-4 py-3 text-muted-foreground whitespace-nowrap text-xs">
                                            {formatDate(log.processed_at)}
                                        </td>
                                    </tr>
                                    {/* Error detail row */}
                                    {log.error_message && expandedId === log.id && (
                                        <tr className="bg-destructive/5 border-b border-destructive/20">
                                            <td colSpan={6} className="px-4 py-3">
                                                <div className="flex items-start gap-2">
                                                    <RiErrorWarningLine size={15} className="text-destructive mt-0.5 shrink-0" />
                                                    <p className="text-xs text-destructive break-words">{log.error_message}</p>
                                                </div>
                                            </td>
                                        </tr>
                                    )}
                                </React.Fragment>
                            ))
                        )}
                        </tbody>
                    </table>
                </div>
                {logs.length > 0 && (
                    <div className="px-4 py-2 border-t border-border text-xs text-muted-foreground">
                        {logs.length} record{logs.length !== 1 ? 's' : ''} · Auto-refreshes every 30s ·{' '}
                        <span className="text-muted-foreground/70">Click error rows to expand details</span>
                    </div>
                )}
            </div>
        </div>
    );
};

export default HistoryPage;
