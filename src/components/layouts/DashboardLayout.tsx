import React, { useState } from 'react';
import { NavLink, useLocation } from 'react-router-dom';
import {
    RiDashboardLine, RiTrophyLine, RiUploadCloud2Line,
    RiHistoryLine, RiMenuLine, RiCloseLine, RiPhoneLine,
    RiSettings3Line, RiUserLine, RiShieldUserLine,
} from 'react-icons/ri';
import { useRole, type Role } from '@/contexts/RoleContext';

// ---- Nav item type --------------------------------------------------------

interface NavItem {
    label: string;
    path: string;
    icon: React.ReactNode;
}

const MAIN_NAV: NavItem[] = [
    { label: 'Overview',    path: '/',            icon: <RiDashboardLine size={18} /> },
    { label: 'Leaderboard', path: '/leaderboard', icon: <RiTrophyLine size={18} /> },
];

const SETTINGS_NAV: NavItem[] = [
    { label: 'Upload CSV',     path: '/upload',  icon: <RiUploadCloud2Line size={18} /> },
    { label: 'Import History', path: '/history', icon: <RiHistoryLine size={18} /> },
];

// ---- Role badge icons & colours ------------------------------------------

const ROLE_META: Record<Role, { icon: React.ReactNode; label: string; color: string }> = {
    admin: { icon: <RiShieldUserLine size={14} />, label: 'Admin', color: 'bg-primary/20 text-primary' },
    agent: { icon: <RiUserLine       size={14} />, label: 'Agent', color: 'bg-sidebar-foreground/10 text-sidebar-foreground/70' },
};

// ---- Single nav link -------------------------------------------------------

const NavItem: React.FC<{ item: NavItem; onClick?: () => void }> = ({ item, onClick }) => {
    const location = useLocation();
    const isActive =
        item.path === '/'
            ? location.pathname === '/'
            : location.pathname.startsWith(item.path);

    return (
        <NavLink
            to={item.path}
            onClick={onClick}
            className={[
                'flex items-center gap-3 px-3 py-2.5 rounded-md text-sm font-medium transition-colors duration-150',
                isActive
                    ? 'bg-sidebar-accent text-sidebar-accent-foreground border-l-2 border-primary pl-[10px]'
                    : 'text-sidebar-foreground/70 hover:bg-sidebar-accent hover:text-sidebar-accent-foreground',
            ].join(' ')}
        >
      <span className={isActive ? 'text-primary' : 'text-sidebar-foreground/50'}>
        {item.icon}
      </span>
            {item.label}
        </NavLink>
    );
};

// ---- Role switcher --------------------------------------------------------

const RoleSwitcher: React.FC = () => {
    const { role, setRole } = useRole();
    const current = ROLE_META[role];
    const roles: Role[] = ['admin', 'agent'];

    return (
        <div className="px-3 py-3 border-t border-sidebar-border space-y-2">
            <p className="text-[10px] font-semibold uppercase tracking-widest text-sidebar-foreground/40 px-1">
                Demo Role
            </p>
            <div className="flex flex-col gap-1">
                {roles.map((r) => {
                    const meta = ROLE_META[r];
                    const isSelected = r === role;
                    return (
                        <button
                            key={r}
                            onClick={() => setRole(r)}
                            className={[
                                'flex items-center gap-2 px-3 py-2 rounded-md text-sm font-medium w-full text-left transition-colors duration-150',
                                isSelected
                                    ? `${meta.color} bg-opacity-100`
                                    : 'text-sidebar-foreground/60 hover:bg-sidebar-accent hover:text-sidebar-foreground',
                            ].join(' ')}
                        >
                            <span className={isSelected ? '' : 'opacity-50'}>{meta.icon}</span>
                            {meta.label}
                            {isSelected && (
                                <span className="ml-auto text-[10px] font-semibold uppercase tracking-wide opacity-70">
                  Active
                </span>
                            )}
                        </button>
                    );
                })}
            </div>
            <p className="text-[10px] text-sidebar-foreground/30 px-1 text-pretty">
                Switch roles to demo access control
            </p>
        </div>
    );
};

// ---- Sidebar content -------------------------------------------------------

interface SidebarContentProps {
    onNavClick?: () => void;
}

