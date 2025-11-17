# ElevenLabs TTS Setup Guide

Upgrade Freya's voice to **premium, ultra-realistic speech** using ElevenLabs!

## 🎯 What You Get

- **Natural, human-like speech** - Way better than Piper
- **Emotional expression** - Actual intonation and personality
- **Fast streaming** - Lower latency with turbo model
- **Multiple voices** - Choose from dozens of professional voices
- **Voice cloning** - Clone your own voice (premium plans)

## 📋 Prerequisites

1. **ElevenLabs Account** - Sign up at https://elevenlabs.io
2. **API Key** - Get it from your ElevenLabs account dashboard
3. **Credits** - Free tier gives 10,000 characters/month

## 🚀 Quick Setup

### Step 1: Install ElevenLabs

```bash
pip install elevenlabs>=1.0.0
```

### Step 2: Get Your API Key

1. Go to https://elevenlabs.io/app/speech-synthesis
2. Click your profile → Settings
3. Copy your API key

### Step 3: Configure Freya

Edit `config/default.yaml`:

```yaml
tts:
  engine: "elevenlabs"  # Changed from "piper"

  # ElevenLabs settings
  elevenlabs:
    api_key: "your_api_key_here"  # Paste your key here
    voice_id: "21m00Tcm4TlvDq8ikWAM"  # Rachel (default)
    model: "eleven_turbo_v2_5"  # Fast, low latency
```

### Step 4: Run Freya

```bash
python main.py
```

That's it! Freya will now sound AMAZING! 🎉

---

## 🎤 Voice Options

### Popular Pre-Made Voices

Edit the `voice_id` in config to choose:

**Female Voices:**
- `21m00Tcm4TlvDq8ikWAM` - **Rachel** (calm, clear) ⭐ DEFAULT
- `AZnzlk1XvdvUeBnXmlld` - **Domi** (strong, confident)
- `EXAVITQu4vr4xnSDxMaL` - **Bella** (soft, warm)
- `MF3mGyEYCl7XYWbV9V6O` - **Elli** (emotional, expressive)

**Male Voices:**
- `ErXwobaYiN019PkySvjV` - **Antoni** (well-rounded)
- `TxGEqnHWrfWFTfGW9XjX` - **Josh** (deep, authoritative)
- `VR6AewLTigWG4xSOukaG` - **Arnold** (crisp, professional)
- `pNInz6obpgDQGcFmaJgB` - **Adam** (deep narrator)
- `yoZ06aMxZJJ28mfd3POQ` - **Sam** (raspy, dynamic)

### Browse All Voices

Go to https://elevenlabs.io/app/voice-library to hear samples!

---

## ⚙️ Fine-Tuning Settings

### Model Selection

```yaml
model: "eleven_turbo_v2_5"  # Fast, lowest latency ⚡
# OR
model: "eleven_multilingual_v2"  # Higher quality, slower 🎯
```

**Recommendation:** Use `turbo_v2_5` for real-time conversations

### Voice Settings

Adjust in `config/default.yaml`:

```yaml
elevenlabs:
  stability: 0.5  # 0-1: Higher = more consistent
  similarity_boost: 0.75  # 0-1: Higher = more like original
  style: 0.0  # 0-1: Higher = more expressive
  use_speaker_boost: true  # Better clarity
```

**For Freya's personality:**
- `stability: 0.4-0.6` - Natural variation
- `similarity_boost: 0.7-0.8` - Clear voice
- `style: 0.2-0.4` - Some emotion

---

## 💰 Pricing & Credits

### Free Tier
- **10,000 characters/month**
- ~60 minutes of audio
- Access to all voices
- Good for testing!

### Starter ($5/month)
- **30,000 characters/month**
- ~3 hours of audio

### Creator ($22/month)
- **100,000 characters/month**
- ~10 hours of audio
- Voice cloning

**Freya Usage Estimate:**
- Average response: 50-100 characters
- 100 conversations = ~5,000-10,000 characters

---

## 🔧 Troubleshooting

### "ElevenLabs dependency missing"

```bash
pip install elevenlabs
```

### "API key not configured"

Make sure you:
1. Pasted your API key in `config/default.yaml`
2. Removed the quotes if you copied them
3. Restarted Freya

### "Quota exceeded"

You've used your monthly credits. Options:
- Wait for next month (free tier resets)
- Upgrade plan
- Switch back to Piper: `engine: "piper"`

### Audio choppy or cutting out

1. Check your internet connection
2. Try lowering quality: `model: "eleven_turbo_v2_5"`
3. Reduce `style` setting

---

## 🔄 Switching Back to Piper

Just change in `config/default.yaml`:

```yaml
tts:
  engine: "piper"  # Local, free, offline
```

No other changes needed!

---

## 🎨 Custom Voice Cloning

With Creator plan or higher:

1. Go to https://elevenlabs.io/app/voice-lab
2. Upload 1-5 minutes of clean audio
3. Create your custom voice
4. Copy the voice ID
5. Paste it in `config/default.yaml`

Now Freya sounds like YOU! 🤯

---

## 📊 Comparison

| Feature | Piper (Local) | ElevenLabs (Cloud) |
|---------|---------------|-------------------|
| Quality | ⭐⭐⭐ Good | ⭐⭐⭐⭐⭐ Excellent |
| Speed | ⚡⚡⚡⚡ Fast | ⚡⚡⚡⚡ Fast |
| Cost | Free | $0-22/month |
| Internet | Not needed | Required |
| Voices | Limited | 100+ options |
| Emotion | Basic | Natural |
| Latency | ~100ms | ~200-500ms |

---

## 💡 Pro Tips

1. **Test voices first** - Try different voice IDs to find your favorite
2. **Monitor usage** - Check your dashboard to track credits
3. **Adjust settings** - Fine-tune stability/style for better results
4. **Use turbo model** - Faster response times for conversations
5. **Save credits** - Use Piper for testing, ElevenLabs for final

---

**Enjoy premium AI speech! 🎉**

Need help? Check https://elevenlabs.io/docs
