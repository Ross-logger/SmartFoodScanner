"""
Inference for Transformer OCR Correction Model (T5)
Highest accuracy, requires more compute
"""

import json
from pathlib import Path
from typing import List, Dict
import torch
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer


class OcrCorrectorTransformer:
    """
    Transformer-based OCR Corrector (T5)
    
    Usage:
        corrector = OcrCorrectorTransformer()
        corrected = corrector.correct("s0y lec1th1n")
        # Returns: "soy lecithin"
    """
    
    def __init__(self, model_dir: str = "models/transformer", device: str = None):
        """
        Initialize Transformer corrector
        
        Args:
            model_dir: Path to trained model directory
            device: Device to use (cuda/cpu)
        """
        self.model_dir = Path(model_dir)
        
        if device is None:
            self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        else:
            self.device = device
        
        # Load model
        if self.model_dir.exists():
            self._load_model()
        else:
            print(f"Warning: Model directory {model_dir} not found.")
            print("Run train_transformer.py first to train the model.")
            self.model = None
            self.tokenizer = None
    
    def _load_model(self):
        """Load trained model"""
        
        # Load config
        config_path = self.model_dir / "config.json"
        if config_path.exists():
            with open(config_path, 'r') as f:
                self.config = json.load(f)
        else:
            self.config = {'max_length': 128}
        
        # Load model and tokenizer
        try:
            self.tokenizer = AutoTokenizer.from_pretrained(str(self.model_dir))
            self.model = AutoModelForSeq2SeqLM.from_pretrained(str(self.model_dir))
            self.model.to(self.device)
            self.model.eval()
            
            print(f"Model loaded from {self.model_dir}")
            print(f"Using device: {self.device}")
        except Exception as e:
            print(f"Error loading model: {e}")
            self.model = None
            self.tokenizer = None
    
    def correct(
        self, 
        text: str, 
        max_length: int = None,
        num_beams: int = 4,
        temperature: float = 1.0
    ) -> str:
        """
        Correct OCR errors in text
        
        Args:
            text: Noisy text to correct
            max_length: Maximum output length (default from config)
            num_beams: Number of beams for beam search
            temperature: Sampling temperature
            
        Returns:
            Corrected text
        """
        if not text or self.model is None:
            return text
        
        if max_length is None:
            max_length = self.config.get('max_length', 128)
        
        # Add task prefix
        input_text = f"correct ocr: {text}"
        
        # Tokenize
        input_ids = self.tokenizer(
            input_text,
            return_tensors='pt',
            max_length=max_length,
            truncation=True
        ).input_ids.to(self.device)
        
        # Generate
        with torch.no_grad():
            outputs = self.model.generate(
                input_ids,
                max_length=max_length,
                num_beams=num_beams,
                temperature=temperature,
                early_stopping=True
            )
        
        # Decode
        corrected = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
        
        return corrected
    
    def correct_batch(
        self, 
        texts: List[str], 
        max_length: int = None,
        num_beams: int = 4,
        batch_size: int = 8
    ) -> List[str]:
        """
        Correct multiple texts efficiently
        
        Args:
            texts: List of noisy texts
            max_length: Maximum output length
            num_beams: Number of beams for beam search
            batch_size: Batch size for processing
            
        Returns:
            List of corrected texts
        """
        if not texts or self.model is None:
            return texts
        
        if max_length is None:
            max_length = self.config.get('max_length', 128)
        
        corrected_texts = []
        
        # Process in batches
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i+batch_size]
            
            # Add task prefix
            input_texts = [f"correct ocr: {text}" for text in batch]
            
            # Tokenize
            inputs = self.tokenizer(
                input_texts,
                return_tensors='pt',
                max_length=max_length,
                padding=True,
                truncation=True
            ).to(self.device)
            
            # Generate
            with torch.no_grad():
                outputs = self.model.generate(
                    **inputs,
                    max_length=max_length,
                    num_beams=num_beams,
                    early_stopping=True
                )
            
            # Decode
            batch_corrected = self.tokenizer.batch_decode(outputs, skip_special_tokens=True)
            corrected_texts.extend(batch_corrected)
        
        return corrected_texts
    
    def correct_with_details(
        self, 
        text: str,
        max_length: int = None,
        num_beams: int = 4
    ) -> Dict:
        """
        Correct text and return detailed information
        
        Args:
            text: Noisy text
            max_length: Maximum output length
            num_beams: Number of beams for beam search
            
        Returns:
            Dict with corrected text and details
        """
        corrected = self.correct(text, max_length, num_beams)
        
        return {
            'original': text,
            'corrected': corrected,
            'model': 'transformer-t5',
            'changed': corrected.lower() != text.lower(),
            'device': self.device
        }
    
    def correct_with_alternatives(
        self,
        text: str,
        max_length: int = None,
        num_return_sequences: int = 3,
        num_beams: int = 5
    ) -> List[str]:
        """
        Get multiple correction alternatives
        
        Args:
            text: Noisy text
            max_length: Maximum output length
            num_return_sequences: Number of alternatives to return
            num_beams: Number of beams (must be >= num_return_sequences)
            
        Returns:
            List of alternative corrections
        """
        if not text or self.model is None:
            return [text]
        
        if max_length is None:
            max_length = self.config.get('max_length', 128)
        
        # Ensure num_beams >= num_return_sequences
        num_beams = max(num_beams, num_return_sequences)
        
        # Add task prefix
        input_text = f"correct ocr: {text}"
        
        # Tokenize
        input_ids = self.tokenizer(
            input_text,
            return_tensors='pt',
            max_length=max_length,
            truncation=True
        ).input_ids.to(self.device)
        
        # Generate multiple sequences
        with torch.no_grad():
            outputs = self.model.generate(
                input_ids,
                max_length=max_length,
                num_beams=num_beams,
                num_return_sequences=num_return_sequences,
                early_stopping=True
            )
        
        # Decode all
        alternatives = []
        for output in outputs:
            corrected = self.tokenizer.decode(output, skip_special_tokens=True)
            alternatives.append(corrected)
        
        return alternatives


def demo():
    """Demo of the Transformer OCR corrector"""
    print("="*60)
    print("Transformer (T5) OCR Corrector - Demo")
    print("="*60)
    
    corrector = OcrCorrectorTransformer()
    
    if corrector.model is None:
        print("\nModel not found. Please train the model first:")
        print("  python train_transformer.py")
        print("\nNote: This requires GPU. You can use Google Colab.")
        return
    
    # Test examples
    test_cases = [
        "s0y lec1th1n",
        "whey pr0te1n",
        "m0n0s0d1um glUtamate",
        "natral flvors",
        "c0rn syrup",
        "v1tam1n c",
        "sod1um benzoate",
        "art1f1c1al fl4vors",
        "palm o1l",
        "h1gh fruct0se c0rn syrup"
    ]
    
    print("\nTest Cases:")
    print("-"*60)
    
    for noisy in test_cases:
        result = corrector.correct_with_details(noisy)
        
        print(f"\nOriginal:  {result['original']}")
        print(f"Corrected: {result['corrected']}")
        print(f"Changed:   {result['changed']}")
    
    # Demo alternatives
    print("\n" + "="*60)
    print("Alternative Corrections:")
    print("="*60)
    
    test_text = "s0y lec1th1n"
    alternatives = corrector.correct_with_alternatives(test_text, num_return_sequences=3)
    
    print(f"\nOriginal: {test_text}")
    print("Alternatives:")
    for i, alt in enumerate(alternatives, 1):
        print(f"  {i}. {alt}")
    
    print("\n" + "="*60)


if __name__ == "__main__":
    demo()