const SidebarContent: React.FC<SidebarContentProps> = ({ onNavClick }) => {
    const { canAccessSettings } = useRole();

    return (
        <div className="flex flex-col h-full">
            {/* App name */}
            <div className="flex items-center gap-2 px-4 py-5 border-b border-sidebar-border">
                <div className="flex items-center justify-center w-8 h-8 rounded-lg bg-primary shrink-0">
                    <RiPhoneLine size={16} className="text-primary-foreground" />
                </div>
                <div className="min-w-0">
          <span className="text-sidebar-foreground font-semibold text-sm leading-tight block truncate">
            Call Dashboard
          </span>
                    <span className="text-sidebar-foreground/50 text-xs leading-tight block truncate">
            Reporter
          </span>
                </div>
            </div>

            {/* Nav */}
            <nav className="flex-1 px-3 py-4 space-y-4 overflow-y-auto">
                {/* Main section */}
                <div className="space-y-0.5">
                    <p className="text-[10px] font-semibold uppercase tracking-widest text-sidebar-foreground/40 px-3 mb-2">
                        Main
                    </p>
                    {MAIN_NAV.map((item) => (
                        <NavItem key={item.path} item={item} onClick={onNavClick} />
                    ))}
                </div>

                {/* Settings section — admin/manager only */}
                {canAccessSettings && (
                    <div className="space-y-0.5">
                        <div className="flex items-center gap-1.5 px-3 mb-2">
                            <RiSettings3Line size={12} className="text-sidebar-foreground/40" />
                            <p className="text-[10px] font-semibold uppercase tracking-widest text-sidebar-foreground/40">
                                Settings
                            </p>
                        </div>
                        {SETTINGS_NAV.map((item) => (
                            <NavItem key={item.path} item={item} onClick={onNavClick} />
                        ))}
                    </div>
                )}
            </nav>

            {/* Role switcher + version */}
            <div className="shrink-0">
                <RoleSwitcher />
                <div className="px-4 py-2 border-t border-sidebar-border">
                    <p className="text-[10px] text-sidebar-foreground/30">v1.0.0</p>
                </div>
            </div>
        </div>
    );
};

// ---- Layout ---------------------------------------------------------------

interface DashboardLayoutProps {
    children: React.ReactNode;
}

const DashboardLayout: React.FC<DashboardLayoutProps> = ({ children }) => {
    const [mobileOpen, setMobileOpen] = useState(false);

    return (
        <div className="flex min-h-screen w-full bg-background">
            {/* Desktop sidebar */}
            <aside className="hidden lg:flex flex-col w-60 shrink-0 bg-sidebar h-screen sticky top-0 overflow-y-auto">
                <SidebarContent />
            </aside>

            {/* Mobile overlay */}
            {mobileOpen && (
                <div
                    className="fixed inset-0 z-40 bg-black/60 lg:hidden"
                    onClick={() => setMobileOpen(false)}
                />
            )}

            {/* Mobile sidebar drawer */}
            <aside
                className={[
                    'fixed top-0 left-0 h-full w-60 z-50 bg-sidebar flex flex-col transform transition-transform duration-200 ease-out lg:hidden',
                    mobileOpen ? 'translate-x-0' : '-translate-x-full',
                ].join(' ')}
            >
                <div className="absolute top-3 right-3">
                    <button
                        onClick={() => setMobileOpen(false)}
                        className="p-1.5 rounded-md text-sidebar-foreground/60 hover:text-sidebar-foreground hover:bg-sidebar-accent"
                        aria-label="Close menu"
                    >
                        <RiCloseLine size={20} />
                    </button>
                </div>
                <SidebarContent onNavClick={() => setMobileOpen(false)} />
            </aside>

            {/* Main content */}
            <div className="flex-1 min-w-0 flex flex-col overflow-x-hidden">
                {/* Top bar (mobile only) */}
                <header className="lg:hidden flex items-center gap-3 px-4 py-3 bg-white border-b border-border sticky top-0 z-30">
                    <button
                        onClick={() => setMobileOpen(true)}
                        className="p-1.5 rounded-md text-foreground/60 hover:text-foreground hover:bg-muted"
                        aria-label="Open menu"
                    >
                        <RiMenuLine size={20} />
                    </button>
                    <span className="font-semibold text-sm text-foreground truncate">
            Call Dashboard Reporter
          </span>
                </header>

                <main className="flex-1 p-4 md:p-6">
                    {children}
                </main>
            </div>
        </div>
    );
};

export default DashboardLayout;
