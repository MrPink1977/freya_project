# Fix Windows Python File Association

## The Problem
Windows is asking "How do you want to open this file?" when running Python scripts.

## Quick Fix (Manual Steps)

### Option 1: Right-Click Method
1. Find any `.py` file (like `main.py`)
2. **Right-click** on the file
3. Select **"Open with"** → **"Choose another app"**
4. Check the box **"Always use this app to open .py files"**
5. Select **"Python"** or **"Python Launcher"** from the list
   - If not listed, click "More apps" 
   - If still not there, click "Look for another app on this PC"
   - Navigate to: `C:\Windows\py.exe`
6. Click **OK**

### Option 2: Add .PY to PATHEXT (Run PowerShell as Administrator)

```powershell
# Run PowerShell as Administrator, then:
[Environment]::SetEnvironmentVariable("PATHEXT", "$env:PATHEXT;.PY;.PYW", "Machine")
```

Then restart your PowerShell terminal.

### Option 3: Registry Fix (Run as Administrator)

```powershell
# Run PowerShell as Administrator
cmd /c 'assoc .py=Python.File'
cmd /c 'ftype Python.File="C:\windows\py.exe" "%L" %*'
```

## Verification

After applying any fix, test with:
```powershell
python --version
# Should show Python version without asking how to open
```

## Current Issue
Your current PATHEXT is missing `.PY`:
```
Current: .COM;.EXE;.BAT;.CMD;.VBS;.VBE;.JS;.JSE;.WSF;.WSH;.MSC;.CPL
Needed:  .COM;.EXE;.BAT;.CMD;.VBS;.VBE;.JS;.JSE;.WSF;.WSH;.MSC;.CPL;.PY;.PYW
```

This is why Windows doesn't recognize `.py` files as executable.

## Recommended Solution
Use **Option 1** (right-click method) - it's the safest and doesn't require admin rights.
