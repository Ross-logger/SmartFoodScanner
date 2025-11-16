# Google Colab Training Guide

Use Google Colab's free GPU to train the Transformer model!

## 📓 Quick Setup

### Step 1: Create New Colab Notebook

Go to [Google Colab](https://colab.research.google.com/) and create a new notebook.

### Step 2: Enable GPU

1. Click `Runtime` → `Change runtime type`
2. Select `GPU` (T4 or better)
3. Click `Save`

### Step 3: Upload Your Code

Run these cells in Colab:

```python
# Cell 1: Install dependencies
!pip install torch transformers sentencepiece symspellpy tqdm pandas scikit-learn python-Levenshtein

# Cell 2: Clone or upload your ML folder
# Option A: If your code is on GitHub
# !git clone https://github.com/yourusername/SmartFoodScanner.git
# %cd SmartFoodScanner/ML

# Option B: Upload files manually
from google.colab import files
import os

# Create ML directory
!mkdir -p ML
%cd ML

# Upload files (you can drag and drop)
print("Upload these files:")
print("- data_preparation.py")
print("- generate_errors.py")
print("- train_transformer.py")
```

### Step 4: Prepare Data

```python
# Cell 3: Prepare training data
!python data_preparation.py
!python generate_errors.py --train-size 15000 --test-size 2000
```

### Step 5: Train Model

```python
# Cell 4: Train Transformer model
!python train_transformer.py \
    --model t5-small \
    --epochs 5 \
    --batch-size 32 \
    --lr 5e-5
```

This will take approximately 1-2 hours.

### Step 6: Download Model

```python
# Cell 5: Download trained model
from google.colab import files
import shutil

# Create archive
!zip -r transformer_model.zip models/transformer/

# Download
files.download('transformer_model.zip')
```

---

## 📋 Complete Colab Notebook Code

Copy and paste this into a new Colab notebook:

```python
# ============================================================================
# CELL 1: Setup and Installation
# ============================================================================

print("Installing dependencies...")
!pip install -q torch transformers sentencepiece symspellpy tqdm pandas scikit-learn python-Levenshtein

print("\n✅ Dependencies installed!")

# ============================================================================
# CELL 2: Upload Training Scripts
# ============================================================================

# Create directory structure
!mkdir -p ML/data
!mkdir -p ML/models/transformer

# Upload files
from google.colab import files

print("Please upload these files:")
print("1. data_preparation.py")
print("2. generate_errors.py")
print("3. train_transformer.py")
print("\nDrag and drop them here:")

uploaded = files.upload()

# Move files to ML directory
import shutil
for filename in uploaded.keys():
    shutil.move(filename, f'ML/{filename}')

print("\n✅ Files uploaded!")

# ============================================================================
# CELL 3: Prepare Training Data
# ============================================================================

%cd ML

print("Preparing ingredient vocabulary...")
!python data_preparation.py

print("\nGenerating synthetic OCR errors...")
!python generate_errors.py --train-size 15000 --test-size 2000

print("\n✅ Data preparation complete!")

# Check data
!ls -lh data/

# ============================================================================
# CELL 4: Train Transformer Model
# ============================================================================

import torch
print(f"GPU Available: {torch.cuda.is_available()}")
print(f"GPU Name: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'None'}")

print("\nStarting training...")
print("This will take approximately 1-2 hours.\n")

!python train_transformer.py \
    --model t5-small \
    --epochs 5 \
    --batch-size 32 \
    --lr 5e-5 \
    --train data/train_pairs.txt \
    --test data/test_pairs.txt \
    --output models/transformer

print("\n✅ Training complete!")

# ============================================================================
# CELL 5: Test the Model
# ============================================================================

# Quick test
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
import torch

print("Loading model for testing...")
model_dir = "models/transformer"
tokenizer = AutoTokenizer.from_pretrained(model_dir)
model = AutoModelForSeq2SeqLM.from_pretrained(model_dir)
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
model.to(device)

# Test cases
test_cases = [
    "s0y lec1th1n",
    "whey pr0te1n",
    "m0n0s0d1um glUtamate",
    "natral flvors",
    "c0rn syrup"
]

print("\nTest Results:")
print("="*60)

for noisy in test_cases:
    input_text = f"correct ocr: {noisy}"
    input_ids = tokenizer(input_text, return_tensors='pt').input_ids.to(device)
    
    with torch.no_grad():
        outputs = model.generate(input_ids, max_length=128, num_beams=4)
    
    corrected = tokenizer.decode(outputs[0], skip_special_tokens=True)
    print(f"{noisy:30s} → {corrected}")

print("="*60)

# ============================================================================
# CELL 6: Download Model
# ============================================================================

print("Creating model archive...")
!cd .. && zip -r transformer_model.zip ML/models/transformer/

print("\nDownloading model...")
files.download('transformer_model.zip')

print("\n✅ Download complete!")
print("\nTo use the model:")
print("1. Extract transformer_model.zip")
print("2. Place in your ML/models/ directory")
print("3. Use: OcrCorrectorTransformer(model_dir='ML/models/transformer')")

# ============================================================================
# CELL 7: (Optional) Extended Training
# ============================================================================

# If you want to train longer for better accuracy
print("Extended training with more epochs...")

!python train_transformer.py \
    --model t5-small \
    --epochs 10 \
    --batch-size 32 \
    --lr 3e-5 \
    --train data/train_pairs.txt \
    --test data/test_pairs.txt \
    --output models/transformer_extended

# ============================================================================
# CELL 8: (Optional) Try Different Models
# ============================================================================

# Try ByT5 (byte-level, better for character errors)
print("Training ByT5 model...")

!python train_transformer.py \
    --model google/byt5-small \
    --epochs 5 \
    --batch-size 16 \
    --lr 5e-5 \
    --train data/train_pairs.txt \
    --test data/test_pairs.txt \
    --output models/byt5

# ============================================================================
# CELL 9: Compare Models
# ============================================================================

import torch
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

def test_model(model_dir, test_cases):
    """Test a model and return results"""
    tokenizer = AutoTokenizer.from_pretrained(model_dir)
    model = AutoModelForSeq2SeqLM.from_pretrained(model_dir)
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    model.to(device)
    
    results = []
    for noisy in test_cases:
        input_text = f"correct ocr: {noisy}"
        input_ids = tokenizer(input_text, return_tensors='pt').input_ids.to(device)
        
        with torch.no_grad():
            outputs = model.generate(input_ids, max_length=128, num_beams=4)
        
        corrected = tokenizer.decode(outputs[0], skip_special_tokens=True)
        results.append(corrected)
    
    return results

# Test cases
test_cases = [
    "s0y lec1th1n",
    "whey pr0te1n",
    "m0n0s0d1um glUtamate",
    "natral flvors",
]

print("Model Comparison:")
print("="*80)
print(f"{'Noisy Input':<30} {'T5-small':<25} {'ByT5':<25}")
print("="*80)

t5_results = test_model("models/transformer", test_cases)
byt5_results = test_model("models/byt5", test_cases)

for noisy, t5_corr, byt5_corr in zip(test_cases, t5_results, byt5_results):
    print(f"{noisy:<30} {t5_corr:<25} {byt5_corr:<25}")

print("="*80)
```

---

## 💡 Tips for Colab Training

1. **Session Timeout**: Colab sessions disconnect after ~90 minutes of inactivity
   - Keep the tab open
   - Click cells occasionally
   - Or use Colab Pro for longer sessions

2. **Save Checkpoints**: Model saves automatically during training
   - Checkpoints saved to `models/transformer/`
   - Download periodically if training long

3. **Monitor Training**: Watch the loss decrease
   - Should drop steadily
   - If loss plateaus, training is done

4. **Batch Size**: Adjust based on GPU memory
   - T4 GPU: batch_size=32
   - V100 GPU: batch_size=64
   - If OOM error: reduce batch_size

5. **Training Time**:
   - 10k samples, 5 epochs: ~1 hour
   - 20k samples, 10 epochs: ~3 hours

---

## 🔍 Monitoring Training

Add this to a cell to monitor GPU usage:

```python
# Monitor GPU
!nvidia-smi

# Check training progress
!tail -f logs/training.log  # If you set up logging
```

---

## 📊 After Training

Your model will be in `models/transformer/` with:
- `config.json` - Model configuration
- `pytorch_model.bin` - Model weights
- `tokenizer.json` - Tokenizer
- `config.json` - Training config

Total size: ~200-500 MB

---

## ⚠️ Troubleshooting

### "CUDA out of memory"
```python
# Reduce batch size
!python train_transformer.py --batch-size 16  # or 8
```

### "Session disconnected"
```python
# Resume from checkpoint
!python train_transformer.py --resume-from models/transformer/checkpoint-XXX
```

### "Model takes too long"
```python
# Reduce data or epochs
!python generate_errors.py --train-size 5000
!python train_transformer.py --epochs 3
```

---

## 📝 Alternative: Use Pretrained T5

If training takes too long, you can use pretrained T5 with minimal fine-tuning:

```python
# Just 1-2 epochs on small dataset
!python train_transformer.py \
    --model t5-small \
    --epochs 2 \
    --train-size 3000
```

This works surprisingly well for OCR correction!

