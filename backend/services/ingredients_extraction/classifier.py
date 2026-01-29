"""
ML-Based Ingredient Section Classifier
Classifies text lines as ingredient vs non-ingredient using machine learning.
"""

import re
import pickle
import os
from typing import List, Dict, Tuple, Optional
import numpy as np
from pathlib import Path

from backend.services.ingredients_extraction.config import IngredientExtractionConfig

# Try to import sklearn, but gracefully handle if not available
SKLEARN_AVAILABLE = False
try:
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.preprocessing import StandardScaler
    SKLEARN_AVAILABLE = True
except ImportError:
    pass


class IngredientSectionClassifier:
    """
    ML classifier to identify ingredient text lines.
    
    Uses feature engineering + Random Forest classifier to distinguish
    ingredient text from non-ingredient text (addresses, instructions, etc.).
    """
    
    def __init__(self, config: Optional[IngredientExtractionConfig] = None, model_path: Optional[str] = None):
        """
        Initialize classifier.
        
        Args:
            config: Configuration object
            model_path: Path to saved model file (optional)
        """
        self.config = config or IngredientExtractionConfig()
        self.model = None
        self.vectorizer = None
        self.scaler = None
        self.is_trained = False
        
        # Default model path
        if model_path is None:
            model_dir = Path(__file__).parent.parent.parent.parent / "app" / "ML" / "models" / "ingredient_classifier"
            model_dir.mkdir(parents=True, exist_ok=True)
            model_path = str(model_dir / "classifier.pkl")
        
        self.model_path = model_path
        
        # Load model if it exists
        if os.path.exists(model_path):
            self._load_model()
        elif SKLEARN_AVAILABLE:
            # Initialize untrained model (will need training)
            self._init_model()
    
    def _init_model(self):
        """Initialize untrained model components."""
        if not SKLEARN_AVAILABLE:
            return
        
        # Random Forest is good for this task - handles non-linear relationships
        self.model = RandomForestClassifier(
            n_estimators=100,
            max_depth=10,
            random_state=42,
            class_weight='balanced'  # Handle imbalanced data
        )
        
        # TF-IDF vectorizer for text features
        self.vectorizer = TfidfVectorizer(
            max_features=50,  # Keep top 50 features
            ngram_range=(1, 2),  # Unigrams and bigrams
            stop_words='english'
        )
        
        # Scaler for numerical features
        self.scaler = StandardScaler()
    
    def _load_model(self):
        """Load trained model from disk."""
        if not SKLEARN_AVAILABLE:
            print("⚠️  Cannot load model: scikit-learn not available")
            return
        
        try:
            with open(self.model_path, 'rb') as f:
                data = pickle.load(f)
                self.model = data['model']
                self.vectorizer = data['vectorizer']
                self.scaler = data['scaler']
                self.is_trained = True
            print(f"✅ Loaded classifier model from {self.model_path}")
        except Exception as e:
            print(f"⚠️  Failed to load model: {e}. Will use rule-based fallback.")
            self._init_model()
    
    def _save_model(self):
        """Save trained model to disk."""
        if not self.is_trained or self.model is None:
            return
        
        try:
            os.makedirs(os.path.dirname(self.model_path), exist_ok=True)
            with open(self.model_path, 'wb') as f:
                pickle.dump({
                    'model': self.model,
                    'vectorizer': self.vectorizer,
                    'scaler': self.scaler
                }, f)
            print(f"✅ Saved classifier model to {self.model_path}")
        except Exception as e:
            print(f"⚠️  Failed to save model: {e}")
    
    def extract_features(self, text: str, context: Optional[Dict] = None) -> np.ndarray:
        """
        Extract features from a text line.
        
        Features include:
        - Text length and word count
        - Punctuation patterns (commas, semicolons)
        - Ingredient keywords presence
        - Non-ingredient keywords presence
        - Character patterns (numbers, letters ratio)
        - Position in document (if context provided)
        
        Args:
            text: Text line to extract features from
            context: Optional context dict with position info
            
        Returns:
            Feature vector as numpy array
        """
        text_lower = text.lower().strip()
        words = text.split()
        
        # Feature 1-2: Length features
        text_length = len(text)
        word_count = len(words)
        
        # Feature 3-5: Punctuation features
        comma_count = text.count(',')
        semicolon_count = text.count(';')
        period_count = text.count('.')
        
        # Feature 6-7: Separator patterns
        has_and = bool(re.search(r'\band\b', text_lower))
        has_ampersand = '&' in text
        
        # Feature 8-10: Ingredient keyword presence
        ingredient_keywords = ['flour', 'sugar', 'salt', 'oil', 'powder', 'extract',
                              'lecithin', 'starch', 'gum', 'acid', 'milk', 'cream',
                              'butter', 'egg', 'wheat', 'soy', 'corn', 'rice']
        ingredient_keyword_count = sum(1 for kw in ingredient_keywords if kw in text_lower)
        has_ingredient_keyword = ingredient_keyword_count > 0
        
        # Feature 11-13: Non-ingredient keyword presence
        non_ingredient_keywords = ['address', 'contact', 'phone', 'email', 'website',
                                   'manufactured', 'prepared', 'store', 'keep',
                                   'expir', 'best before', 'net weight', 'product of']
        non_ingredient_keyword_count = sum(1 for kw in non_ingredient_keywords if kw in text_lower)
        has_non_ingredient_keyword = non_ingredient_keyword_count > 0
        
        # Feature 14-15: Pattern matches
        matches_start_pattern = any(re.search(p, text_lower) for p in self.config.START_PATTERNS)
        matches_stop_pattern = any(re.search(p, text_lower) for p in self.config.STOP_PATTERNS)
        
        # Feature 16-17: Character patterns
        digit_count = sum(c.isdigit() for c in text)
        letter_count = sum(c.isalpha() for c in text)
        digit_ratio = digit_count / max(text_length, 1)
        letter_ratio = letter_count / max(text_length, 1)
        
        # Feature 18-19: E-number patterns (common in ingredients)
        has_e_number = bool(re.search(r'\be\d+\b', text_lower))
        has_d_number = bool(re.search(r'\bd\d+\b', text_lower))
        
        # Feature 20: Parentheses (often contain percentages in ingredients)
        has_parentheses = '(' in text and ')' in text
        
        # Feature 21-22: Position features (if context provided)
        line_position = context.get('line_index', 0) / max(context.get('total_lines', 1), 1) if context else 0.5
        is_early_line = line_position < 0.3
        
        # Feature 23-24: Word length patterns
        avg_word_length = np.mean([len(w) for w in words]) if words else 0
        has_long_words = any(len(w) > 10 for w in words)
        
        # Feature 25: Starts with number (common in ingredients: "2 cups flour")
        starts_with_number = bool(re.match(r'^\d+', text.strip()))
        
        # Combine all features into array
        features = np.array([
            text_length,
            word_count,
            comma_count,
            semicolon_count,
            period_count,
            int(has_and),
            int(has_ampersand),
            ingredient_keyword_count,
            int(has_ingredient_keyword),
            non_ingredient_keyword_count,
            int(has_non_ingredient_keyword),
            int(matches_start_pattern),
            int(matches_stop_pattern),
            digit_ratio,
            letter_ratio,
            int(has_e_number),
            int(has_d_number),
            int(has_parentheses),
            line_position,
            int(is_early_line),
            avg_word_length,
            int(has_long_words),
            int(starts_with_number),
        ])
        
        return features
    
    def classify_line(self, text: str, context: Optional[Dict] = None, threshold: float = 0.5) -> Tuple[bool, float]:
        """
        Classify if a text line is ingredient text.
        
        Args:
            text: Text line to classify
            context: Optional context dict with position info
            threshold: Confidence threshold (0.0 to 1.0)
            
        Returns:
            Tuple of (is_ingredient: bool, confidence: float)
        """
        if not text or not text.strip():
            return False, 0.0
        
        # If model not trained, use rule-based fallback
        if not self.is_trained or self.model is None:
            return self._rule_based_classify(text, context)
        
        try:
            # Extract features
            numerical_features = self.extract_features(text, context)
            
            # Get TF-IDF features from text
            text_features = self.vectorizer.transform([text]).toarray()[0]
            
            # Combine features
            all_features = np.concatenate([numerical_features, text_features])
            
            # Scale features
            all_features_scaled = self.scaler.transform([all_features])
            
            # Predict
            prediction = self.model.predict_proba(all_features_scaled)[0]
            confidence = prediction[1]  # Probability of being ingredient
            is_ingredient = confidence >= threshold
            
            return is_ingredient, float(confidence)
        
        except Exception as e:
            # Fallback to rule-based if ML fails
            print(f"⚠️  ML classification failed: {e}. Using rule-based fallback.")
            return self._rule_based_classify(text, context)
    
    def _rule_based_classify(self, text: str, context: Optional[Dict] = None) -> Tuple[bool, float]:
        """
        Rule-based fallback classification.
        Used when ML model is not available or not trained.
        
        Args:
            text: Text line to classify
            context: Optional context dict
            
        Returns:
            Tuple of (is_ingredient: bool, confidence: float)
        """
        text_lower = text.lower().strip()
        
        # Strong indicators of non-ingredient text
        non_ingredient_patterns = [
            r'\b(address|contact|phone|email|website|www\.|http)',
            r'\b(manufactured|prepared|packaged|distributed|imported)',
            r'\b(store|keep|refrigerated|frozen|expir|best before)',
            r'\b(net weight|product of|made in|country of origin)',
        ]
        
        for pattern in non_ingredient_patterns:
            if re.search(pattern, text_lower):
                return False, 0.1
        
        # Strong indicators of ingredient text
        ingredient_patterns = [
            r'\b(flour|sugar|salt|oil|powder|extract|lecithin|starch)',
            r'\b(milk|cream|butter|cheese|egg|wheat|soy|corn)',
            r'\be\d+\b',  # E-numbers
            r'[,;]',  # Common separators
        ]
        
        ingredient_score = sum(1 for pattern in ingredient_patterns if re.search(pattern, text_lower))
        
        # If has ingredient keywords and no non-ingredient keywords, likely ingredient
        if ingredient_score >= 1 and len(text) > 3:
            confidence = min(0.7 + (ingredient_score * 0.1), 0.95)
            return True, confidence
        
        # Default: uncertain
        return False, 0.3
    
    def classify_lines(self, lines: List[str], threshold: float = 0.5) -> List[Tuple[str, bool, float]]:
        """
        Classify multiple text lines.
        
        Args:
            lines: List of text lines
            threshold: Confidence threshold
            
        Returns:
            List of tuples: (text, is_ingredient, confidence)
        """
        results = []
        total_lines = len(lines)
        
        for i, line in enumerate(lines):
            context = {
                'line_index': i,
                'total_lines': total_lines
            }
            is_ingredient, confidence = self.classify_line(line, context, threshold)
            results.append((line, is_ingredient, confidence))
        
        return results
    
    def train(self, training_data: List[Tuple[str, bool]]):
        """
        Train the classifier on labeled data.
        
        Args:
            training_data: List of (text, is_ingredient) tuples
        """
        if not SKLEARN_AVAILABLE:
            print("⚠️  Cannot train: scikit-learn not available")
            return
        
        if not training_data:
            print("⚠️  No training data provided")
            return
        
        print(f"📊 Training classifier on {len(training_data)} samples...")
        
        # Separate features and labels
        texts = [item[0] for item in training_data]
        labels = [int(item[1]) for item in training_data]
        
        # Extract features
        print("  Extracting features...")
        numerical_features = np.array([self.extract_features(text) for text in texts])
        
        # Fit TF-IDF vectorizer
        print("  Fitting TF-IDF vectorizer...")
        text_features = self.vectorizer.fit_transform(texts).toarray()
        
        # Combine features
        all_features = np.concatenate([numerical_features, text_features], axis=1)
        
        # Scale features
        print("  Scaling features...")
        all_features_scaled = self.scaler.fit_transform(all_features)
        
        # Train model
        print("  Training Random Forest classifier...")
        self.model.fit(all_features_scaled, labels)
        
        self.is_trained = True
        
        # Evaluate
        predictions = self.model.predict(all_features_scaled)
        accuracy = np.mean(predictions == labels)
        print(f"✅ Training complete! Accuracy: {accuracy:.2%}")
        
        # Save model
        self._save_model()
