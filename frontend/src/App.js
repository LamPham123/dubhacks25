import React, { useEffect, useState } from "react";
import "./App.css";

// CONFIGURATION - Update with your Raspberry Pi IP
const API_BASE_URL = "http://192.168.0.X:5000"; // Replace X with your Pi's IP
const USE_MOCK_DATA = true; // Set to false when ready to connect to real Pi

function App() {
  const [status, setStatus] = useState(null);
  const [diagnostics, setDiagnostics] = useState(null);
  const [solutions, setSolutions] = useState(null);
  const [output, setOutput] = useState("");
  const [loading, setLoading] = useState({ diagnose: false, fix: false });

  const fetchStatus = async () => {
    if (USE_MOCK_DATA) {
      const data = {
        timestamp: new Date().toISOString(),
        status: "healthy",
        metrics: {
          ping: { latency_ms: 27.28 },
          signal: { signal_dbm: -59, quality: "good" }
        }
      };
      setStatus(data);
      return;
    }

    try {
      const response = await fetch(`${API_BASE_URL}/api/monitor`);
      if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
      const data = await response.json();
      setStatus(data);
    } catch (err) {
      console.error("Error fetching status:", err);
    }
  };

  const diagnose = async () => {
    setLoading(prev => ({ ...prev, diagnose: true }));
    setOutput("🔬 Running diagnostics...");
    setDiagnostics(null);
    setSolutions(null);

    if (USE_MOCK_DATA) {
      setTimeout(() => {
        const diagnostic = {
          issue: "Network is healthy",
          summary: "Your connection is working great! Router responds in 6ms, internet in 22ms.",
          details: [
            "✅ Router connection: Excellent (6.5ms)",
            "✅ Internet speed: Good (22ms)",
            "✅ WiFi signal: Strong (-59 dBm)",
            "📶 64 networks nearby on channel 165",
            "🖥️ 4 devices connected"
          ]
        };
        
        setDiagnostics(diagnostic);
        setOutput("");
        setLoading(prev => ({ ...prev, diagnose: false }));
      }, 1500);
      return;
    }

    try {
      const response = await fetch(`${API_BASE_URL}/api/diagnose`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ alert: status })
      });

      if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
      const data = await response.json();
      
      // Transform API data to simplified format
      const simplified = {
        issue: data.issue || "Analysis complete",
        summary: data.root_cause || "Diagnostic completed",
        details: []
      };

      // Add relevant details
      if (data.tools_data?.ping_multiple) {
        const router = data.tools_data.ping_multiple.results.find(r => r.target.includes("192.168"));
        if (router) {
          simplified.details.push(`${router.success ? "✅" : "❌"} Router connection: ${router.latency_ms.toFixed(1)}ms`);
        }
      }

      if (data.tools_data?.wifi_scan) {
        simplified.details.push(`📶 ${data.tools_data.wifi_scan.networks_found} networks nearby`);
      }

      if (data.tools_data?.arp_table) {
        simplified.details.push(`🖥️ ${data.tools_data.arp_table.total_devices} devices connected`);
      }

      setDiagnostics(simplified);
      setOutput("");
      setLoading(prev => ({ ...prev, diagnose: false }));
    } catch (err) {
      console.error("Error running diagnostics:", err);
      setOutput("❌ Diagnostic failed");
      setLoading(prev => ({ ...prev, diagnose: false }));
    }
  };

  const fix = async () => {
    setLoading(prev => ({ ...prev, fix: true }));
    setOutput("🤖 Getting recommendations...");
    setSolutions(null);

    if (USE_MOCK_DATA) {
      setTimeout(() => {
        const solutionData = {
          status: "healthy",
          message: "Your network is working perfectly!",
          actions: [
            "No fixes needed - everything looks good",
            "Keep monitoring if you notice any slowdowns"
          ]
        };
        
        setSolutions(solutionData);
        setOutput("");
        setLoading(prev => ({ ...prev, fix: false }));
      }, 1500);
      return;
    }

    try {
      const response = await fetch(`${API_BASE_URL}/api/fix`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ diagnostic: diagnostics, alert: status })
      });

      if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
      const data = await response.json();
      
      // Simplify solutions
      const simplified = {
        status: data.issue || "complete",
        message: data.root_cause || "Analysis complete",
        actions: data.solutions || []
      };
      
      setSolutions(simplified);
      setOutput("");
      setLoading(prev => ({ ...prev, fix: false }));
    } catch (err) {
      console.error("Error generating solutions:", err);
      setOutput("❌ Failed to get recommendations");
      setLoading(prev => ({ ...prev, fix: false }));
    }
  };

  useEffect(() => {
    fetchStatus();
    const interval = setInterval(fetchStatus, 30000);
    return () => clearInterval(interval);
  }, []);

  const getStatusColor = (statusText) => {
    if (statusText === "healthy") return "good";
    if (statusText === "warning") return "fair";
    return "poor";
  };

  const getSignalPercentage = (dbm) => {
    return Math.max(0, Math.min(100, ((dbm + 90) / 60) * 100));
  };

  const getSignalClass = (signal_dbm) => {
    if (signal_dbm >= -50) return "excellent";
    if (signal_dbm >= -60) return "good";
    if (signal_dbm >= -70) return "fair";
    return "poor";
  };

  return (
    <div className="App">
      <div className="container">
        {/* Header */}
        <div className="header">
          <h1>Dr Wifi</h1>
          <p>Your Network Health Assistant</p>
        </div>

        {/* Main Card */}
        <div className="card">
          {status ? (
            <>
              {/* Status Header */}
              <div className="status-header">
                <div>
                  <h2>Network Status</h2>
                  <div className="status-badge">
                    <span className={`status-dot ${getStatusColor(status.status)}`}></span>
                    <span className="status-text">{status.status}</span>
                  </div>
                </div>
                <div className="timestamp">
                  {new Date(status.timestamp).toLocaleTimeString()}
                </div>
              </div>

              {/* Simple Metrics */}
              <div className="metrics-grid-2">
                <div className="metric-card-large ping">
                  <div className="metric-label">Connection Speed</div>
                  <div className="metric-value">{status.metrics.ping.latency_ms.toFixed(0)}</div>
                  <div className="metric-unit">ms response time</div>
                  <div className="metric-status">
                    {status.metrics.ping.latency_ms < 50 ? "⚡ Fast" : 
                     status.metrics.ping.latency_ms < 100 ? "✅ Good" : "⚠️ Slow"}
                  </div>
                </div>

                <div className="metric-card-large signal">
                  <div className="metric-label">WiFi Signal</div>
                  <div className="metric-value">{status.metrics.signal.signal_dbm}</div>
                  <div className="metric-unit">dBm</div>
                  <div className="signal-bar">
                    <div 
                      className={`signal-bar-fill ${getSignalClass(status.metrics.signal.signal_dbm)}`}
                      style={{ width: `${getSignalPercentage(status.metrics.signal.signal_dbm)}%` }}
                    ></div>
                  </div>
                  <div className="metric-status">
                    {status.metrics.signal.quality === "good" ? "💪 Strong" :
                     status.metrics.signal.quality === "fair" ? "👌 OK" : "⚠️ Weak"}
                  </div>
                </div>
              </div>

              {/* Action Buttons */}
              <div className="buttons">
                <button 
                  className="diagnose" 
                  onClick={diagnose}
                  disabled={loading.diagnose}
                >
                  {loading.diagnose ? "🔄 Checking..." : "🔍 Check My Network"}
                </button>
                <button 
                  className="fix" 
                  onClick={fix}
                  disabled={loading.fix}
                >
                  {loading.fix ? "🔄 Thinking..." : "💡 Get Help"}
                </button>
              </div>
            </>
          ) : (
            <div className="loading">
              <div className="spinner"></div>
              <p>Checking your network...</p>
            </div>
          )}
        </div>

        {/* Diagnostics Card - Simplified */}
        {diagnostics && (
          <div className="card diagnostic-card">
            <h3>
              <span>🔬</span> {diagnostics.issue}
            </h3>
            
            <div className="simple-summary">
              {diagnostics.summary}
            </div>

            {diagnostics.details && diagnostics.details.length > 0 && (
              <div className="simple-details">
                {diagnostics.details.map((detail, idx) => (
                  <div key={idx} className="detail-item">{detail}</div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Solutions Card - Simplified */}
        {solutions && (
          <div className="card solutions-card">
            <h3>
              <span>💡</span> Recommendations
            </h3>
            
            <div className="simple-summary">
              {solutions.message}
            </div>

            {solutions.actions && solutions.actions.length > 0 && (
              <div className="simple-actions">
                {solutions.actions.map((action, idx) => (
                  <div key={idx} className="action-item">
                    <span className="action-number">{idx + 1}</span>
                    <span className="action-text">{action}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Output Card */}
        {output && (
          <div className="card output-card">
            <p>{output}</p>
          </div>
        )}
      </div>
    </div>
  );
}

export default App;