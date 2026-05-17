import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import IntersectObserver from '@/components/common/IntersectObserver';
import { Toaster } from '@/components/ui/sonner';
import DashboardLayout from '@/components/layouts/DashboardLayout';
import SettingsGuard from '@/components/common/SettingsGuard';
import { RoleProvider } from '@/contexts/RoleContext';
import { routes } from './routes';

const App: React.FC = () => {
    return (
        <RoleProvider>
            <Router>
                <IntersectObserver />
                <DashboardLayout>
                    <SettingsGuard>
                        <Routes>
                            {routes.map((route, index) => (
                                <Route key={index} path={route.path} element={route.element} />
                            ))}
                            <Route path="*" element={<Navigate to="/" replace />} />
                        </Routes>
                    </SettingsGuard>
                </DashboardLayout>
                <Toaster position="top-right" />
            </Router>
        </RoleProvider>
    );
};

export default App;
