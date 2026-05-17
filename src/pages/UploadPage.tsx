import React, { useCallback, useRef, useState } from 'react';
import { RiUploadCloud2Line, RiFileLine, RiCheckLine, RiErrorWarningLine, RiCloseLine } from 'react-icons/ri';
import { api, UploadResult } from '@/services/api';

type UploadState = 'idle' | 'uploading' | 'success' | 'error';

const UploadPage: React.FC = () => {
    const [dragActive, setDragActive] = useState(false);
    const [uploadState, setUploadState] = useState<UploadState>('idle');
    const [result, setResult] = useState<UploadResult | null>(null);
    const [errorMsg, setErrorMsg] = useState<string | null>(null);
    const [selectedFile, setSelectedFile] = useState<File | null>(null);
    const inputRef = useRef<HTMLInputElement>(null);

    const reset = () => {
        setUploadState('idle');
        setResult(null);
        setErrorMsg(null);
        setSelectedFile(null);
        if (inputRef.current) inputRef.current.value = '';
    };

    const handleFile = useCallback(async (file: File) => {
        if (!file.name.toLowerCase().endsWith('.csv')) {
            setErrorMsg('Only .csv files are accepted.');
            setUploadState('error');
            return;
        }
        setSelectedFile(file);
        setUploadState('uploading');
        setResult(null);
        setErrorMsg(null);
        try {
            const res = await api.upload(file);
            setResult(res);
            setUploadState('success');
        } catch (e) {
            setErrorMsg((e as Error).message);
            setUploadState('error');
        }
    }, []);

    // Drag handlers
    const onDragOver = (e: React.DragEvent) => { e.preventDefault(); setDragActive(true); };
    const onDragLeave = () => setDragActive(false);
    const onDrop = (e: React.DragEvent) => {
        e.preventDefault();
        setDragActive(false);
        const file = e.dataTransfer.files[0];
        if (file) handleFile(file);
    };
    const onInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0];
        if (file) handleFile(file);
    };

    return (
        <div className="space-y-6 max-w-2xl">
            <div>
                <h1 className="text-xl font-bold text-foreground text-balance">Upload CSV</h1>
                <p className="text-sm text-muted-foreground mt-0.5">
                    Import call records from your PBX system. Supported formats: 3CX, Yeastar, FreePBX.
                </p>
            </div>

            {/* Drop zone */}
            <div
                onDragOver={onDragOver}
                onDragLeave={onDragLeave}
                onDrop={onDrop}
                className={[
                    'relative rounded-xl border-2 border-dashed transition-all duration-200',
                    dragActive
                        ? 'border-primary bg-primary/5 scale-[1.01]'
                        : 'border-border bg-card hover:border-primary/50 hover:bg-muted/30',
                    uploadState === 'uploading' ? 'pointer-events-none opacity-70' : 'cursor-pointer',
                ].join(' ')}
                onClick={() => uploadState !== 'uploading' && inputRef.current?.click()}
            >
                <input
                    ref={inputRef}
                    type="file"
                    accept=".csv"
                    className="hidden"
                    onChange={onInputChange}
                />
                <div className="flex flex-col items-center gap-4 px-6 py-12 text-center">
                    <div className={[
                        'flex items-center justify-center w-16 h-16 rounded-full transition-colors',
                        dragActive ? 'bg-primary/10' : 'bg-muted',
                    ].join(' ')}>
                        <RiUploadCloud2Line
                            size={32}
                            className={dragActive ? 'text-primary' : 'text-muted-foreground'}
                        />
                    </div>
                    <div>
                        <p className="text-base font-medium text-foreground">
                            {dragActive ? 'Drop your CSV here' : 'Drag & drop your CSV file here'}
                        </p>
                        <p className="text-sm text-muted-foreground mt-1">or click to browse</p>
                    </div>
                    <button
                        type="button"
                        onClick={(e) => { e.stopPropagation(); inputRef.current?.click(); }}
                        className="px-4 py-2 rounded-lg bg-primary text-primary-foreground text-sm font-medium hover:bg-primary/90 transition-colors"
                    >
                        Browse Files
                    </button>
                    <p className="text-xs text-muted-foreground">Accepts .csv files only</p>
                </div>
            </div>

            {/* Uploading state */}
            {uploadState === 'uploading' && selectedFile && (
                <div className="bg-card rounded-lg border border-border p-4 flex items-center gap-3">
                    <RiFileLine size={20} className="text-primary shrink-0" />
                    <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium text-foreground truncate">{selectedFile.name}</p>
                        <div className="mt-1.5 h-1.5 rounded-full bg-muted overflow-hidden">
                            <div className="h-full bg-primary rounded-full animate-pulse w-2/3" />
                        </div>
                    </div>
                    <span className="text-xs text-muted-foreground shrink-0">Uploading…</span>
                </div>
            )}

            {/* Success result card */}
            {uploadState === 'success' && result && (
                <div className="bg-card rounded-lg border border-green-200 shadow-card overflow-hidden">
                    <div className="flex items-center gap-3 px-5 py-4 bg-green-50 border-b border-green-200">
                        <div className="flex items-center justify-center w-8 h-8 rounded-full bg-green-100">
                            <RiCheckLine size={18} className="text-green-700" />
                        </div>
                        <div className="flex-1 min-w-0">
                            <p className="font-semibold text-green-800">Import Successful</p>
                            <p className="text-xs text-green-700 truncate">{result.filename}</p>
                        </div>
                        <button onClick={reset} className="text-green-600 hover:text-green-800 shrink-0" aria-label="Dismiss">
                            <RiCloseLine size={18} />
                        </button>
                    </div>
                    <div className="grid grid-cols-3 divide-x divide-border">
                        <div className="px-5 py-4 text-center">
                            <p className="text-xs text-muted-foreground font-medium uppercase tracking-wide mb-1">PBX Detected</p>
                            <p className="text-lg font-bold text-foreground">{result.pbx_detected}</p>
                        </div>
                        <div className="px-5 py-4 text-center">
                            <p className="text-xs text-muted-foreground font-medium uppercase tracking-wide mb-1">Rows Imported</p>
                            <p className="text-lg font-bold text-green-700 tabular-nums">{result.rows_imported}</p>
                        </div>
                        <div className="px-5 py-4 text-center">
                            <p className="text-xs text-muted-foreground font-medium uppercase tracking-wide mb-1">Rows Skipped</p>
                            <p className="text-lg font-bold text-muted-foreground tabular-nums">{result.rows_skipped}</p>
                        </div>
                    </div>
                    <div className="px-5 py-3 bg-muted/30 border-t border-border">
                        <button
                            onClick={reset}
                            className="text-sm text-primary hover:underline font-medium"
                        >
                            Upload another file
                        </button>
                    </div>
                </div>
            )}

            {/* Error card */}
            {uploadState === 'error' && errorMsg && (
                <div className="bg-card rounded-lg border border-destructive/30 shadow-card overflow-hidden">
                    <div className="flex items-center gap-3 px-5 py-4 bg-destructive/5 border-b border-destructive/20">
                        <div className="flex items-center justify-center w-8 h-8 rounded-full bg-destructive/10">
                            <RiErrorWarningLine size={18} className="text-destructive" />
                        </div>
                        <div className="flex-1 min-w-0">
                            <p className="font-semibold text-destructive">Import Failed</p>
                        </div>
                        <button onClick={reset} className="text-destructive/60 hover:text-destructive shrink-0" aria-label="Dismiss">
                            <RiCloseLine size={18} />
                        </button>
                    </div>
                    <div className="px-5 py-4">
                        <p className="text-sm text-foreground break-words">{errorMsg}</p>
                    </div>
                    <div className="px-5 py-3 bg-muted/30 border-t border-border">
                        <button onClick={reset} className="text-sm text-primary hover:underline font-medium">
                            Try again
                        </button>
                    </div>
                </div>
            )}

            {/* Supported formats info */}
            {uploadState === 'idle' && (
                <div className="bg-card rounded-lg border border-border p-5">
                    <h3 className="text-sm font-semibold text-foreground mb-3">Supported PBX Formats</h3>
                    <div className="space-y-2">
                        {[
                            { name: '3CX', headers: '"Call ID", "Ring Duration", "Dialed Number", "Reason"' },
                            { name: 'Yeastar', headers: '"CallFrom", "CallTo", "Talk Duration", "Disposition"' },
                            { name: 'FreePBX', headers: '"src", "dst", "duration", "disposition", "accountcode"' },
                        ].map((fmt) => (
                            <div key={fmt.name} className="flex gap-3 items-start">
                <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold bg-primary/10 text-primary shrink-0 mt-0.5">
                  {fmt.name}
                </span>
                                <p className="text-xs text-muted-foreground break-words">{fmt.headers}</p>
                            </div>
                        ))}
                    </div>
                </div>
            )}
        </div>
    );
};

export default UploadPage;
