import { useState } from 'react';
import { useAdminUsers, useActivateUser, useDeactivateUser, useCreateAdminUser } from '../api/admin';
import { Users, UserCheck, Shield, Clock, UserPlus, Power, PowerOff, X } from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';

export function AdminDashboardStats() {
  const { data, isLoading, error } = useAdminUsers();
  const activateUser = useActivateUser();
  const deactivateUser = useDeactivateUser();
  const createUser = useCreateAdminUser();

  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [formData, setFormData] = useState({ username: '', email: '', password: '', role: 'etradie' });
  const [formError, setFormError] = useState('');

  const handleCreateSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setFormError('');
    createUser.mutate(formData, {
      onSuccess: () => {
        setIsCreateModalOpen(false);
        setFormData({ username: '', email: '', password: '', role: 'etradie' });
      },
      onError: (err: any) => {
        setFormError(err?.response?.data?.error || 'Failed to create user');
      }
    });
  };

  if (isLoading) {
    return (
      <div className="animate-pulse flex space-x-4 mb-6">
        <div className="flex-1 space-y-4 py-1">
          <div className="h-20 bg-black/5 dark:bg-white/5 rounded-2xl w-full"></div>
        </div>
      </div>
    );
  }

  if (error) {
    return null; // Fail silently if there's an error (e.g., unauthorized)
  }

  const users = data?.users || [];
  const totalCount = data?.count || 0;
  const activeCount = users.filter((u: any) => u.active).length;
  const adminCount = users.filter((u: any) => u.role === 'admin').length;

  return (
    <div className="mb-6 animate-fade-in max-w-7xl">
      <div className="flex items-start justify-between mb-8">
        <div className="flex items-start gap-4">
          <div className="mt-0.5 rounded-xl bg-brand/10 p-2 border border-brand/20 shadow-sm">
            <Shield className="w-4 h-4 text-brand" strokeWidth={2.5} />
          </div>
          <div className="space-y-1">
            <h3 className="text-[10px] font-black uppercase tracking-[0.2em] text-brand mb-1">
              Platform Administration
            </h3>
            <p className="text-sm font-bold text-black dark:text-white tracking-tight">
              User Management
            </p>
          </div>
        </div>
        <button
          onClick={() => setIsCreateModalOpen(true)}
          className="flex items-center gap-2 rounded-xl bg-black dark:bg-white px-4 py-2.5 text-[10px] font-black uppercase tracking-widest text-white dark:text-black hover:opacity-90 shadow-sm transition-all"
        >
          <UserPlus size={14} strokeWidth={3} />
          Create User
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-10">
        <div className="p-6 rounded-2xl border border-black/10 dark:border-white/10 bg-black/[0.01] dark:bg-white/[0.02] flex items-center justify-between shadow-sm">
          <div>
            <p className="text-[10px] font-black uppercase tracking-[0.2em] text-black/40 dark:text-white/40 mb-1">Total Users</p>
            <p className="text-2xl font-black text-black dark:text-white tracking-tight">{totalCount}</p>
          </div>
          <div className="p-3 bg-brand/10 rounded-xl border border-brand/20">
            <Users size={20} className="text-brand" />
          </div>
        </div>
        <div className="p-6 rounded-2xl border border-black/10 dark:border-white/10 bg-black/[0.01] dark:bg-white/[0.02] flex items-center justify-between shadow-sm">
          <div>
            <p className="text-[10px] font-black uppercase tracking-[0.2em] text-black/40 dark:text-white/40 mb-1">Active Accounts</p>
            <p className="text-2xl font-black text-black dark:text-white tracking-tight">{activeCount}</p>
          </div>
          <div className="p-3 bg-green-500/10 rounded-xl border border-green-500/20">
            <UserCheck size={20} className="text-green-500" />
          </div>
        </div>
        <div className="p-6 rounded-2xl border border-black/10 dark:border-white/10 bg-black/[0.01] dark:bg-white/[0.02] flex items-center justify-between shadow-sm">
          <div>
            <p className="text-[10px] font-black uppercase tracking-[0.2em] text-black/40 dark:text-white/40 mb-1">Administrators</p>
            <p className="text-2xl font-black text-black dark:text-white tracking-tight">{adminCount}</p>
          </div>
          <div className="p-3 bg-purple-500/10 rounded-xl border border-purple-500/20">
            <Shield size={20} className="text-purple-500" />
          </div>
        </div>
      </div>

      <div className="rounded-2xl border border-black/10 dark:border-white/10 bg-black/[0.01] dark:bg-white/[0.02] overflow-hidden shadow-sm">
        <div className="p-6 border-b border-black/5 dark:border-white/5">
          <h3 className="text-sm font-bold text-black dark:text-white">Recent Users</h3>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm text-left">
            <thead className="bg-black/5 dark:bg-white/5 border-b border-black/5 dark:border-white/5">
              <tr>
                <th className="px-6 py-4 text-[10px] font-black uppercase tracking-widest text-black/40 dark:text-white/40">User</th>
                <th className="px-6 py-4 text-[10px] font-black uppercase tracking-widest text-black/40 dark:text-white/40">Role</th>
                <th className="px-6 py-4 text-[10px] font-black uppercase tracking-widest text-black/40 dark:text-white/40">Status</th>
                <th className="px-6 py-4 text-[10px] font-black uppercase tracking-widest text-black/40 dark:text-white/40">Joined</th>
                <th className="px-6 py-4 text-[10px] font-black uppercase tracking-widest text-black/40 dark:text-white/40">Last Login</th>
                <th className="px-6 py-4 text-[10px] font-black uppercase tracking-widest text-black/40 dark:text-white/40 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-black/5 dark:divide-white/5">
              {users.slice(0, 5).map((u: any) => (
                <tr key={u.id} className="hover:bg-black/5 dark:hover:bg-white/5 transition-colors">
                  <td className="px-6 py-4">
                    <div className="flex flex-col">
                      <span className="font-bold text-black dark:text-white tracking-tight">{u.username}</span>
                      <span className="text-[11px] font-medium text-black/40 dark:text-white/40">{u.email}</span>
                    </div>
                  </td>
                  <td className="px-6 py-4">
                    <span className={`inline-flex items-center px-2 py-0.5 rounded text-[10px] font-black uppercase tracking-wider ${
                      u.role === 'admin' ? 'bg-purple-500/10 text-purple-500 border border-purple-500/20' : 'bg-black/5 dark:bg-white/5 text-black/60 dark:text-white/60 border border-black/10 dark:border-white/10'
                    }`}>
                      {u.role}
                    </span>
                  </td>
                  <td className="px-6 py-4">
                    <span className={`inline-flex items-center px-2 py-0.5 rounded text-[10px] font-black uppercase tracking-wider ${
                      u.active ? 'bg-green-500/10 text-green-500 border border-green-500/20' : 'bg-red-500/10 text-red-500 border border-red-500/20'
                    }`}>
                      {u.active ? 'Active' : 'Inactive'}
                    </span>
                  </td>
                  <td className="px-6 py-4 text-[11px] font-bold text-black/60 dark:text-white/60">
                    {formatDistanceToNow(new Date(u.created_at), { addSuffix: true })}
                  </td>
                  <td className="px-6 py-4 text-[11px] font-bold text-black/60 dark:text-white/60">
                    {u.last_login_at ? (
                      <span className="flex items-center gap-1.5">
                        <Clock size={12} strokeWidth={2.5} />
                        {formatDistanceToNow(new Date(u.last_login_at), { addSuffix: true })}
                      </span>
                    ) : (
                      'Never'
                    )}
                  </td>
                  <td className="px-4 py-3 text-right">
                    {u.active ? (
                      <button
                        onClick={() => deactivateUser.mutate(u.id)}
                        disabled={deactivateUser.isPending}
                        className="p-1.5 text-red-500 hover:bg-red-500/10 rounded disabled:opacity-50 transition-colors"
                        title="Deactivate User"
                      >
                        <PowerOff className="w-4 h-4" />
                      </button>
                    ) : (
                      <button
                        onClick={() => activateUser.mutate(u.id)}
                        disabled={activateUser.isPending}
                        className="p-1.5 text-green-500 hover:bg-green-500/10 rounded disabled:opacity-50 transition-colors"
                        title="Activate User"
                      >
                        <Power className="w-4 h-4" />
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
      {isCreateModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
          <div className="bg-white dark:bg-black rounded-2xl shadow-2xl w-full max-w-md overflow-hidden animate-fade-in border border-black/10 dark:border-white/10">
            <div className="flex items-center justify-between p-6 border-b border-black/10 dark:border-white/10 bg-black/[0.02] dark:bg-white/[0.02]">
              <h3 className="text-base font-bold text-black dark:text-white tracking-tight">Create New User</h3>
              <button onClick={() => setIsCreateModalOpen(false)} className="text-black/40 dark:text-white/40 hover:text-black dark:hover:text-white transition-colors">
                <X size={20} strokeWidth={2.5} />
              </button>
            </div>
            <form onSubmit={handleCreateSubmit} className="p-6 space-y-6">
              {formError && (
                <div className="p-4 bg-red-500/10 border border-red-500/20 text-red-500 text-[11px] font-bold rounded-xl">
                  {formError}
                </div>
              )}
              <div className="space-y-2">
                <label className="text-[10px] font-black uppercase tracking-[0.2em] text-black/40 dark:text-white/40 ml-1">Username</label>
                <input
                  type="text"
                  required
                  value={formData.username}
                  onChange={(e) => setFormData({ ...formData, username: e.target.value })}
                  className="w-full rounded-xl border border-black/10 dark:border-white/10 bg-white dark:bg-black px-4 py-3 text-sm font-bold text-black dark:text-white placeholder:text-black/20 dark:placeholder:text-white/20 focus:border-brand transition-all outline-none"
                  placeholder="johndoe"
                />
              </div>
              <div className="space-y-2">
                <label className="text-[10px] font-black uppercase tracking-[0.2em] text-black/40 dark:text-white/40 ml-1">Email</label>
                <input
                  type="email"
                  required
                  value={formData.email}
                  onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                  className="w-full rounded-xl border border-black/10 dark:border-white/10 bg-white dark:bg-black px-4 py-3 text-sm font-bold text-black dark:text-white placeholder:text-black/20 dark:placeholder:text-white/20 focus:border-brand transition-all outline-none"
                  placeholder="john@example.com"
                />
              </div>
              <div className="space-y-2">
                <label className="text-[10px] font-black uppercase tracking-[0.2em] text-black/40 dark:text-white/40 ml-1">Password</label>
                <input
                  type="password"
                  required
                  value={formData.password}
                  onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                  className="w-full rounded-xl border border-black/10 dark:border-white/10 bg-white dark:bg-black px-4 py-3 text-sm font-bold text-black dark:text-white placeholder:text-black/20 dark:placeholder:text-white/20 focus:border-brand transition-all outline-none"
                  placeholder="••••••••"
                />
              </div>
              <div className="space-y-2">
                <label className="text-[10px] font-black uppercase tracking-[0.2em] text-black/40 dark:text-white/40 ml-1">Role</label>
                <div className="relative">
                  <select
                    value={formData.role}
                    onChange={(e) => setFormData({ ...formData, role: e.target.value })}
                    className="w-full rounded-xl border border-black/10 dark:border-white/10 bg-white dark:bg-black px-4 py-3 text-sm font-bold text-black dark:text-white focus:border-brand transition-all outline-none appearance-none"
                  >
                    <option value="etradie">User (etradie)</option>
                    <option value="admin">Administrator (admin)</option>
                  </select>
                </div>
              </div>
              <div className="pt-4 flex gap-4">
                <button
                  type="button"
                  onClick={() => setIsCreateModalOpen(false)}
                  className="flex-1 rounded-xl border border-black/10 dark:border-white/10 bg-transparent px-4 py-3 text-[10px] font-black uppercase tracking-widest text-black/60 dark:text-white/60 hover:bg-black/5 dark:hover:bg-white/5 transition-all"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={createUser.isPending}
                  className="flex-1 rounded-xl bg-black dark:bg-white px-4 py-3 text-[10px] font-black uppercase tracking-widest text-white dark:text-black hover:opacity-90 shadow-lg shadow-black/10 dark:shadow-white/10 transition-all disabled:opacity-50"
                >
                  {createUser.isPending ? 'Creating...' : 'Create User'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
