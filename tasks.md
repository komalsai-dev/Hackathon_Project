# Commands and Tasks Reference (Windows PowerShell & Bash)

This project runs natively on Windows PowerShell using Python without requiring external tools.

### 1. Setup & Dependencies
```powershell
python -m pip install -r requirements.txt
```

### 2. Generate Dataset
```powershell
# Default Starter dataset (~5-10% scale for fast local testing):
python -m backend.generator.run --scale starter --seed 20261022

# Full benchmark volume (100 programs, 1,000 courses, 500 faculty, 20,000 student plans):
python -m backend.generator.run --scale full --seed 20261022
```
Or via the cross-platform runner:
```powershell
python run.py generate --scale starter
python run.py generate --scale full
```

### 3. Run Validation Suite
```powershell
python -m backend.validation.validate
# Or
python run.py validate
```

### 4. Run Pytest Test Suite
```powershell
python -m pytest backend/tests/ -v
# Or
python run.py test
```

### 5. Launch Optional API
```powershell
python -m backend.api.main
# Or
python run.py api
```

### 6. Clean Generated Files
```powershell
python run.py clean
```
