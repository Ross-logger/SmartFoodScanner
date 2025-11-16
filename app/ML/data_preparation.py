"""
Data Preparation for OCR Error Correction
Prepares training data from various sources and creates ingredient vocabulary
"""

import os
import json
import random
from pathlib import Path
from typing import List, Set
import requests


class DataPreparation:
    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        
    def get_common_ingredients(self) -> List[str]:
        """Get a comprehensive list of common food ingredients"""
        
        # Common food ingredients database
        ingredients = [
            # Sugars and sweeteners
            "sugar", "glucose", "fructose", "sucrose", "maltose", "lactose",
            "high fructose corn syrup", "corn syrup", "dextrose", "maltodextrin",
            "honey", "molasses", "maple syrup", "agave nectar", "stevia",
            "aspartame", "sucralose", "saccharin", "xylitol", "erythritol",
            
            # Fats and oils
            "palm oil", "coconut oil", "sunflower oil", "canola oil", "soybean oil",
            "olive oil", "vegetable oil", "corn oil", "peanut oil", "sesame oil",
            "butter", "margarine", "shortening", "lard", "cocoa butter",
            
            # Proteins
            "whey protein", "soy protein", "pea protein", "casein", "gelatin",
            "collagen", "egg white", "milk protein", "wheat protein",
            
            # Flours and starches
            "wheat flour", "rice flour", "corn flour", "potato starch", "tapioca starch",
            "cornstarch", "modified food starch", "whole wheat flour", "almond flour",
            "oat flour", "coconut flour", "arrowroot powder",
            
            # Leavening agents
            "baking soda", "baking powder", "yeast", "sodium bicarbonate",
            "ammonium bicarbonate", "cream of tartar",
            
            # Emulsifiers
            "soy lecithin", "sunflower lecithin", "mono and diglycerides",
            "polysorbate 80", "sorbitan monostearate", "lecithin",
            
            # Preservatives
            "sodium benzoate", "potassium sorbate", "calcium propionate",
            "sodium nitrite", "sodium nitrate", "citric acid", "ascorbic acid",
            "tocopherols", "bht", "bha", "tbhq", "sulfur dioxide",
            "potassium metabisulfite", "sodium metabisulfite",
            
            # Thickeners and stabilizers
            "xanthan gum", "guar gum", "carrageenan", "pectin", "agar",
            "gellan gum", "locust bean gum", "cellulose gum", "gum arabic",
            "modified cellulose", "methylcellulose", "carboxymethyl cellulose",
            
            # Flavor enhancers
            "monosodium glutamate", "msg", "disodium inosinate", "disodium guanylate",
            "yeast extract", "autolyzed yeast extract", "hydrolyzed vegetable protein",
            
            # Flavors
            "natural flavors", "artificial flavors", "vanilla extract", "vanilla flavoring",
            "natural vanilla flavor", "artificial vanilla flavor", "smoke flavor",
            "caramel flavor", "butter flavor", "cheese flavor",
            
            # Colors
            "caramel color", "beta carotene", "annatto", "turmeric", "paprika extract",
            "red 40", "yellow 5", "yellow 6", "blue 1", "red 3", "titanium dioxide",
            "carmine", "cochineal extract", "beetroot red", "chlorophyll",
            
            # Acids
            "citric acid", "malic acid", "tartaric acid", "lactic acid", "acetic acid",
            "phosphoric acid", "fumaric acid", "adipic acid",
            
            # Salts and minerals
            "salt", "sodium chloride", "sea salt", "calcium carbonate", "calcium chloride",
            "potassium chloride", "magnesium chloride", "ferric phosphate",
            "zinc oxide", "calcium phosphate", "sodium phosphate",
            
            # Vitamins
            "vitamin a", "vitamin b1", "vitamin b2", "vitamin b3", "vitamin b6",
            "vitamin b12", "vitamin c", "vitamin d", "vitamin e", "vitamin k",
            "thiamine", "riboflavin", "niacin", "pyridoxine", "cobalamin",
            "ascorbic acid", "cholecalciferol", "tocopherol", "folic acid",
            "pantothenic acid", "biotin",
            
            # Dairy ingredients
            "milk", "cream", "buttermilk", "yogurt", "cheese", "whey", "skim milk",
            "whole milk", "condensed milk", "evaporated milk", "milk powder",
            "nonfat milk", "lactose", "milk solids", "milk fat",
            
            # Egg ingredients
            "eggs", "egg yolk", "egg white", "whole eggs", "dried egg",
            "egg powder", "albumin",
            
            # Grains and cereals
            "wheat", "oats", "barley", "rye", "rice", "corn", "quinoa", "millet",
            "sorghum", "buckwheat", "amaranth", "spelt", "kamut",
            
            # Nuts and seeds
            "almonds", "peanuts", "cashews", "walnuts", "pecans", "hazelnuts",
            "pistachios", "macadamia nuts", "sunflower seeds", "pumpkin seeds",
            "sesame seeds", "chia seeds", "flax seeds", "poppy seeds",
            
            # Chocolate and cocoa
            "cocoa", "cocoa powder", "chocolate", "dark chocolate", "milk chocolate",
            "white chocolate", "cocoa mass", "cocoa solids", "chocolate liquor",
            
            # Spices and herbs
            "pepper", "black pepper", "white pepper", "paprika", "cayenne pepper",
            "chili powder", "garlic powder", "onion powder", "cinnamon", "nutmeg",
            "ginger", "turmeric", "cumin", "coriander", "cardamom", "cloves",
            "oregano", "basil", "thyme", "rosemary", "sage", "parsley", "dill",
            
            # Fruits and vegetables (dried/processed)
            "tomato paste", "tomato powder", "dried tomatoes", "raisins",
            "dried cranberries", "dried apricots", "dried apples", "banana chips",
            "dried onion", "dried garlic", "potato flakes", "vegetable powder",
            
            # Alcohol
            "ethanol", "alcohol", "ethyl alcohol", "grain alcohol", "wine", "rum",
            
            # Other common ingredients
            "water", "carbonated water", "filtered water", "spring water",
            "coffee", "tea", "cocoa", "vanilla", "caramel", "salt", "pepper",
            "vinegar", "soy sauce", "fish sauce", "worcestershire sauce",
            "mustard", "ketchup", "mayonnaise", "enzymes", "cultures",
            "probiotics", "fiber", "inulin", "resistant starch", "cellulose",
        ]
        
        # Add variations and common misspellings
        expanded = set(ingredients)
        for ing in ingredients:
            # Add variations
            if "flavor" in ing:
                expanded.add(ing.replace("flavor", "flavour"))
            if "color" in ing:
                expanded.add(ing.replace("color", "colour"))
                
        return sorted(list(expanded))
    
    def fetch_openfoodfacts_ingredients(self, limit: int = 1000) -> Set[str]:
        """
        Fetch real ingredient lists from Open Food Facts
        Note: Requires internet connection
        """
        print("Fetching ingredients from Open Food Facts...")
        ingredients = set()
        
        try:
            # Search for products with ingredient lists
            url = "https://world.openfoodfacts.org/cgi/search.pl"
            params = {
                "action": "process",
                "json": 1,
                "page_size": 100,
                "page": 1,
                "fields": "ingredients_text"
            }
            
            for page in range(1, min(11, limit // 100 + 1)):  # Get up to 10 pages
                params["page"] = page
                response = requests.get(url, params=params, timeout=10)
                
                if response.status_code == 200:
                    data = response.json()
                    products = data.get("products", [])
                    
                    for product in products:
                        ingredients_text = product.get("ingredients_text", "")
                        if ingredients_text:
                            # Parse ingredients (split by comma, clean)
                            parts = ingredients_text.lower().split(",")
                            for part in parts:
                                # Clean and extract ingredient names
                                cleaned = part.strip()
                                # Remove percentages and parentheses content
                                cleaned = cleaned.split("(")[0].strip()
                                cleaned = cleaned.split("%")[0].strip()
                                if len(cleaned) > 2 and len(cleaned) < 50:
                                    ingredients.add(cleaned)
                    
                    print(f"Fetched page {page}, total unique ingredients: {len(ingredients)}")
                else:
                    print(f"Failed to fetch page {page}")
                    
        except Exception as e:
            print(f"Error fetching from Open Food Facts: {e}")
            print("Continuing with built-in ingredient list...")
        
        return ingredients
    
    def create_ingredient_vocabulary(self, include_openfoodfacts: bool = True):
        """Create comprehensive ingredient vocabulary"""
        print("Creating ingredient vocabulary...")
        
        # Start with common ingredients
        ingredients = set(self.get_common_ingredients())
        print(f"Loaded {len(ingredients)} common ingredients")
        
        # Optionally fetch from Open Food Facts
        if include_openfoodfacts:
            try:
                off_ingredients = self.fetch_openfoodfacts_ingredients(limit=1000)
                ingredients.update(off_ingredients)
                print(f"Added {len(off_ingredients)} ingredients from Open Food Facts")
            except:
                print("Skipping Open Food Facts (network error)")
        
        # Save to file
        output_file = self.data_dir / "ingredients.txt"
        with open(output_file, "w", encoding="utf-8") as f:
            for ing in sorted(ingredients):
                f.write(f"{ing}\n")
        
        print(f"Saved {len(ingredients)} ingredients to {output_file}")
        return list(ingredients)
    
    def load_ingredients(self) -> List[str]:
        """Load ingredient vocabulary from file"""
        file_path = self.data_dir / "ingredients.txt"
        if not file_path.exists():
            print("Ingredient file not found, creating...")
            return self.create_ingredient_vocabulary()
        
        with open(file_path, "r", encoding="utf-8") as f:
            ingredients = [line.strip() for line in f if line.strip()]
        
        print(f"Loaded {len(ingredients)} ingredients")
        return ingredients


def main():
    """Main function to prepare all data"""
    print("="*60)
    print("OCR Error Correction - Data Preparation")
    print("="*60)
    
    prep = DataPreparation()
    
    # Create ingredient vocabulary
    # Set include_openfoodfacts=False if you don't have internet
    ingredients = prep.create_ingredient_vocabulary(include_openfoodfacts=True)
    
    print("\n" + "="*60)
    print("Data preparation complete!")
    print("="*60)
    print(f"Total ingredients: {len(ingredients)}")
    print(f"Saved to: {prep.data_dir / 'ingredients.txt'}")
    print("\nNext step: Run generate_errors.py to create training pairs")


if __name__ == "__main__":
    main()

