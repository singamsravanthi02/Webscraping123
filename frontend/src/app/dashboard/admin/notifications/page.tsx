"use client";

import { useState, useEffect } from "react";
import { Send, Bell, Mail, Smartphone, History, Clock, AlertCircle, CheckCircle2 } from "lucide-react";
import api from "@/lib/api";

export default function AdminNotificationsPage() {
  const [logs, setLogs] = useState<any[]>([]);
  const [subject, setSubject] = useState("");
  const [message, setMessage] = useState("");
  const [channel, setChannel] = useState("email");
  const [isSending, setIsSending] = useState(false);
  const [activeTab, setActiveTab] = useState("broadcast");

  useEffect(() => {
    if (activeTab === "logs") {
      fetchLogs();
    }
  }, [activeTab]);

  const fetchLogs = async () => {
    try {
      const res = await api.get("/notifications/logs");
      setLogs(res.data);
    } catch (error) {
      console.error(error);
      setLogs([]);
    }
  };

  const handleBroadcast = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSending(true);
    try {
      await api.post("/notifications/broadcast", { subject, message, channel });
      alert("Broadcast successfully queued!");
      setSubject("");
      setMessage("");
    } catch (error) {
      console.error(error);
      alert("Failed to send broadcast");
    } finally {
      setIsSending(false);
    }
  };

  const getStatusIcon = (status: string) => {
    switch(status.toLowerCase()) {
      case 'sent': return <CheckCircle2 className="w-5 h-5 text-green-400" />;
      case 'failed': return <AlertCircle className="w-5 h-5 text-red-400" />;
      case 'processing': return <Clock className="w-5 h-5 text-yellow-400" />;
      default: return <Clock className="w-5 h-5 text-gray-400" />;
    }
  };

  const getChannelIcon = (ch: string) => {
    switch(ch.toLowerCase()) {
      case 'email': return <Mail className="w-4 h-4" />;
      case 'sms': return <Smartphone className="w-4 h-4" />;
      default: return <Bell className="w-4 h-4" />;
    }
  };

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500 text-white">
      
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 bg-[#1a1a24] p-8 rounded-3xl border border-[#2a2a35] shadow-2xl relative overflow-hidden">
        <div className="absolute -top-24 -right-24 w-64 h-64 bg-blue-500/20 blur-3xl rounded-full" />
        <div className="relative z-10">
          <h1 className="text-3xl font-bold flex items-center gap-3">
            <Bell className="w-8 h-8 text-blue-400" />
            Notification Engine
          </h1>
          <p className="text-gray-400 mt-2">Manage queues, broadcasts, and automated alerts across Email, SMS, and Push.</p>
        </div>
      </div>

      <div className="flex gap-4 border-b border-[#2a2a35] pb-px">
        <button 
          onClick={() => setActiveTab("broadcast")}
          className={`px-4 py-2 font-medium text-sm transition-colors border-b-2 ${activeTab === 'broadcast' ? 'border-blue-500 text-blue-400' : 'border-transparent text-gray-400 hover:text-white'}`}
        >
          Send Broadcast
        </button>
        <button 
          onClick={() => setActiveTab("logs")}
          className={`px-4 py-2 font-medium text-sm transition-colors border-b-2 ${activeTab === 'logs' ? 'border-blue-500 text-blue-400' : 'border-transparent text-gray-400 hover:text-white'}`}
        >
          Queue & Logs
        </button>
      </div>

      {activeTab === "broadcast" && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          <div className="bg-[#1a1a24] p-6 rounded-2xl border border-[#2a2a35]">
            <h2 className="text-xl font-semibold mb-6 flex items-center gap-2">
              <Send className="w-5 h-5 text-blue-400" />
              Compose Broadcast
            </h2>
            <form onSubmit={handleBroadcast} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-400 mb-2">Channel</label>
                <div className="flex gap-4">
                  {['email', 'sms', 'push'].map(ch => (
                    <label key={ch} className="flex items-center gap-2 cursor-pointer">
                      <input 
                        type="radio" 
                        name="channel" 
                        value={ch} 
                        checked={channel === ch}
                        onChange={(e) => setChannel(e.target.value)}
                        className="text-blue-500 bg-[#13131a] border-[#2a2a35]"
                      />
                      <span className="capitalize text-gray-300 flex items-center gap-1">
                        {getChannelIcon(ch)} {ch}
                      </span>
                    </label>
                  ))}
                </div>
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-400 mb-2">Subject (for Email/Push)</label>
                <input 
                  type="text"
                  value={subject}
                  onChange={(e) => setSubject(e.target.value)}
                  placeholder="Important Update..."
                  required
                  className="w-full bg-[#13131a] border border-[#2a2a35] rounded-xl px-4 py-3 text-white focus:outline-none focus:border-blue-500 transition-colors"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-400 mb-2">Message Body</label>
                <textarea 
                  value={message}
                  onChange={(e) => setMessage(e.target.value)}
                  placeholder="Write your message here..."
                  required
                  rows={6}
                  className="w-full bg-[#13131a] border border-[#2a2a35] rounded-xl px-4 py-3 text-white focus:outline-none focus:border-blue-500 transition-colors resize-none"
                />
              </div>

              <button 
                type="submit"
                disabled={isSending}
                className="w-full flex items-center justify-center gap-2 bg-blue-600 hover:bg-blue-500 text-white px-6 py-3 rounded-xl font-medium transition-all shadow-lg disabled:opacity-50"
              >
                {isSending ? 'Queuing...' : 'Send Broadcast'}
                <Send className="w-4 h-4" />
              </button>
            </form>
          </div>

          <div className="bg-[#1a1a24] p-6 rounded-2xl border border-[#2a2a35]">
            <h2 className="text-xl font-semibold mb-6 flex items-center gap-2">
              <History className="w-5 h-5 text-purple-400" />
              Active System Triggers
            </h2>
            <div className="space-y-4">
              {[
                { title: 'Job Alerts', desc: 'Triggered when a new matching job is posted.', ch: ['email', 'push'], status: 'active' },
                { title: 'Interview Reminders', desc: 'Triggered 24h before an AI interview.', ch: ['sms', 'email'], status: 'active' },
                { title: 'Weekly Reports', desc: 'Summary of analytics sent every Sunday.', ch: ['email'], status: 'active' },
                { title: 'Assessment Deadline', desc: 'Triggered 48h before an assessment closes.', ch: ['push'], status: 'active' }
              ].map((trigger, idx) => (
                <div key={idx} className="p-4 bg-[#13131a] rounded-xl border border-[#2a2a35] flex justify-between items-center">
                  <div>
                    <h3 className="font-semibold text-white">{trigger.title}</h3>
                    <p className="text-sm text-gray-400">{trigger.desc}</p>
                    <div className="flex gap-2 mt-2">
                      {trigger.ch.map(c => (
                        <span key={c} className="text-xs bg-[#2a2a35] px-2 py-1 rounded flex items-center gap-1 uppercase">
                          {getChannelIcon(c)} {c}
                        </span>
                      ))}
                    </div>
                  </div>
                  <div className="px-3 py-1 bg-green-500/10 text-green-400 rounded-full text-xs font-medium border border-green-500/20">
                    Active
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {activeTab === "logs" && (
        <div className="bg-[#1a1a24] p-6 rounded-2xl border border-[#2a2a35]">
          <h2 className="text-xl font-semibold mb-6 flex items-center gap-2">
            <History className="w-5 h-5 text-blue-400" />
            Notification Queue & Logs
          </h2>
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm text-gray-300">
              <thead className="bg-[#13131a] text-gray-400">
                <tr>
                  <th className="px-4 py-3 rounded-tl-lg">ID</th>
                  <th className="px-4 py-3">User ID</th>
                  <th className="px-4 py-3">Template</th>
                  <th className="px-4 py-3">Channel</th>
                  <th className="px-4 py-3">Status</th>
                  <th className="px-4 py-3 rounded-tr-lg">Timestamp</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#2a2a35]">
                {logs.map((log) => (
                  <tr key={log.id} className="hover:bg-[#13131a] transition-colors">
                    <td className="px-4 py-3 font-medium">#{log.id}</td>
                    <td className="px-4 py-3">{log.user_id}</td>
                    <td className="px-4 py-3">{log.template_name}</td>
                    <td className="px-4 py-3 uppercase text-xs flex items-center gap-1 mt-1">
                      {getChannelIcon(log.channel)} {log.channel}
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        {getStatusIcon(log.status)}
                        <span className="capitalize">{log.status}</span>
                      </div>
                      {log.error_message && (
                        <p className="text-xs text-red-400 mt-1 max-w-[200px] truncate">{log.error_message}</p>
                      )}
                    </td>
                    <td className="px-4 py-3 text-gray-500">
                      {new Date(log.created_at).toLocaleString()}
                    </td>
                  </tr>
                ))}
                {logs.length === 0 && (
                  <tr>
                    <td colSpan={6} className="px-4 py-8 text-center text-gray-500">
                      No logs available.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

    </div>
  );
}
