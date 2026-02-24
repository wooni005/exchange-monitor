import React, { useState, useEffect } from 'react';
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from 'recharts';

function App() {
  const [data, setData] = useState(null);
  const [history, setHistory] = useState([]);
  const [error, setError] = useState(false);

  const fetchData = async () => {
    try {
      // Fetch latest status
      const resStatus = await fetch('http://127.0.0.1:8000/');
      const statusJson = await resStatus.json();
      setData(statusJson);

      // Fetch chart history
      const resHistory = await fetch('http://127.0.0.1:8000/history');
      const historyJson = await resHistory.json();
      setHistory(historyJson);
      
      setError(false);
    } catch (err) {
      setError(true);
    }
  };

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 30000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="min-h-screen bg-slate-900 flex flex-col items-center justify-center p-4 font-sans text-white">
      <div className="w-full max-w-4xl space-y-4">
        
        {/* Top Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="bg-slate-800 p-6 rounded-2xl border border-slate-700">
            <p className="text-sm text-slate-400 uppercase tracking-widest">Current EUR/CZK</p>
            <p className="text-5xl font-mono text-emerald-400">{data?.latest_rate?.toFixed(4) || "---"}</p>
          </div>
          <div className="bg-slate-800 p-6 rounded-2xl border border-slate-700">
            <p className="text-sm text-slate-400 uppercase tracking-widest">Monthly High</p>
            <p className="text-5xl font-mono text-amber-400">{data?.monthly_high?.toFixed(4) || "---"}</p>
          </div>
        </div>

        {/* Chart Section */}
        <div className="bg-slate-800 p-6 rounded-2xl border border-slate-700 h-80">
          <h3 className="text-slate-400 mb-4 uppercase text-xs tracking-widest">Price Trend (Last 100 checks)</h3>
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={history}>
              <CartesianGrid strokeDasharray="3 3" stroke="#334155" vertical={false} />
              <XAxis dataKey="time" stroke="#64748b" fontSize={10} tickMargin={10} />
              <YAxis domain={['auto', 'auto']} stroke="#64748b" fontSize={10} hide />
              <Tooltip 
                contentStyle={{ backgroundColor: '#1e293b', border: 'none', borderRadius: '8px' }}
                itemStyle={{ color: '#10b981' }}
              />
              <Line 
                type="monotone" 
                dataKey="rate" 
                stroke="#10b981" 
                strokeWidth={3} 
                dot={false} 
                animationDuration={1000}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>

        <div className="text-center text-[10px] text-slate-500 uppercase tracking-widest">
          {error ? "⚠️ Backend Connection Lost" : `Last updated: ${data?.last_checked || "never"}`}
        </div>
      </div>
    </div>
  );
}

export default App;
