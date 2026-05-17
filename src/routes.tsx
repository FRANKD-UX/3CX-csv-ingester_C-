import type { ReactNode } from 'react';
import OverviewPage from './pages/OverviewPage';
import LeaderboardPage from './pages/LeaderboardPage';
import UploadPage from './pages/UploadPage';
import HistoryPage from './pages/HistoryPage';

export interface RouteConfig {
    name: string;
    path: string;
    element: ReactNode;
    visible?: boolean;
    public?: boolean;
}

export const routes: RouteConfig[] = [
    { name: 'Overview', path: '/', element: <OverviewPage />, public: true },
    { name: 'Leaderboard', path: '/leaderboard', element: <LeaderboardPage />, public: true },
    { name: 'Upload', path: '/upload', element: <UploadPage />, public: true },
    { name: 'Import History', path: '/history', element: <HistoryPage />, public: true },
];
