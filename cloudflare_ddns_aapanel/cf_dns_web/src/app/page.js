"use client";
import { useState, useEffect } from "react";

export default function Dashboard() {
  const [settings, setSettings] = useState({ interval: 30, cf_email: "", cf_key: "", cf_zone: "" });
  const [configs, setConfigs] = useState([]);
  const [records, setRecords] = useState([]);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState({ type: "", text: "" });
  const [showAddModal, setShowAddModal] = useState(false);
  const [newRecord, setNewRecord] = useState({ name: "", content: "", proxied: false });

  useEffect(() => {
    fetchSettings();
    fetchConfigs();
  }, []);

  const fetchSettings = async () => {
    const res = await fetch("/api/settings");
    const data = await res.json();
    setSettings((prev) => ({ ...prev, ...data }));
    
    if (data.cf_email && data.cf_key && data.cf_zone) {
      autoFetchRecords(data);
    }
  };

  const autoFetchRecords = async (credData) => {
    try {
      const res = await fetch("/api/fetch-records", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: credData.cf_email, key: credData.cf_key, zoneId: credData.cf_zone }),
      });
      const data = await res.json();
      if (data.success) {
        setRecords(data.data);
      }
    } catch (e) {
      console.error(e);
    }
  };

  const fetchConfigs = async () => {
    const res = await fetch("/api/configs");
    const data = await res.json();
    setConfigs(data);
  };

  const saveSettings = async () => {
    setLoading(true);
    setMessage({ type: "", text: "" });
    try {
      const res = await fetch("/api/settings", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(settings),
      });
      const data = await res.json();
      setMessage({ type: data.success ? "success" : "error", text: data.message || "Lỗi lưu cài đặt" });
    } catch (e) {
      setMessage({ type: "error", text: e.message });
    }
    setLoading(false);
  };

  const forceUpdate = async () => {
    setLoading(true);
    setMessage({ type: "", text: "" });
    try {
      const res = await fetch("/api/force-update", { method: "POST" });
      const data = await res.json();
      setMessage({ type: data.success ? "success" : "error", text: data.results.join(" | ") });
    } catch (e) {
      setMessage({ type: "error", text: e.message });
    }
    setLoading(false);
  };

  const fetchCloudflareRecords = async () => {
    if (!settings.cf_email || !settings.cf_key || !settings.cf_zone) {
      setMessage({ type: "error", text: "Vui lòng lưu thông tin Cloudflare trước khi fetch" });
      return;
    }
    setLoading(true);
    setMessage({ type: "", text: "" });
    try {
      const res = await fetch("/api/fetch-records", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: settings.cf_email, key: settings.cf_key, zoneId: settings.cf_zone }),
      });
      const data = await res.json();
      if (data.success) {
        setRecords(data.data);
        setMessage({ type: "success", text: `Đã tải ${data.data.length} records.` });
      } else {
        setMessage({ type: "error", text: data.error });
      }
    } catch (e) {
      setMessage({ type: "error", text: e.message });
    }
    setLoading(false);
  };

  const toggleDdns = async (record, isActive) => {
    let newConfigs;
    if (isActive) {
      // Remove it
      newConfigs = configs.filter((c) => c.RECORD_NAME !== record.name);
    } else {
      // Add it
      newConfigs = [
        ...configs.filter((c) => c.RECORD_NAME !== record.name),
        {
          AUTH_EMAIL: settings.cf_email,
          AUTH_KEY: settings.cf_key,
          ZONE_ID: settings.cf_zone,
          RECORD_NAME: record.name,
          PROXIED: record.proxied,
        },
      ];
    }
    setConfigs(newConfigs); // optimistic update

    try {
      await fetch("/api/configs", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(newConfigs),
      });
    } catch (e) {
      setMessage({ type: "error", text: "Lỗi lưu cấu hình: " + e.message });
      fetchConfigs(); // revert
    }
  };

  const submitAddRecord = async () => {
    if (!newRecord.name || !newRecord.content) {
      setMessage({ type: "error", text: "Vui lòng nhập tên miền và IP." });
      return;
    }
    setLoading(true);
    setMessage({ type: "", text: "" });
    try {
      const res = await fetch("/api/add-record", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          email: settings.cf_email,
          key: settings.cf_key,
          zoneId: settings.cf_zone,
          recordName: newRecord.name,
          content: newRecord.content,
          proxied: newRecord.proxied
        }),
      });
      const data = await res.json();
      if (data.success) {
        setMessage({ type: "success", text: "Thêm Record thành công." });
        setShowAddModal(false);
        setNewRecord({ name: "", content: "", proxied: false });
        fetchCloudflareRecords();
      } else {
        setMessage({ type: "error", text: data.error });
      }
    } catch (e) {
      setMessage({ type: "error", text: e.message });
    }
    setLoading(false);
  };

  const deleteRecord = async (record) => {
    if (!window.confirm(`Bạn có chắc chắn muốn xóa bản ghi ${record.name} trên Cloudflare?`)) return;
    setLoading(true);
    setMessage({ type: "", text: "" });
    try {
      const res = await fetch("/api/delete-record", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          email: settings.cf_email,
          key: settings.cf_key,
          zoneId: settings.cf_zone,
          recordId: record.id
        }),
      });
      const data = await res.json();
      if (data.success) {
        setMessage({ type: "success", text: "Xóa Record thành công." });
        
        // Remove from DDNS if active
        if (configs.some(c => c.RECORD_NAME === record.name)) {
          const newConfigs = configs.filter((c) => c.RECORD_NAME !== record.name);
          setConfigs(newConfigs);
          await fetch("/api/configs", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(newConfigs),
          });
        }
        
        fetchCloudflareRecords();
      } else {
        setMessage({ type: "error", text: data.error });
      }
    } catch (e) {
      setMessage({ type: "error", text: e.message });
    }
    setLoading(false);
  };

  return (
    <div className="min-h-screen bg-slate-900 text-white p-8 font-sans">
      <div className="max-w-5xl mx-auto space-y-8">
        
        <div className="flex justify-between items-center bg-slate-800/50 p-6 rounded-2xl backdrop-blur border border-slate-700">
          <div>
            <h1 className="text-3xl font-bold bg-gradient-to-r from-blue-400 to-emerald-400 bg-clip-text text-transparent">
              Cloudflare DDNS Manager
            </h1>
            <p className="text-slate-400 mt-2">Standalone Dashboard</p>
          </div>
          <button
            onClick={forceUpdate}
            disabled={loading}
            className="px-6 py-3 bg-gradient-to-r from-amber-500 to-orange-500 rounded-lg font-medium shadow-lg shadow-orange-500/20 hover:shadow-orange-500/40 transition disabled:opacity-50"
          >
            Force Update (Test)
          </button>
        </div>

        {message.text && (
          <div className={`p-4 rounded-lg border ${message.type === "error" ? "bg-red-500/10 border-red-500/20 text-red-400" : "bg-emerald-500/10 border-emerald-500/20 text-emerald-400"}`}>
            {message.text}
          </div>
        )}

        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          
          {/* Settings Panel */}
          <div className="col-span-1 bg-slate-800/50 p-6 rounded-2xl border border-slate-700 h-fit space-y-4">
            <h2 className="text-xl font-semibold mb-4">Cài đặt chung</h2>
            
            <div>
              <label className="block text-sm text-slate-400 mb-1">Email Cloudflare</label>
              <input
                type="text"
                className="w-full bg-slate-900 border border-slate-700 rounded-lg px-4 py-2 focus:ring-2 focus:ring-blue-500 outline-none"
                value={settings.cf_email || ""}
                onChange={(e) => setSettings({ ...settings, cf_email: e.target.value })}
              />
            </div>
            
            <div>
              <label className="block text-sm text-slate-400 mb-1">API Key / Token</label>
              <input
                type="password"
                className="w-full bg-slate-900 border border-slate-700 rounded-lg px-4 py-2 focus:ring-2 focus:ring-blue-500 outline-none"
                value={settings.cf_key || ""}
                onChange={(e) => setSettings({ ...settings, cf_key: e.target.value })}
              />
            </div>
            
            <div>
              <label className="block text-sm text-slate-400 mb-1">Zone ID</label>
              <input
                type="text"
                className="w-full bg-slate-900 border border-slate-700 rounded-lg px-4 py-2 focus:ring-2 focus:ring-blue-500 outline-none"
                value={settings.cf_zone || ""}
                onChange={(e) => setSettings({ ...settings, cf_zone: e.target.value })}
              />
            </div>

            <div>
              <label className="block text-sm text-slate-400 mb-1">Thời gian quét (giây)</label>
              <input
                type="number"
                min="10"
                className="w-full bg-slate-900 border border-slate-700 rounded-lg px-4 py-2 focus:ring-2 focus:ring-blue-500 outline-none"
                value={settings.interval || 30}
                onChange={(e) => setSettings({ ...settings, interval: parseInt(e.target.value) })}
              />
            </div>

            <button
              onClick={saveSettings}
              disabled={loading}
              className="w-full mt-4 px-4 py-2 bg-blue-600 hover:bg-blue-500 rounded-lg font-medium transition disabled:opacity-50"
            >
              Lưu Thông Tin
            </button>
            <div className="flex gap-2 mt-2">
              <button
                onClick={fetchCloudflareRecords}
                disabled={loading}
                className="flex-1 px-4 py-2 bg-emerald-600 hover:bg-emerald-500 rounded-lg font-medium transition disabled:opacity-50"
              >
                Tải Danh Sách
              </button>
              <button
                onClick={() => setShowAddModal(true)}
                disabled={loading}
                className="flex-1 px-4 py-2 bg-blue-600 hover:bg-blue-500 rounded-lg font-medium transition disabled:opacity-50"
              >
                Thêm Subdomain
              </button>
            </div>
          </div>

          {/* Records Panel */}
          <div className="col-span-2 bg-slate-800/50 p-6 rounded-2xl border border-slate-700">
            <h2 className="text-xl font-semibold mb-6">Quản lý A Record</h2>
            
            {records.length === 0 ? (
              <div className="text-center text-slate-500 py-12">
                Chưa có dữ liệu. Hãy tải danh sách A Record từ Cloudflare.
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left">
                  <thead>
                    <tr className="border-b border-slate-700 text-slate-400">
                      <th className="pb-3 font-medium">Tên miền</th>
                      <th className="pb-3 font-medium">IP Hiện tại</th>
                      <th className="pb-3 font-medium">Proxy</th>
                      <th className="pb-3 font-medium text-center">Bật DDNS</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-700">
                    {records.map((rec) => {
                      const isActive = configs.some((c) => c.RECORD_NAME === rec.name);
                      return (
                        <tr key={rec.id} className="hover:bg-slate-800/30 transition">
                          <td className="py-4 font-medium">{rec.name}</td>
                          <td className="py-4 font-mono text-sm text-slate-300">{rec.content}</td>
                          <td className="py-4">
                            {rec.proxied ? (
                              <span className="px-2 py-1 bg-amber-500/20 text-amber-400 rounded-md text-xs">Bật</span>
                            ) : (
                              <span className="px-2 py-1 bg-slate-700 text-slate-400 rounded-md text-xs">Tắt</span>
                            )}
                          </td>
                          <td className="py-4 text-center">
                            <div className="flex items-center justify-center gap-4">
                              <label className="relative inline-flex items-center cursor-pointer">
                                <input
                                  type="checkbox"
                                  className="sr-only peer"
                                  checked={isActive}
                                  onChange={() => toggleDdns(rec, isActive)}
                                />
                                <div className="w-11 h-6 bg-slate-700 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-emerald-500"></div>
                              </label>
                              <button
                                onClick={() => deleteRecord(rec)}
                                className="text-red-400 hover:text-red-300 transition text-sm font-medium"
                              >
                                Xóa CF
                              </button>
                            </div>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </div>

        </div>
      </div>

      {showAddModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
          <div className="bg-slate-800 border border-slate-700 rounded-2xl shadow-xl w-full max-w-md overflow-hidden">
            <div className="p-6 border-b border-slate-700">
              <h3 className="text-xl font-semibold">Thêm A Record Mới</h3>
            </div>
            <div className="p-6 space-y-4">
              <div>
                <label className="block text-sm text-slate-400 mb-1">Tên miền (ví dụ: sub.domain.com)</label>
                <input
                  type="text"
                  className="w-full bg-slate-900 border border-slate-700 rounded-lg px-4 py-2 focus:ring-2 focus:ring-blue-500 outline-none"
                  value={newRecord.name}
                  onChange={(e) => setNewRecord({ ...newRecord, name: e.target.value })}
                />
              </div>
              <div>
                <label className="block text-sm text-slate-400 mb-1">IPv4</label>
                <input
                  type="text"
                  className="w-full bg-slate-900 border border-slate-700 rounded-lg px-4 py-2 focus:ring-2 focus:ring-blue-500 outline-none"
                  value={newRecord.content}
                  onChange={(e) => setNewRecord({ ...newRecord, content: e.target.value })}
                />
              </div>
              <div>
                <label className="block text-sm text-slate-400 mb-1">Proxy</label>
                <select
                  className="w-full bg-slate-900 border border-slate-700 rounded-lg px-4 py-2 focus:ring-2 focus:ring-blue-500 outline-none"
                  value={newRecord.proxied}
                  onChange={(e) => setNewRecord({ ...newRecord, proxied: e.target.value === "true" })}
                >
                  <option value={false}>Tắt</option>
                  <option value={true}>Bật</option>
                </select>
              </div>
            </div>
            <div className="p-6 border-t border-slate-700 bg-slate-800/50 flex justify-end gap-3">
              <button
                onClick={() => setShowAddModal(false)}
                className="px-4 py-2 rounded-lg font-medium hover:bg-slate-700 transition"
              >
                Hủy
              </button>
              <button
                onClick={submitAddRecord}
                disabled={loading}
                className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 rounded-lg font-medium transition disabled:opacity-50"
              >
                Thêm Record
              </button>
            </div>
          </div>
        </div>
      )}

    </div>
  );
}
