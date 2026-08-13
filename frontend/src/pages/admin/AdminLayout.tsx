import { ReactNode } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { ArrowLeft, Bot, Building2, LayoutDashboard, PanelLeft, PanelLeftClose, ScrollText, Users } from 'lucide-react';
import { HavisIQMark } from '../../components/HavisIQMark';
import { PageContainer } from '../../components/PageContainer';
import { useSidebarCollapse } from '../../lib/useSidebarCollapse';

const NAV_ITEMS = [
  { to: '/admin', label: 'Dashboard', icon: LayoutDashboard },
  { to: '/admin/workspaces', label: 'Workspaces', icon: Building2 },
  { to: '/admin/users', label: 'Users', icon: Users },
  { to: '/admin/agents', label: 'Agents', icon: Bot },
  { to: '/admin/audit', label: 'Audit Logs', icon: ScrollText },
];

export function AdminLayout({ children }: { children: ReactNode }) {
  const location = useLocation();
  const [collapsed, setCollapsed] = useSidebarCollapse('havisiq-admin-sidebar-collapsed');

  return (
    <div className="min-h-screen bg-paper flex">
      <aside
        className={`shrink-0 overflow-hidden border-r border-ink/10 bg-white flex flex-col transition-[width] duration-200 ${
          collapsed ? 'w-16' : 'w-56'
        }`}
      >
        <div className="flex items-center justify-between gap-2 px-4 py-4 border-b border-ink/10">
          {collapsed ? (
            <HavisIQMark />
          ) : (
            <div className="flex items-center gap-2 min-w-0">
              <HavisIQMark />
              <span className="font-display font-semibold text-ink truncate">Admin Portal</span>
            </div>
          )}
        </div>
        <div className="px-2 pt-2">
          <Link
            to="/dashboard"
            title={collapsed ? 'Back to Dashboard' : undefined}
            className="flex items-center gap-2 rounded-full px-3 py-2 text-sm text-ink/60 transition hover:bg-paper hover:text-ink"
          >
            <ArrowLeft size={16} className="shrink-0" />
            {!collapsed && <span className="truncate">Back to Dashboard</span>}
          </Link>
        </div>
        <nav className="flex flex-col p-2 gap-1 border-t border-ink/10 mt-1 pt-2">
          {NAV_ITEMS.map((item) => {
            const Icon = item.icon;
            const isActive = location.pathname === item.to;
            return (
              <Link
                key={item.to}
                to={item.to}
                title={collapsed ? item.label : undefined}
                className={`flex items-center gap-2 rounded-full px-3 py-2 text-sm transition ${
                  isActive ? 'bg-gold-50 text-gold-700 font-medium' : 'text-ink/60 hover:bg-paper hover:text-ink'
                }`}
              >
                <Icon size={16} className="shrink-0" />
                {!collapsed && <span className="truncate">{item.label}</span>}
              </Link>
            );
          })}
        </nav>
        <button
          onClick={() => setCollapsed((v) => !v)}
          className="mt-auto flex items-center gap-2 px-4 py-3 text-xs text-ink/50 border-t border-ink/10 transition hover:text-ink hover:bg-paper"
          aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
        >
          {collapsed ? <PanelLeft size={16} /> : <PanelLeftClose size={16} />}
          {!collapsed && <span>Collapse</span>}
        </button>
      </aside>
      <main className="flex-1 overflow-y-auto p-6">
        <PageContainer>{children}</PageContainer>
      </main>
    </div>
  );
}
