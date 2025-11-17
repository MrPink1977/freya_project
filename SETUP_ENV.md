# Environment Variables Setup

Keep your API keys and secrets safe using environment variables!

## 🔒 Why Use Environment Variables?

- **Security**: API keys stay out of git history
- **Flexibility**: Different settings per machine
- **Easy updates**: Change keys without editing config files
- **No conflicts**: Your local settings won't conflict with git pulls

---

## 🚀 Quick Setup

### Step 1: Copy the Example File

```bash
cp .env.example .env
```

On Windows:
```cmd
copy .env.example .env
```

### Step 2: Edit `.env` File

Open `.env` in your text editor and add your API key:

```bash
# ElevenLabs API Key
ELEVENLABS_API_KEY=sk_your_actual_api_key_here

# Optional: Choose a different voice
ELEVENLABS_VOICE_ID=21m00Tcm4TlvDq8ikWAM

# Optional: Choose model
ELEVENLABS_MODEL=eleven_turbo_v2_5
```

### Step 3: Run Freya

```bash
python main.py
```

Freya will automatically load your `.env` file! ✅

---

## 📋 Supported Variables

### ElevenLabs TTS

| Variable | Description | Default |
|----------|-------------|---------|
| `ELEVENLABS_API_KEY` | Your API key from elevenlabs.io | *(none)* |
| `ELEVENLABS_VOICE_ID` | Voice to use | `21m00Tcm4TlvDq8ikWAM` (Rachel) |
| `ELEVENLABS_MODEL` | Model to use | `eleven_turbo_v2_5` |

---

## 🔐 Security Best Practices

### ✅ DO:
- Use `.env` for local development
- Keep `.env` file private (never commit it!)
- Use `.env.example` as a template (safe to commit)
- Use different API keys for different machines

### ❌ DON'T:
- Commit `.env` to git (it's in `.gitignore`)
- Share your `.env` file
- Put API keys in `config/default.yaml`
- Hardcode secrets in code

---

## 🔄 How It Works

**Priority order (highest to lowest):**

1. **Environment variable** (from `.env` or system)
2. **Config file** (`config/default.yaml`)
3. **Default value**

Example:
```bash
# .env file
ELEVENLABS_API_KEY=sk_my_key_123

# config/default.yaml
elevenlabs:
  api_key: ""  # This is ignored if .env exists
```

Result: Uses `sk_my_key_123` from `.env` ✅

---

## 📁 File Overview

```
freya_project/
├── .env.example        # Template (safe to commit)
├── .env                # Your secrets (NEVER commit!)
├── .gitignore          # Ensures .env is not committed
└── config/
    └── default.yaml    # Public config (no secrets)
```

---

## 🔧 Troubleshooting

### "API key not configured"

1. Make sure `.env` exists in project root
2. Check that `ELEVENLABS_API_KEY=your_key` is set
3. No quotes needed around the value
4. Restart Freya after editing `.env`

### "Can't find .env file"

`.env` should be in the same folder as `main.py`:

```bash
# Check location
pwd  # Should show: /path/to/freya_project

# Create .env if missing
cp .env.example .env
```

### "Still using config file value"

Environment variables **override** config file. If you set:
- `.env`: `ELEVENLABS_API_KEY=sk_env_key`
- `config/default.yaml`: `api_key: "sk_config_key"`

Freya will use `sk_env_key` ✅

---

## 🎯 Example Workflows

### Development (Multiple Machines)

**Machine 1 (Desktop):**
```bash
# .env
ELEVENLABS_API_KEY=sk_desktop_key_123
ELEVENLABS_VOICE_ID=AZnzlk1XvdvUeBnXmlld  # Domi
```

**Machine 2 (Laptop):**
```bash
# .env
ELEVENLABS_API_KEY=sk_laptop_key_456
ELEVENLABS_VOICE_ID=21m00Tcm4TlvDq8ikWAM  # Rachel
```

Both use the same codebase, different settings! ✨

### Testing (Switch Between Voices)

```bash
# Test with Rachel
ELEVENLABS_VOICE_ID=21m00Tcm4TlvDq8ikWAM

# Test with Domi
ELEVENLABS_VOICE_ID=AZnzlk1XvdvUeBnXmlld

# Test with Bella
ELEVENLABS_VOICE_ID=EXAVITQu4vr4xnSDxMaL
```

Just change `.env` and restart Freya!

---

## 🌟 Advanced: System Environment Variables

Instead of `.env` file, you can use system environment variables:

**Windows (PowerShell):**
```powershell
$env:ELEVENLABS_API_KEY="sk_your_key"
python main.py
```

**Windows (CMD):**
```cmd
set ELEVENLABS_API_KEY=sk_your_key
python main.py
```

**Linux/Mac:**
```bash
export ELEVENLABS_API_KEY="sk_your_key"
python main.py
```

These override both `.env` file AND config file!

---

## ✅ Checklist

- [ ] Copy `.env.example` to `.env`
- [ ] Add your ElevenLabs API key to `.env`
- [ ] Verify `.env` is listed in `.gitignore`
- [ ] Test by running `python main.py`
- [ ] Never commit `.env` to git!

---

**Your API keys are now safe! 🔒**
