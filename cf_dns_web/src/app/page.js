"use client"
import { useState, useEffect } from 'react';

export default function Home() {
  const [configs, setConfigs] = useState([]);
  const [intervalTime, setIntervalTime] = useState(30);
  const [loading, setLoading] = useState(true);
  const [modalOpen, setModalOpen] = useState(false);
  const [editIndex, setEditIndex] = useState(-1);
  const [formData, setFormData] = useState({ AUTH_EMAIL: '', AUTH_KEY: '', ZONE_ID: '', RECORD_NAME: '', PROXIED: false });
  const [logMessages, setLogMessages] = useState([]);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      const [confRes, setRes] = await Promise.all([
        fetch('/api/configs'),
        fetch('/api/settings')
      ]);
      const confData = await confRes.json();
      const setData = await setRes.json();
      setConfigs(confData);
      if (setData.interval) setIntervalTime(setData.interval);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const saveSettings = async () => {
    try {
      const res = await fetch('/api/settings', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ interval: intervalTime })
      });
      const data = await res.json();
      if (data.success) alert(data.message);
    } catch (e) {
      alert('Lỗi lưu cài đặt');
    }
  };

  const saveConfig = async () => {
    let newConfigs = [...configs];
    if (editIndex >= 0) {
      newConfigs[editIndex] = formData;
    } else {
      newConfigs.push(formData);
    }
    
    try {
      const res = await fetch('/api/configs', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(newConfigs)
      });
      if (res.ok) {
        setConfigs(newConfigs);
        setModalOpen(false);
      }
    } catch (e) {
      alert('Lỗi lưu cấu hình');
    }
  };

  const deleteConfig = async (index) => {
    if (!confirm('Bạn có chắc chắn muốn xoá?')) return;
    let newConfigs = configs.filter((_, i) => i !== index);
    try {
      await fetch('/api/configs', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(newConfigs)
      });
      setConfigs(newConfigs);
    } catch (e) {}
  };

  const openAdd = () => {
    setEditIndex(-1);
    setFormData({ AUTH_EMAIL: '', AUTH_KEY: '', ZONE_ID: '', RECORD_NAME: '', PROXIED: false });
    setModalOpen(true);
  };

  const openEdit = (index) => {
    setEditIndex(index);
    setFormData({ ...configs[index] });
    setModalOpen(true);
  };

  const forceUpdate = async () => {
    setLogMessages(["Đang gửi yêu cầu (Force Update)..."]);
    try {
      const res = await fetch('/api/force-update', { method: 'POST' });
      const data = await res.json();
      setLogMessages(data.results || ["Hoàn tất"]);
    } catch (e) {
      setLogMessages([`Lỗi: ${e.message}`]);
    }
  };

  return (
    <div className="min-h-screen bg-slate-900 text-white p-8">
      <div className="max-w-5xl mx-auto">
        <h1 className="text-4xl font-bold mb-2 bg-gradient-to-r from-blue-400 to-purple-500 bg-clip-text text-transparent">Cloudflare DNS Auto Update</h1>
        <p className="text-slate-400 mb-8">Independent Standalone Web Dashboard</p>

        {/* Cài đặt */}
        <div className="bg-slate-800/50 p-6 rounded-xl border border-slate-700/50 backdrop-blur-md mb-8 flex items-center justify-between">
          <div>
            <h2 className="text-xl font-semibold">Trạng thái Dịch vụ</h2>
            <p className="text-sm text-slate-400">Daemon đang chạy ngầm và tự động cập nhật</p>
          </div>
          <div className="flex items-center space-x-4">
            <span className="text-sm">Thời gian quét:</span>
            <input 
              type="number" 
              value={intervalTime} 
              onChange={e => setIntervalTime(e.target.value)} 
              className="bg-slate-900 border border-slate-700 rounded px-3 py-1 w-24 focus:outline-none focus:border-blue-500" 
              min="10" 
            />
            <span className="text-sm">giây</span>
            <button onClick={saveSettings} className="bg-blue-600 hover:bg-blue-500 px-4 py-2 rounded-lg text-sm font-medium transition">Lưu Thời Gian</button>
          </div>
        </div>

        {/* Danh sách cấu hình */}
        <div className="bg-slate-800/50 p-6 rounded-xl border border-slate-700/50 backdrop-blur-md mb-8">
          <div className="flex justify-between mb-6">
            <h2 className="text-xl font-semibold">Cấu hình Tên miền</h2>
            <div className="space-x-3">
              <button onClick={openAdd} className="bg-green-600 hover:bg-green-500 px-4 py-2 rounded-lg text-sm font-medium transition">Thêm Cấu Hình</button>
              <button onClick={forceUpdate} className="bg-orange-600 hover:bg-orange-500 px-4 py-2 rounded-lg text-sm font-medium transition">Force Update (Test)</button>
            </div>
          </div>

          {loading ? (
            <p className="text-slate-400">Đang tải...</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="border-b border-slate-700 text-slate-400">
                    <th className="py-3 px-4">Tên miền (Record)</th>
                    <th className="py-3 px-4">Zone ID</th>
                    <th className="py-3 px-4">Proxy</th>
                    <th className="py-3 px-4 text-right">Hành động</th>
                  </tr>
                </thead>
                <tbody>
                  {configs.length === 0 && (
                    <tr>
                      <td colSpan="4" className="py-6 text-center text-slate-500">Chưa có cấu hình nào. Hãy thêm mới!</td>
                    </tr>
                  )}
                  {configs.map((conf, i) => (
                    <tr key={i} className="border-b border-slate-700/50 hover:bg-slate-700/20 transition">
                      <td className="py-3 px-4 font-medium">{conf.RECORD_NAME}</td>
                      <td className="py-3 px-4 font-mono text-sm">{conf.ZONE_ID}</td>
                      <td className="py-3 px-4">
                        {conf.PROXIED === 'true' || conf.PROXIED === true ? (
                          <span className="bg-orange-500/20 text-orange-400 px-2 py-1 rounded text-xs font-semibold">Bật (Cam)</span>
                        ) : (
                          <span className="bg-slate-600/30 text-slate-400 px-2 py-1 rounded text-xs font-semibold">Tắt (Xám)</span>
                        )}
                      </td>
                      <td className="py-3 px-4 text-right space-x-3">
                        <button onClick={() => openEdit(i)} className="text-blue-400 hover:text-blue-300">Sửa</button>
                        <button onClick={() => deleteConfig(i)} className="text-red-400 hover:text-red-300">Xóa</button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* Logs / Test Results */}
        {logMessages.length > 0 && (
          <div className="bg-black/50 p-6 rounded-xl border border-slate-800 font-mono text-sm">
            <h3 className="text-slate-400 mb-3 uppercase tracking-wider text-xs">Test Logs</h3>
            <div className="space-y-1">
              {logMessages.map((msg, idx) => (
                <div key={idx} className={msg.includes('thành công') ? 'text-green-400' : msg.includes('Lỗi') ? 'text-red-400' : 'text-slate-300'}>
                  &gt; {msg}
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Modal Thêm/Sửa */}
      {modalOpen && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4 z-50">
          <div className="bg-slate-800 border border-slate-700 rounded-xl p-6 w-full max-w-md shadow-2xl">
            <h2 className="text-xl font-bold mb-4">{editIndex >= 0 ? 'Sửa Cấu Hình' : 'Thêm Cấu Hình'}</h2>
            
            <div className="space-y-4">
              <div>
                <label className="block text-sm text-slate-400 mb-1">Email Cloudflare</label>
                <input type="text" className="w-full bg-slate-900 border border-slate-700 rounded px-4 py-2 focus:border-blue-500 focus:outline-none" 
                  value={formData.AUTH_EMAIL} onChange={e => setFormData({...formData, AUTH_EMAIL: e.target.value})} placeholder="email@domain.com" />
              </div>
              <div>
                <label className="block text-sm text-slate-400 mb-1">API Key / Token</label>
                <input type="text" className="w-full bg-slate-900 border border-slate-700 rounded px-4 py-2 focus:border-blue-500 focus:outline-none" 
                  value={formData.AUTH_KEY} onChange={e => setFormData({...formData, AUTH_KEY: e.target.value})} placeholder="Global API Key / Token" />
              </div>
              <div>
                <label className="block text-sm text-slate-400 mb-1">Zone ID</label>
                <input type="text" className="w-full bg-slate-900 border border-slate-700 rounded px-4 py-2 focus:border-blue-500 focus:outline-none" 
                  value={formData.ZONE_ID} onChange={e => setFormData({...formData, ZONE_ID: e.target.value})} placeholder="xxxxxxxxxx" />
              </div>
              <div>
                <label className="block text-sm text-slate-400 mb-1">Tên miền (Record Name)</label>
                <input type="text" className="w-full bg-slate-900 border border-slate-700 rounded px-4 py-2 focus:border-blue-500 focus:outline-none" 
                  value={formData.RECORD_NAME} onChange={e => setFormData({...formData, RECORD_NAME: e.target.value})} placeholder="home.domain.com" />
              </div>
              <div>
                <label className="flex items-center space-x-2 text-sm text-slate-300">
                  <input type="checkbox" checked={formData.PROXIED === true || formData.PROXIED === 'true'} onChange={e => setFormData({...formData, PROXIED: e.target.checked})} className="rounded bg-slate-900 border-slate-700" />
                  <span>Bật Proxy (Đám mây cam)</span>
                </label>
              </div>
            </div>

            <div className="mt-6 flex justify-end space-x-3">
              <button onClick={() => setModalOpen(false)} className="px-4 py-2 text-sm text-slate-400 hover:text-white transition">Hủy</button>
              <button onClick={saveConfig} className="bg-blue-600 hover:bg-blue-500 px-6 py-2 rounded-lg text-sm font-medium transition">Lưu lại</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
