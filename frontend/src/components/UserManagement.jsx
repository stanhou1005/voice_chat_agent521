import { useState, useEffect } from 'react';
import * as api from '../services/api';

function ResetPassword({ userId, username, onDone }) {
  const [pw, setPw] = useState('');
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState('');

  async function handleReset(e) {
    e.preventDefault();
    if (!pw) return;
    setBusy(true); setErr('');
    try {
      await api.resetUserPassword(userId, pw);
      setPw('');
      onDone();
    } catch (e) { setErr(e.message); }
    finally { setBusy(false); }
  }

  return (
    <form className="reset-pw-form" onSubmit={handleReset}>
      <input type="password" value={pw} onChange={e => setPw(e.target.value)}
        placeholder={`${username} 新密码`} className="reset-pw-input" />
      <button type="submit" className="btn-save" disabled={busy} style={{margin:0}}>改密</button>
      {err && <span className="login-error" style={{fontSize:11}}>{err}</span>}
    </form>
  );
}

export default function UserManagement({ isOpen, onClose }) {
  const [users, setUsers] = useState([]);
  const [newUsername, setNewUsername] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (isOpen) _loadUsers();
  }, [isOpen]);

  async function _loadUsers() {
    try {
      const data = await api.getUsers();
      setUsers(data.users || []);
    } catch (e) {
      setError('加载用户列表失败');
    }
  }

  async function handleCreate(e) {
    e.preventDefault();
    if (!newUsername.trim() || !newPassword) return;
    setError('');
    setLoading(true);
    try {
      await api.createUser(newUsername.trim(), newPassword);
      setNewUsername('');
      setNewPassword('');
      await _loadUsers();
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  async function handleDelete(userId, username) {
    if (!confirm(`确定删除用户 "${username}"？`)) return;
    setError('');
    try {
      await api.deleteUser(userId);
      await _loadUsers();
    } catch (err) {
      setError(err.message);
    }
  }

  if (!isOpen) return null;

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content user-management" onClick={e => e.stopPropagation()}>
        <h2>用户管理</h2>

        {error && <div className="login-error">{error}</div>}

        <form onSubmit={handleCreate} className="user-create-form">
          <input
            type="text" value={newUsername} onChange={e => setNewUsername(e.target.value)}
            placeholder="新用户名" autoFocus
          />
          <input
            type="password" value={newPassword} onChange={e => setNewPassword(e.target.value)}
            placeholder="新密码"
          />
          <button type="submit" className="btn-save" disabled={loading}>
            {loading ? '创建中…' : '创建用户'}
          </button>
        </form>

        <div className="user-list">
          {users.map(u => (
            <div key={u.id} className="user-row">
              <span className="user-info">
                <strong>{u.username}</strong>
                <span className="user-role-tag">{u.role === 'admin' ? '管理员' : '普通用户'}</span>
              </span>
              <span className="user-actions">
                <ResetPassword userId={u.id} username={u.username} onDone={() => {}} />
                <button
                  className="btn-delete-user"
                  onClick={() => handleDelete(u.id, u.username)}
                >删除</button>
              </span>
            </div>
          ))}
          {users.length === 0 && <p className="session-empty">暂无用户</p>}
        </div>

        <div className="modal-actions">
          <button className="btn-close" onClick={onClose}>关闭</button>
        </div>
      </div>
    </div>
  );
}
