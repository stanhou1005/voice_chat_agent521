import { useState, useEffect, useCallback } from 'react';
import * as api from '../services/api';

export default function SettingsModal({ isOpen, onClose }) {
  const [form, setForm] = useState({
    model_name: '',
    base_url: '',
    api_key: '',
    tavily_key: '',
    proxy_url: '',
  });
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    if (isOpen) {
      api.getSettings().then(setForm).catch(console.error);
      setSaved(false);
    }
  }, [isOpen]);

  const handleChange = useCallback((e) => {
    const { name, value } = e.target;
    setForm((prev) => ({ ...prev, [name]: value }));
  }, []);

  const handleSave = useCallback(async () => {
    await api.updateSettings(form);
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  }, [form]);

  if (!isOpen) return null;

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <h2>设置</h2>

        <label>模型名称</label>
        <input name="model_name" value={form.model_name} onChange={handleChange} />

        <label>模型服务地址</label>
        <input name="base_url" value={form.base_url} onChange={handleChange} />

        <label>模型 API Key</label>
        <input name="api_key" type="password" value={form.api_key} onChange={handleChange} />

        <label>Tavily Search API Key</label>
        <input name="tavily_key" type="password" value={form.tavily_key} onChange={handleChange} />

        <label>代理地址（可选）</label>
        <input name="proxy_url" value={form.proxy_url} onChange={handleChange} placeholder="http://host:port" />

        <div className="modal-actions">
          <button className="btn-save" onClick={handleSave}>保存</button>
          <button className="btn-close" onClick={onClose}>关闭</button>
          {saved && <span className="saved-hint">已保存</span>}
        </div>
      </div>
    </div>
  );
}
