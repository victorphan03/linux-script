"use client";

import { useState, useEffect } from "react";

export default function Dashboard() {
  const [configs, setConfigs] = useState([]);
  const [settings, setSettings] = useState({ interval: 30 });
  const [loading, setLoading] = useState(true);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingConfig, setEditingConfig] = useState(null);
  
  const [formData, setFormData] = useState({
    AUTH_EMAIL: "",
    AUTH_KEY: "",
    ZONE_ID: "",
    RECORD_NAME: "",
    PROXIED: "false",
    OLD_RECORD_NAME: ""
  });

  const [notification, setNotification] = useState({ show: false, message: "", type: "success" });

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    setLoading(true);
    try {
      const resConf = await fetch("/api/configs");
      const confs = await resConf.json();
      setConfigs(confs);

      const resSet = await fetch("/api/settings");
      const sets = await resSet.json();
      setSettings(sets);
    } catch (e) {
      showNotification("Lỗi khi tải dữ liệu", "error");
    }
    setLoading(false);
  };

  const showNotification = (message, type = "success") => {
    setNotification({ show: true, message, type });
    setTimeout(() => setNotification({ show: false, message: "", type: "success" }), 3000);
  };

  const openModal = (conf = null) => {
    if (conf) {
      setFormData({ ...conf, OLD_RECORD_NAME: conf.RECORD_NAME });
      setEditingConfig(conf);
    } else {
      setFormData({ AUTH_EMAIL: "", AUTH_KEY: "", ZONE_ID: "", RECORD_NAME: "", PROXIED: "false", OLD_RECORD_NAME: "" });
      setEditingConfig(null);
    }
    setIsModalOpen(true);
  };

  const handleClone = (conf) => {
    setFormData({ 
      ...conf, 
      RECORD_NAME: conf.RECORD_NAME + "-copy",
      OLD_RECORD_NAME: ""
    });
    setEditingConfig(null);
    setIsModalOpen(true);
  };

  const handleSaveConfig = async (e) => {
    e.preventDefault();
    
    // Xử lý tạo mới hoặc sửa
    let newConfigs = [...configs];
    let confObj = { ...formData };
    const oldName = confObj.OLD_RECORD_NAME;
    delete confObj.OLD_RECORD_NAME;

    if (editingConfig) {
      const idx = newConfigs.findIndex(c => c.RECORD_NAME === (oldName || editingConfig.RECORD_NAME));
      if (idx > -1) {
        newConfigs[idx] = confObj;
      } else {
        newConfigs.push(confObj);
      }
    } else {
      newConfigs.push(confObj);
    }

    try {
      const res = await fetch("/api/configs", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(newConfigs)
      });
      if (res.ok) {
        showNotification("Lưu cấu hình thành công");
        setConfigs(newConfigs);
        setIsModalOpen(false);
      }
    } catch (e) {
      showNotification("Lỗi lưu cấu hình", "error");
    }
  };

  const handleDelete = async (recordName) => {
    if (!confirm(`Bạn có chắc muốn xoá ${recordName}?`)) return;
    const newConfigs = configs.filter(c => c.RECORD_NAME !== recordName);
    try {
      const res = await fetch("/api/configs", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(newConfigs)
      });
      if (res.ok) {
        showNotification("Đã xoá cấu hình");
        setConfigs(newConfigs);
      }
    } catch (e) {
      showNotification("Lỗi khi xoá", "error");
    }
  };

  const handleForceUpdate = async () => {
    showNotification("Đang chạy Force Update...", "info");
    try {
      const res = await fetch("/api/force-update", { method: "POST" });
      const data = await res.json();
      if (data.success) {
        alert("Kết quả Update:\n\n" + data.results.join("\n"));
        showNotification("Force Update hoàn tất");
      } else {
        showNotification("Lỗi Force Update", "error");
      }
    } catch (e) {
      showNotification("Lỗi kết nối", "error");
    }
  };

  const handleSaveSettings = async () => {
    try {
      const res = await fetch("/api/settings", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(settings)
      });
      if (res.ok) {
        showNotification("Lưu thời gian chờ thành công");
      }
    } catch (e) {
      showNotification("Lỗi lưu cài đặt", "error");
    }
  };

  return (
    <div className="min-h-screen bg-slate-900 text-slate-100 font-sans p-8 transition-colors duration-300 relative overflow-hidden">
      {/* Background blobs for premium glassmorphism feel */}
      <div className="absolute top-[-10%] left-[-10%] w-[40%] h-[40%] rounded-full bg-blue-600/20 blur-[120px] pointer-events-none"></div>
      <div className="absolute bottom-[-10%] right-[-10%] w-[40%] h-[40%] rounded-full bg-purple-600/20 blur-[120px] pointer-events-none"></div>

      {/* Notification Toast */}
      {notification.show && (
        <div className={`fixed top-5 right-5 px-6 py-3 rounded-lg shadow-xl backdrop-blur-md z-50 transition-all duration-300 animate-fade-in-down
          ${notification.type === 'error' ? 'bg-red-500/80 border border-red-500/50' : notification.type === 'info' ? 'bg-blue-500/80 border border-blue-500/50' : 'bg-emerald-500/80 border border-emerald-500/50'}`}>
          {notification.message}
        </div>
      )}

      <div className="max-w-6xl mx-auto relative z-10">
        <header className="mb-10 flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
          <div>
            <h1 className="text-4xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-blue-400 to-purple-400 mb-2">
              Cloudflare DNS
            </h1>
            <p className="text-slate-400">Trình tự động cập nhật IP động độc lập</p>
          </div>
          
          <div className="flex items-center gap-3 bg-white/5 backdrop-blur-md px-5 py-3 rounded-2xl border border-white/10 shadow-lg">
            <span className="text-sm text-slate-300">Quét mỗi</span>
            <input 
              type="number" 
              value={settings.interval} 
              onChange={e => setSettings({...settings, interval: parseInt(e.target.value) || 30})}
              className="w-16 bg-slate-800/50 border border-slate-600 rounded px-2 py-1 text-center focus:outline-none focus:border-blue-500 transition-colors"
              min="10"
            />
            <span className="text-sm text-slate-300 mr-2">giây</span>
            <button 
              onClick={handleSaveSettings}
              className="bg-blue-600 hover:bg-blue-500 text-white px-3 py-1.5 rounded-lg text-sm font-medium transition-all shadow-lg shadow-blue-500/20 active:scale-95 cursor-pointer"
            >
              Lưu
            </button>
          </div>
        </header>

        <main>
          <div className="flex gap-4 mb-6">
            <button 
              onClick={() => openModal()}
              className="flex items-center gap-2 bg-gradient-to-r from-emerald-500 to-emerald-600 hover:from-emerald-400 hover:to-emerald-500 text-white px-5 py-2.5 rounded-xl font-semibold transition-all shadow-lg shadow-emerald-500/20 active:scale-95 cursor-pointer"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 4v16m8-8H4"></path></svg>
              Thêm Cấu Hình
            </button>
            <button 
              onClick={handleForceUpdate}
              className="flex items-center gap-2 bg-white/10 hover:bg-white/20 border border-white/10 text-white px-5 py-2.5 rounded-xl font-semibold transition-all backdrop-blur-md active:scale-95 cursor-pointer"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"></path></svg>
              Force Update Test
            </button>
          </div>

          <div className="bg-slate-800/40 backdrop-blur-xl border border-slate-700/50 rounded-2xl shadow-2xl overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="bg-slate-800/80 text-slate-300 text-sm uppercase tracking-wider border-b border-slate-700/50">
                    <th className="px-6 py-4 font-semibold">Tên miền (Record)</th>
                    <th className="px-6 py-4 font-semibold">Zone ID</th>
                    <th className="px-6 py-4 font-semibold">Proxy</th>
                    <th className="px-6 py-4 font-semibold text-right">Hành động</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-700/50">
                  {loading ? (
                    <tr>
                      <td colSpan="4" className="px-6 py-8 text-center text-slate-400">
                        <div className="inline-block animate-spin w-6 h-6 border-2 border-blue-500 border-t-transparent rounded-full"></div>
                        <p className="mt-2">Đang tải dữ liệu...</p>
                      </td>
                    </tr>
                  ) : configs.length === 0 ? (
                    <tr>
                      <td colSpan="4" className="px-6 py-8 text-center text-slate-400">
                        Chưa có cấu hình nào. Hãy thêm mới!
                      </td>
                    </tr>
                  ) : (
                    configs.map((conf, idx) => (
                      <tr key={idx} className="hover:bg-slate-700/30 transition-colors group">
                        <td className="px-6 py-4 font-medium text-blue-300">{conf.RECORD_NAME}</td>
                        <td className="px-6 py-4 text-slate-400 font-mono text-sm">{conf.ZONE_ID}</td>
                        <td className="px-6 py-4">
                          {(conf.PROXIED === 'true' || conf.PROXIED === true) ? (
                            <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-orange-500/20 text-orange-400 border border-orange-500/20">
                              <span className="w-1.5 h-1.5 rounded-full bg-orange-500 animate-pulse"></span>
                              Bật (Đám mây cam)
                            </span>
                          ) : (
                            <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-slate-500/20 text-slate-400 border border-slate-500/20">
                              <span className="w-1.5 h-1.5 rounded-full bg-slate-500"></span>
                              Tắt (Đám mây xám)
                            </span>
                          )}
                        </td>
                        <td className="px-6 py-4 text-right whitespace-nowrap">
                          <button 
                            onClick={() => handleClone(conf)}
                            className="text-slate-400 hover:text-green-400 p-2 transition-colors inline-block cursor-pointer"
                            title="Nhân bản"
                          >
                            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M8 7v8a2 2 0 002 2h6M8 7V5a2 2 0 012-2h4.586a1 1 0 01.707.293l4.414 4.414a1 1 0 01.293.707V15a2 2 0 01-2 2h-2M8 7H6a2 2 0 00-2 2v10a2 2 0 002 2h8a2 2 0 002-2v-2"></path></svg>
                          </button>
                          <button 
                            onClick={() => openModal(conf)}
                            className="text-slate-400 hover:text-blue-400 p-2 transition-colors inline-block cursor-pointer"
                            title="Sửa"
                          >
                            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"></path></svg>
                          </button>
                          <button 
                            onClick={() => handleDelete(conf.RECORD_NAME)}
                            className="text-slate-400 hover:text-red-400 p-2 transition-colors inline-block cursor-pointer"
                            title="Xóa"
                          >
                            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"></path></svg>
                          </button>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </main>
      </div>

      {/* Modal Overlay */}
      {isModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-fade-in">
          <div className="bg-slate-800 border border-slate-700 w-full max-w-lg rounded-2xl shadow-2xl overflow-hidden transform animate-scale-in">
            <div className="px-6 py-4 border-b border-slate-700 bg-slate-800/80 flex justify-between items-center">
              <h3 className="text-xl font-bold text-white">{editingConfig ? "Sửa Cấu Hình" : "Thêm Cấu Hình Mới"}</h3>
              <button onClick={() => setIsModalOpen(false)} className="text-slate-400 hover:text-white transition-colors cursor-pointer">
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12"></path></svg>
              </button>
            </div>
            
            <form onSubmit={handleSaveConfig} className="p-6 space-y-4">
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-1">Email Cloudflare</label>
                <input required type="email" value={formData.AUTH_EMAIL} onChange={e => setFormData({...formData, AUTH_EMAIL: e.target.value})} className="w-full bg-slate-900 border border-slate-700 rounded-lg px-4 py-2.5 text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none transition-all" placeholder="name@example.com" />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-1">API Key / Token</label>
                <input required type="text" value={formData.AUTH_KEY} onChange={e => setFormData({...formData, AUTH_KEY: e.target.value})} className="w-full bg-slate-900 border border-slate-700 rounded-lg px-4 py-2.5 text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none transition-all" placeholder="Global API Key hoặc API Token" />
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-300 mb-1">Zone ID</label>
                <input required type="text" value={formData.ZONE_ID} onChange={e => setFormData({...formData, ZONE_ID: e.target.value})} className="w-full bg-slate-900 border border-slate-700 rounded-lg px-4 py-2.5 text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none transition-all" placeholder="32 ký tự ID" />
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-300 mb-1">Tên miền (Record Name)</label>
                <input required type="text" value={formData.RECORD_NAME} onChange={e => setFormData({...formData, RECORD_NAME: e.target.value})} className="w-full bg-slate-900 border border-slate-700 rounded-lg px-4 py-2.5 text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none transition-all" placeholder="Ví dụ: home.domain.com" />
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-300 mb-1">Trạng thái Proxy</label>
                <select value={formData.PROXIED} onChange={e => setFormData({...formData, PROXIED: e.target.value})} className="w-full bg-slate-900 border border-slate-700 rounded-lg px-4 py-2.5 text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none transition-all appearance-none">
                  <option value="true">Bật Proxy (Đám mây cam)</option>
                  <option value="false">Tắt Proxy (Đám mây xám - Khuyên dùng cho HomeLab)</option>
                </select>
              </div>

              <div className="pt-4 flex justify-end gap-3">
                <button type="button" onClick={() => setIsModalOpen(false)} className="px-5 py-2.5 rounded-lg text-slate-300 hover:bg-slate-700 font-medium transition-colors cursor-pointer">
                  Hủy
                </button>
                <button type="submit" className="px-5 py-2.5 bg-blue-600 hover:bg-blue-500 text-white rounded-lg font-medium shadow-lg shadow-blue-500/20 transition-all active:scale-95 cursor-pointer">
                  Lưu Cấu Hình
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Global styles for animations */}
      <style dangerouslySetInnerHTML={{__html: `
        @keyframes fadeInDown {
          from { opacity: 0; transform: translateY(-20px); }
          to { opacity: 1; transform: translateY(0); }
        }
        @keyframes fadeIn {
          from { opacity: 0; }
          to { opacity: 1; }
        }
        @keyframes scaleIn {
          from { opacity: 0; transform: scale(0.95); }
          to { opacity: 1; transform: scale(1); }
        }
        .animate-fade-in-down { animation: fadeInDown 0.3s ease-out forwards; }
        .animate-fade-in { animation: fadeIn 0.2s ease-out forwards; }
        .animate-scale-in { animation: scaleIn 0.2s ease-out forwards; }
      `}} />
    </div>
  );
}
