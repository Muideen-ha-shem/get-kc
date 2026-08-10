import { ReactNode } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { HavisIQMark } from '../../components/HavisIQMark';

const NAV_ITEMS = [
  { to: '/admin', label: 'Dashboard' },
  { to: '/admin/workspaces', label: 'Workspaces' },
  { to: '/admin/users', label: 'Users' },
  { to: '/admin/agents', label: 'Agents' },
  { to: '/admin/audit', label: 'Audit Logs' },
];

export function AdminLayout({ children }: { children: ReactNode }) {
  const location = useLocation();

  return (
    <div className="min-h-screen bg-gray-50 flex">
      <aside className="w-56 border-r bg-white flex flex-col">
        <div className="flex items-center gap-2 px-4 py-4 border-b">
          <HavisIQMark />
          <span className="font-semibold">Admin Portal</span>
        </div>
        <nav className="flex flex-col p-2 gap-1">
          {NAV_ITEMS.map((item) => (
            <Link
              key={item.to}
              to={item.to}
              className={`rounded px-3 py-2 text-sm ${
                location.pathname === item.to ? 'bg-blue-50 text-blue-700 font-medium' : 'text-gray-600 hover:bg-gray-100'
              }`}
            >
              {item.label}
            </Link>
          ))}
        </nav>
      </aside>
      <main className="flex-1 overflow-y-auto p-6">{children}</main>
    </div>
  );
}
