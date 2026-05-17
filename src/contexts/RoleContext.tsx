import React, { createContext, useContext, useState, type ReactNode } from 'react';

export type Role = 'admin' | 'agent';

interface RoleContextType {
    role: Role;
    setRole: (role: Role) => void;
    canAccessSettings: boolean;
}

const RoleContext = createContext<RoleContextType | undefined>(undefined);

export function RoleProvider({ children }: { children: ReactNode }) {
    const [role, setRole] = useState<Role>('admin');
    const canAccessSettings = role === 'admin';

    return (
        <RoleContext.Provider value={{ role, setRole, canAccessSettings }}>
            {children}
        </RoleContext.Provider>
    );
}

export function useRole() {
    const ctx = useContext(RoleContext);
    if (!ctx) throw new Error('useRole must be used within a RoleProvider');
    return ctx;
}
