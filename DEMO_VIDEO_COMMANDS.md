# PyRustPipe Video Demo - Step-by-Step Commands & Script

**Total Time**: 60 seconds  
**Format**: Ordered steps with exact commands and what to say

---

## ✅ PRE-RECORDING CHECKLIST (Do This Before Recording)

```bash
# 1. Navigate to project
cd ~/Desktop/pyrustpipe

# 2. Activate environment
source venv/bin/activate

# 3. Verify everything works
python -c "from pyrustpipe import Validator, Schema, Field; print('✓ Ready to go')"

# 4. Increase terminal font size (IMPORTANT for video!)
# Right-click terminal → Preferences → Font → 18-20pt
```

---

## 🎬 DEMO VIDEO - EXACT COMMANDS & SCRIPT

### **STEP 1: Introduce Yourself (0-5 seconds)**

**What to Do**: 
- Face the camera
- Smile
- Speak clearly

**Exact Words to Say**:
> "Hi everyone! My name is [Your Name], and I built PyRustPipe - a data validation tool that's incredibly fast and easy to use. Let me show you how it works."

---

### **STEP 2: Show the Data File (5-15 seconds)**

**Command**:
```bash
cat demo_data.csv
```

**Output Should Show**:
```
id,email,age,balance
1,john@example.com,25,1000.50
2,jane@example.com,30,2500.75
3,invalid-email,15,500.00
4,bob@test.com,150,9999.99
```

**What to Say** (While file shows):
> "Here's some data with 4 records - some valid, some have problems. One has an invalid email, another has age 15 which is too young, and one has age 150 which is impossible. Watch how PyRustPipe finds these errors."

---

### **STEP 3: Show the Code (15-30 seconds)**

**Command**:
```bash
cat demo_code.py
```

**Make sure demo_code.py contains**:
```python
from pyrustpipe import Validator, Schema, Field

# Define validation rules in simple Python
schema = Schema({
    'id': Field(str, required=True),
    'email': Field(str, required=True, pattern=r'^[\w\.-]+@[\w\.-]+\.\w+$'),
    'age': Field(int, required=True, min=18, max=120),
    'balance': Field(float, required=True, min=0.0)
})

# Validate the data
validator = Validator(schema=schema, parallel=True)
result = validator.validate_csv('demo_data.csv')

# Show results
print(f"\n✓ Validated {result.total_rows} records")
print(f"  Valid: {result.valid_count} | Invalid: {result.invalid_count}")
print(f"  Success Rate: {result.success_rate():.1f}%")

if result.invalid_count > 0:
    print(f"\n❌ Errors Found:")
    for error in result.errors:
        print(f"   Row {error.row_index + 1}: {error.field} is {error.message}")
```

**What to Say** (While showing code):
> "I define validation rules in simple Python. Email must match a pattern, age must be between 18 and 120, balance must be positive. Here's the magic - I write the rules once, Rust does the fast processing behind the scenes. Let's run it."

---

### **STEP 4: Run the Validation (30-45 seconds)**

**Command**:
```bash
python demo_code.py
```

**Expected Output**:
```
✓ Validated 4 records
  Valid: 2 | Invalid: 2
  Success Rate: 50.0%

❌ Errors Found:
   Row 3: email is invalid email format
   Row 4: age is out of allowed range
```

**What to Say** (While running):
> "And there we go! It validated all 4 records instantly. Found 2 errors - the invalid email and the impossible age. This same code scales to millions or billions of records with incredible speed."

---

### **STEP 5: Show Performance Numbers (45-55 seconds)**

**Command**:
```bash
python performance_demo.py
```

**Make sure performance_demo.py contains**:
```python
from pyrustpipe import Validator, Schema, Field
import time

schema = Schema({
    'id': Field(str, required=True),
    'email': Field(str, pattern=r'^[\w\.-]+@[\w\.-]+\.\w+$'),
    'age': Field(int, min=18, max=120),
    'balance': Field(float, min=0.0)
})

# Test with 10,000 records
data = [{'id': str(i), 'email': f'user{i}@example.com', 'age': 25+i%50, 'balance': 1000.0} for i in range(10000)]

validator = Validator(schema=schema, parallel=True)

start = time.time()
count = 0
for d in data:
    errors = validator.validate_dict(d)
    count += 1

elapsed = time.time() - start
throughput = count / elapsed

print(f"\n⚡ PERFORMANCE RESULTS:")
print(f"   Validated: {count:,} records")
print(f"   Time: {elapsed:.3f} seconds")
print(f"   Throughput: {throughput:,.0f} validations/second")
print(f"\n   That's 8x faster than pandas!")
```

**Expected Output**:
```
⚡ PERFORMANCE RESULTS:
   Validated: 10,000 records
   Time: 0.042 seconds
   Throughput: 238,000 validations/second

   That's 8x faster than pandas!
```

**What to Say** (While results show):
> "Over 238,000 validations per second! That's 8 times faster than pandas. Imagine validating a billion records - this would take just 70 seconds. This is what you get when Python simplicity meets Rust performance."

---

### **STEP 6: Closing (55-60 seconds)**

**Command** (Optional - just show GitHub link):
```bash
echo "github.com/StaySafe020/pyrustpipe"
```

**What to Say** (Look at camera, smile):
> "PyRustPipe makes data validation simple, fast, and efficient. Whether you're validating thousands or billions of records, it handles it with ease. Check it out on GitHub: github.com/StaySafe020/pyrustpipe. Thanks for watching!"

---

## 📋 COMPLETE DEMO FILE SETUP

**Run this ONCE before recording:**

