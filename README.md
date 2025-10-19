# 🔍 Network Monitor Agent

**AI-powered network monitoring with continuous packet capture**

---

## 📁 What's Here

```
crewai_starter/
├── monitor_only.py              ← Main script (start here!)
├── requirements.txt             ← Dependencies
│
└── agents/
    ├── __init__.py
    ├── monitor_agent.py         ← Monitor Agent (AI-powered)
    ├── continuous_pcap.py       ← Continuous packet capture manager
    └── shared_tools.py          ← Network diagnostic tools
```

**That's it!** Clean and simple. Other agents will be added one by one.

---

## 🚀 Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Make Sure Ollama is Running
```bash
ollama serve
ollama pull gemma3:1b
```

### 3. Run the Monitor
```bash
# Basic monitoring
python3 monitor_only.py

# WITH continuous packet capture (recommended!)
python3 monitor_only.py --continuous-capture
```

---

## 💻 Commands

```
status       - Quick network check
deep         - Deep scan with packet capture
monitor      - Start continuous monitoring loop

# Packet Capture (when --continuous-capture enabled):
pcap start   - Start background capture
pcap stop    - Stop capture
pcap status  - Show capture status
pcap analyze - Analyze latest captured file

devices      - Scan connected devices
bandwidth    - Measure bandwidth
help         - Show help
exit         - Quit
```

---

## 📦 Continuous Packet Capture

Runs this in the background:
```bash
tcpdump -i wlan0 -n -s 128 -w /tmp/pcap/cap-%F-%H%M%S.pcap -G 300 -W 12
```

- **Rotates** every 5 minutes
- **Keeps** 1 hour of history (12 files)
- **Saves** to `/tmp/pcap/`

---

## 🎯 Current Status

- ✅ **Monitor Agent** - Fully working with AI analysis
- ✅ **Continuous Packet Capture** - Background tcpdump with rotation
- ✅ **Network Tools** - Ping, DNS, signal, devices, bandwidth
- ⏳ **Other Agents** - Will be added one by one

---

## 📝 Requirements

- Python 3.8+
- Ollama with gemma3:1b model
- tcpdump (for packet capture)
- arp-scan (optional, for device scanning)

Install tools:
```bash
sudo apt-get install tcpdump arp-scan
```

---

## 🐛 Troubleshooting

**Ollama not running?**
```bash
ollama serve
```

**tcpdump not found?**
```bash
sudo apt-get install tcpdump
```

**Permission denied for packet capture?**
```bash
# Run with sudo
sudo python3 monitor_only.py --continuous-capture
```

---

## 🔧 Next Steps

1. **Test the Monitor Agent** - Make sure it's working perfectly
2. **Add Diagnostic Agent** - To analyze issues with LLM
3. **Add Solution Agent** - To propose fixes
4. **Add Execution Agent** - To apply fixes safely

One agent at a time, properly tested!

---

**Focus: Get monitoring solid first. Then add intelligence.** 🎯

