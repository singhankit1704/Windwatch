import { useEffect, useState } from "react";
import { LineChart, Line, BarChart, Bar, XAxis, YAxis, Tooltip, Legend, CartesianGrid, ResponsiveContainer } from "recharts";

const api = (p) => fetch(p).then((r) => (r.ok ? r.json() : Promise.reject(r.statusText)));
const mw = (v) => (v == null ? "-" : Math.round(v).toLocaleString() + " MW");

function Decision({ cutoff }) {
  const [date, setDate] = useState("2026-01-15");
  const [rows, setRows] = useState([]);
  const [err, setErr] = useState("");
  useEffect(() => {
    setErr("");
    api(`/api/decision?date=${date}&cutoff_hour=${cutoff}`).then(setRows).catch(() => { setRows([]); setErr("No data for this date"); });
  }, [date, cutoff]);
  const avg = rows.length ? rows.reduce((s, r) => s + r.forecast, 0) / rows.length : null;
  return (
    <>
      <div className="controls">
        <label>Delivery day: <input type="date" value={date} min="2026-01-01" max="2026-01-31" onChange={(e) => setDate(e.target.value)} /></label>
      </div>
      {err && <p>{err}</p>}
      {rows.length > 0 && (
        <>
          <div className="cards">
            <div className="card"><span>Avg forecast wind (what you see at decision time)</span><b>{mw(avg)}</b></div>
            <div className="card"><span>Latest forecast available was published</span><b>{rows[rows.length - 1].publish}</b></div>
          </div>
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={rows}>
              <CartesianGrid strokeDasharray="3 3" /><XAxis dataKey="time" interval={3} /><YAxis width={80} />
              <Tooltip /><Legend />
              <Line dataKey="forecast" name="Forecast (known day-ahead, MW)" stroke="#0b7fc4" dot={false} strokeWidth={2} />
              <Line dataKey="actual" name="Actual (after the fact, MW)" stroke="#e8590c" dot={false} strokeWidth={2} />
            </LineChart>
          </ResponsiveContainer>
          <p className="note">Power to buy from other sources = demand minus forecast wind, plus a buffer for forecast error (see the Accuracy tab).</p>
        </>
      )}
    </>
  );
}

const Bars = ({ data, x, keys, h = 250 }) => (
  <ResponsiveContainer width="100%" height={h}>
    <BarChart data={data}><CartesianGrid strokeDasharray="3 3" /><XAxis dataKey={x} /><YAxis width={70} /><Tooltip /><Legend />
      {keys.map((k) => <Bar key={k.key} dataKey={k.key} name={k.name} fill={k.color} />)}
    </BarChart>
  </ResponsiveContainer>
);

function Accuracy({ cutoff }) {
  const [d, setD] = useState(null);
  const [hz, setHz] = useState([]);
  useEffect(() => { api(`/api/accuracy?cutoff_hour=${cutoff}`).then(setD); }, [cutoff]);
  useEffect(() => { api("/api/horizon").then(setHz); }, []);
  if (!d) return <p>Loading...</p>;
  const s = d.summary;
  const mae = { key: "mae", name: "MAE (MW)", color: "#0b7fc4" };
  const bias = { key: "bias", name: "Bias (MW)", color: "#e8590c" };
  return (
    <>
      <div className="cards">
        <div className="card"><span>Mean absolute error</span><b>{mw(s.mae)}</b></div>
        <div className="card"><span>RMSE</span><b>{mw(s.rmse)}</b></div>
        <div className="card"><span>Bias (actual - forecast)</span><b>{mw(s.bias)}</b></div>
        <div className="card"><span>Error as % of avg wind</span><b>{s.nmae_pct.toFixed(1)}%</b></div>
        <div className="card"><span>90% of the time error is under</span><b>{mw(s.p90_abs)}</b></div>
        <div className="card"><span>Shortfall buffer (90% safe)</span><b>{mw(s.shortfall_p90)}</b></div>
      </div>
      <p className="note">Shortfall buffer: on 9 of 10 half-hours, actual wind was no more than this far below the forecast. Cover this extra amount to avoid being short most of the time.</p>
      <h3>Daily error</h3><Bars data={d.daily} x="date" keys={[mae, bias]} />
      <h3>Error by hour of day</h3><Bars data={d.by_hour} x="hour" keys={[mae, bias]} />
      <h3>How errors are spread (actual - forecast, MW)</h3><Bars data={d.histogram} x="bin" keys={[{ key: "count", name: "Half-hours", color: "#2f9e44" }]} />
      <h3>Error vs forecast horizon (how far ahead it was made)</h3><Bars data={hz} x="label" keys={[mae]} />
    </>
  );
}

export default function App() {
  const [tab, setTab] = useState("decision");
  const [cutoff, setCutoff] = useState(9);
  return (
    <>
      <header><h1>WindWatch</h1><p>UK wind generation: what the day-ahead forecast said vs what happened (January 2026)</p></header>
      <main>
        <div className="controls">
          <label>Decision time (UTC hour, day before delivery): <select value={cutoff} onChange={(e) => setCutoff(+e.target.value)}>{[6, 8, 9, 10, 12].map((h) => <option key={h} value={h}>{String(h).padStart(2, "0")}:00</option>)}</select></label>
        </div>
        <div className="tabs">
          <button className={tab === "decision" ? "on" : ""} onClick={() => setTab("decision")}>Decision view</button>
          <button className={tab === "accuracy" ? "on" : ""} onClick={() => setTab("accuracy")}>Accuracy</button>
        </div>
        <div className="panel">{tab === "decision" ? <Decision cutoff={cutoff} /> : <Accuracy cutoff={cutoff} />}</div>
      </main>
    </>
  );
}