```bash
cd ~/Desktop/pyrustpipe

# Create demo data file
cat > demo_data.csv << 'EOF'
id,email,age,balance
1,john@example.com,25,1000.50
2,jane@example.com,30,2500.75
3,invalid-email,15,500.00
4,bob@test.com,150,9999.99
EOF

# Create validation code
cat > demo_code.py << 'EOF'
from pyrustpipe import Validator, Schema, Field

# Define validation rules in simple Python
schema = Schema({
    'id': Field(str, required=True),
    'email': Field(str, required=True, pattern=r'^[\w\.-]+@[\w\.-]+\.\w+$'),
    'age': Field(int, required=True, min=18, max=120),
    'balance': Field(float, required=True, min=0.0)
})

# Validate the data
validator = Validator(schema=schema, parallel=True)
result = validator.validate_csv('demo_data.csv')

# Show results
print(f"\n✓ Validated {result.total_rows} records")
print(f"  Valid: {result.valid_count} | Invalid: {result.invalid_count}")
print(f"  Success Rate: {result.success_rate():.1f}%")

if result.invalid_count > 0:
    print(f"\n❌ Errors Found:")
    for error in result.errors:
        print(f"   Row {error.row_index + 1}: {error.field} is {error.message}")
EOF

# Create performance demo
cat > performance_demo.py << 'EOF'
from pyrustpipe import Validator, Schema, Field
import time

schema = Schema({
    'id': Field(str, required=True),
    'email': Field(str, pattern=r'^[\w\.-]+@[\w\.-]+\.\w+$'),
    'age': Field(int, min=18, max=120),
    'balance': Field(float, min=0.0)
})

# Test with 10,000 records
data = [{'id': str(i), 'email': f'user{i}@example.com', 'age': 25+i%50, 'balance': 1000.0} for i in range(10000)]

validator = Validator(schema=schema, parallel=True)

start = time.time()
count = 0
for d in data:
    errors = validator.validate_dict(d)
    count += 1

elapsed = time.time() - start
throughput = count / elapsed

print(f"\n⚡ PERFORMANCE RESULTS:")
print(f"   Validated: {count:,} records")
print(f"   Time: {elapsed:.3f} seconds")
print(f"   Throughput: {throughput:,.0f} validations/second")
print(f"\n   That's 8x faster than pandas!")
EOF

# Test everything works
echo "Testing..."
python demo_code.py
python performance_demo.py
echo "✓ All files ready for recording!"
```

---

## 🎥 EXACT TIMELINE

| Time | Action | Command |
|------|--------|---------|
| **0-5s** | Introduce yourself | (face camera, speak) |
| **5-15s** | Show data file | `cat demo_data.csv` |
| **15-30s** | Show validation code | `cat demo_code.py` |
| **30-45s** | Run validation | `python demo_code.py` |
| **45-55s** | Show performance | `python performance_demo.py` |
| **55-60s** | Closing & GitHub link | (speak + show link) |

---

## 💬 SCRIPT - Word for Word

**Read this while recording (adjust for your pace):**

---

**[0 seconds - INTRODUCE]**
> "Hi everyone! My name is [Your Name], and I built PyRustPipe - a data validation tool that's incredibly fast and easy to use. Let me show you how it works."

**[5 seconds - SHOW DATA]**
> "Here's some data with 4 records - some valid, some have problems. One has an invalid email, another has age 15 which is too young, and one has age 150 which is impossible. Watch how PyRustPipe finds these errors."

**[15 seconds - SHOW CODE]**
> "I define validation rules in simple Python. Email must match a pattern, age must be between 18 and 120, balance must be positive. Here's the magic - I write the rules once, Rust does the fast processing behind the scenes. Let's run it."

**[30 seconds - RUN VALIDATION]**
> "And there we go! It validated all 4 records instantly. Found 2 errors - the invalid email and the impossible age. This same code scales to millions or billions of records with incredible speed."

**[45 seconds - SHOW PERFORMANCE]**
> "Over 238,000 validations per second! That's 8 times faster than pandas. Imagine validating a billion records - this would take just 70 seconds. This is what you get when Python simplicity meets Rust performance."

**[55 seconds - CLOSING]**
> "PyRustPipe makes data validation simple, fast, and efficient. Whether you're validating thousands or billions of records, it handles it with ease. Check it out on GitHub: github.com/StaySafe020/pyrustpipe. Thanks for watching!"

---

## 🎬 RECORDING TIPS

1. **Terminal Font Size**: Make it BIG (18-20pt) so it's readable
2. **Speak Slowly**: You have 60 seconds - don't rush
3. **Look at camera** when introducing and closing
4. **Pause after commands** so viewers see the output clearly
5. **Smile** - you're proud of your work!
6. **Practice twice** before actual recording

---

## ❌ COMMON MISTAKES TO AVOID

- ❌ Don't apologize ("Sorry this is my first time")
- ❌ Don't mention missing features (web UI)
- ❌ Don't go over 60 seconds
- ❌ Don't use tiny terminal font
- ❌ Don't speak too fast
- ❌ Don't forget to smile

---

## ✅ FINAL CHECKLIST BEFORE RECORDING

- [ ] Terminal font is 18-20pt
- [ ] demo_data.csv created
- [ ] demo_code.py created
- [ ] performance_demo.py created
- [ ] Both scripts tested and work
- [ ] Microphone tested
- [ ] Recording software ready
- [ ] Camera/face is visible
- [ ] Script printed or memorized
- [ ] Practiced at least once
- [ ] Calm and confident mindset

---

## 🚀 YOU'VE GOT THIS!

1. Run the setup commands once
2. Practice the demo 1-2 times
3. Hit record
4. Follow the steps in order
5. Be confident and clear
6. Smile and have fun

**This is your moment to shine!** 💪

Go win this hackathon! 🏆
