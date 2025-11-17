# Freya Quick Start - Test All Capabilities

## 🚀 Super Fast Start (2 minutes)

### 1. Test Tools Are Working
```bash
python demo_tools.py
```
**Expected:** All 11 tools execute successfully ✓

### 2. Run Comprehensive Test
```bash
python test_freya_comprehensive.py
```
**Expected:** 10/10 tool tests pass ✓

---

## 🎯 Start Freya (TEXT MODE - Easiest)

```bash
python main.py
```

**When prompted, choose TEXT mode** (just press Enter or type 't')

---

## 💬 Test Commands (Copy & Paste These!)

### Time & Date
```
What time is it?
What date is today?
```

### Calculator
```
Calculate 25 * 4
What is sqrt(144) + 10?
Calculate sin(pi/2)
```

### Files
```
List files in the current directory
List files in freya/tools
```

### System
```
Show me system information
```

### Web (if internet available)
```
Search for Python tutorials
```

### Memory
```
Remember that my favorite color is blue
What's my favorite color?
```

### Conversation
```
My name is [Your Name]
What did I just tell you?
```

### Calculator + Context
```
Calculate 10 plus 5
Now multiply that by 2
```

---

## 🎤 Voice Mode (Advanced)

```bash
python main.py
# Choose Voice mode (press 'v')
```

**Say after beep:**
- "Hey Freya, what time is it?"
- "Hey Freya, calculate two plus two"
- "Hey Freya, what date is today?"
- "Hey Freya, list files"

**Hotkeys:**
- **Ctrl+T**: Toggle between voice/text modes
- **Space**: Stop Freya from speaking

---

## ✅ Success Checklist

- [ ] demo_tools.py shows all 11 tools working
- [ ] test_freya_comprehensive.py passes (10/10 tools)
- [ ] Freya responds in text mode
- [ ] Time command works
- [ ] Calculator works
- [ ] List files works
- [ ] Memory persists (ask again in new session)

---

## 🐛 If Something Doesn't Work

### Ollama Not Running
```bash
ollama serve
```

### See Detailed Testing Guide
```bash
cat TESTING_GUIDE.md
# Or open in editor
```

### Check Logs
```bash
# Run in diagnostic mode
python main.py --startup-mode diagnostic
```

---

## 📊 What You're Testing

**11 Total Tools:**
1. ✅ get_current_time - Get time in any timezone
2. ✅ get_current_date - Get current date
3. ✅ calculate_time_until - Countdown to dates
4. ✅ calculator - Math expressions
5. ✅ list_files - Directory listings
6. ✅ read_file - Read text files
7. ✅ write_file - Write to files
8. ✅ web_search - DuckDuckGo search
9. ✅ web_scraper - Extract web content
10. ✅ system_info - OS/Python/disk info
11. ✅ execute_command - Safe shell commands

**Other Features:**
- Conversation context (multi-turn)
- Memory persistence
- Voice mode with wake word
- Camera integration (if hardware available)
- Web search integration
- Semantic memory retrieval

---

## 🎉 Next Steps

1. **Customize**: Edit `config/my_config.yaml`
2. **Add Tools**: Create custom tools in `freya/tools/`
3. **Camera**: Set up facial recognition
4. **Automation**: Add home automation tools

---

**Ready? Run `python demo_tools.py` to start!** 🚀
