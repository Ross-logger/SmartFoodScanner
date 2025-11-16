"""
Test Script to Verify ML Installation and Setup
Run this after installing dependencies to ensure everything works
"""

import sys
import importlib


def test_imports():
    """Test if all required packages are installed"""
    print("Testing package imports...")
    print("-" * 60)
    
    required_packages = {
        'torch': 'PyTorch',
        'numpy': 'NumPy',
        'tqdm': 'tqdm',
        'symspellpy': 'SymSpellPy',
        'transformers': 'Transformers',
        'sklearn': 'scikit-learn',
    }
    
    failed = []
    
    for package, name in required_packages.items():
        try:
            mod = importlib.import_module(package)
            version = getattr(mod, '__version__', 'unknown')
            print(f"✓ {name:20s} - version {version}")
        except ImportError as e:
            print(f"✗ {name:20s} - NOT FOUND")
            failed.append(name)
    
    print("-" * 60)
    
    if failed:
        print(f"\n❌ Missing packages: {', '.join(failed)}")
        print("\nInstall with: pip install -r requirements.txt")
        return False
    else:
        print("\n✅ All packages installed successfully!")
        return True


def test_file_structure():
    """Test if all required files exist"""
    print("\nTesting file structure...")
    print("-" * 60)
    
    from pathlib import Path
    
    required_files = [
        'data_preparation.py',
        'generate_errors.py',
        'train_hybrid.py',
        'train_seq2seq.py',
        'train_transformer.py',
        'inference_hybrid.py',
        'inference_seq2seq.py',
        'inference_transformer.py',
        'fastapi_integration.py',
        'requirements.txt',
        'README.md',
    ]
    
    missing = []
    
    for file in required_files:
        if Path(file).exists():
            print(f"✓ {file}")
        else:
            print(f"✗ {file} - NOT FOUND")
            missing.append(file)
    
    print("-" * 60)
    
    if missing:
        print(f"\n❌ Missing files: {', '.join(missing)}")
        return False
    else:
        print("\n✅ All files present!")
        return True


def test_data_preparation():
    """Test data preparation functionality"""
    print("\nTesting data preparation...")
    print("-" * 60)
    
    try:
        from data_preparation import DataPreparation
        
        prep = DataPreparation(data_dir="test_data")
        ingredients = prep.get_common_ingredients()
        
        print(f"✓ Loaded {len(ingredients)} common ingredients")
        print(f"  Examples: {', '.join(ingredients[:5])}")
        
        # Cleanup
        import shutil
        from pathlib import Path
        test_dir = Path("test_data")
        if test_dir.exists():
            shutil.rmtree(test_dir)
        
        print("-" * 60)
        print("\n✅ Data preparation works!")
        return True
        
    except Exception as e:
        print(f"✗ Error: {e}")
        print("-" * 60)
        print("\n❌ Data preparation failed!")
        return False


def test_error_generation():
    """Test OCR error generation"""
    print("\nTesting error generation...")
    print("-" * 60)
    
    try:
        from generate_errors import OCRErrorGenerator
        
        generator = OCRErrorGenerator()
        
        test_cases = [
            "soy lecithin",
            "whey protein",
            "corn syrup"
        ]
        
        print("Testing error generation:")
        for text in test_cases:
            errors = generator.generate_multiple_errors(text, num_variants=3)
            print(f"  '{text}' →")
            for error in errors:
                print(f"    - {error}")
        
        print("-" * 60)
        print("\n✅ Error generation works!")
        return True
        
    except Exception as e:
        print(f"✗ Error: {e}")
        print("-" * 60)
        print("\n❌ Error generation failed!")
        return False


def test_pytorch():
    """Test PyTorch and GPU availability"""
    print("\nTesting PyTorch...")
    print("-" * 60)
    
    try:
        import torch
        
        print(f"PyTorch version: {torch.__version__}")
        print(f"CUDA available: {torch.cuda.is_available()}")
        
        if torch.cuda.is_available():
            print(f"CUDA version: {torch.version.cuda}")
            print(f"GPU device: {torch.cuda.get_device_name(0)}")
            print("✓ GPU available for training!")
        else:
            print("✓ CPU only (GPU not required for hybrid model)")
        
        # Test tensor operations
        x = torch.randn(3, 3)
        y = torch.randn(3, 3)
        z = torch.mm(x, y)
        print(f"✓ Tensor operations work")
        
        print("-" * 60)
        print("\n✅ PyTorch works!")
        return True
        
    except Exception as e:
        print(f"✗ Error: {e}")
        print("-" * 60)
        print("\n❌ PyTorch test failed!")
        return False


def print_next_steps():
    """Print next steps for the user"""
    print("\n" + "=" * 60)
    print("INSTALLATION TEST COMPLETE")
    print("=" * 60)
    print("\n📋 Next Steps:")
    print("\n1. Prepare training data:")
    print("   python data_preparation.py")
    print("\n2. Generate synthetic errors:")
    print("   python generate_errors.py")
    print("\n3. Train a model:")
    print("   python train_hybrid.py          # Recommended - fast, no GPU")
    print("   python train_seq2seq.py         # Good balance")
    print("   python train_transformer.py     # Best accuracy, needs GPU")
    print("\n4. Test the model:")
    print("   python inference_hybrid.py")
    print("\n5. Integrate into FastAPI:")
    print("   See fastapi_integration.py for examples")
    print("\n📚 Documentation:")
    print("   - README.md           - Overview")
    print("   - QUICKSTART.md       - Quick start guide")
    print("   - STRATEGIES.md       - Model comparison")
    print("   - ARCHITECTURE.md     - Technical details")
    print("   - COLAB_TRAINING.md   - GPU training guide")
    print("\n" + "=" * 60)


def main():
    """Run all tests"""
    print("=" * 60)
    print("ML OCR CORRECTION - INSTALLATION TEST")
    print("=" * 60)
    print()
    
    results = []
    
    # Run tests
    results.append(("Package imports", test_imports()))
    results.append(("File structure", test_file_structure()))
    results.append(("Data preparation", test_data_preparation()))
    results.append(("Error generation", test_error_generation()))
    results.append(("PyTorch", test_pytorch()))
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} - {name}")
    
    all_passed = all(result[1] for result in results)
    
    if all_passed:
        print("\n🎉 All tests passed! Ready to train models.")
        print_next_steps()
        return 0
    else:
        print("\n⚠️  Some tests failed. Please fix issues before proceeding.")
        print("\nCommon fixes:")
        print("  - Install dependencies: pip install -r requirements.txt")
        print("  - Check Python version: python --version (need 3.8+)")
        print("  - Verify file structure: ls -la")
        return 1


if __name__ == "__main__":
    sys.exit(main())

