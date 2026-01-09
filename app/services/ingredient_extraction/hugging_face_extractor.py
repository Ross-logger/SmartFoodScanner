from transformers import AutoTokenizer, AutoModelForTokenClassification
import torch

# Load once (global / init section)
MODEL_NAME = "openfoodfacts/ingredient-detection"
tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
model = AutoModelForTokenClassification.from_pretrained(MODEL_NAME)
model.eval()

def extract_ingredients(ocr_text: str):
    """
    Extract ingredient spans from OCR text using OpenFoodFacts model.
    Handles SentencePiece tokenization correctly.
    """

    inputs = tokenizer(
        ocr_text,
        return_tensors="pt",
        truncation=True,
        max_length=512
    )

    with torch.no_grad():
        outputs = model(**inputs)

    predictions = outputs.logits.argmax(dim=-1)[0].tolist()
    tokens = tokenizer.convert_ids_to_tokens(inputs["input_ids"][0])
    labels = [model.config.id2label[p] for p in predictions]

    ingredients = []
    current = ""

    for token, label in zip(tokens, labels):

        # Skip special tokens
        if token in tokenizer.all_special_tokens:
            continue

        # SentencePiece: ▁ indicates new word
        if token.startswith("▁"):
            word = token[1:]
            new_word = True
        else:
            word = token
            new_word = False

        if label == "B-ING":
            if current:
                ingredients.append(current.strip())
            current = word

        elif label == "I-ING":
            if new_word:
                current += " " + word
            else:
                current += word

        else:  # label == O
            if current:
                ingredients.append(current.strip())
                current = ""

    if current:
        ingredients.append(current.strip())

    return ingredients
