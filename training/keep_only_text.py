import json
import argparse
import sys
from pathlib import Path

def extract_only_text(input_path: str, output_path: str):
    """
    Reads a JSONL file and writes a new JSONL file containing ONLY the "text" field
    for each record. Perfect for cleaning your Open Food Facts OCR dataset.
    """
    input_file = Path(input_path)
    output_file = Path(output_path)
    
    if not input_file.exists():
        print(f"Error: Input file not found: {input_file}")
        sys.exit(1)
    
    processed = 0
    skipped = 0
    
    with open(input_file, "r", encoding="utf-8") as infile, \
         open(output_file, "w", encoding="utf-8") as outfile:
        
        for line_number, line in enumerate(infile, 1):
            line = line.strip()
            if not line:
                continue  # skip empty lines
            
            try:
                data = json.loads(line)
                
                if "text" in data and data["text"] is not None:
                    # Keep ONLY the text field
                    clean_record = {"text": data["text"]}
                    outfile.write(json.dumps(clean_record, ensure_ascii=False) + "\n")
                    processed += 1
                else:
                    print(f"Warning: Line {line_number} has no 'text' field → skipped")
                    skipped += 1
                    
            except json.JSONDecodeError as e:
                print(f"Error: Invalid JSON on line {line_number}: {e}")
                skipped += 1
            except Exception as e:
                print(f"Unexpected error on line {line_number}: {e}")
                skipped += 1
    
    print(f"\n✅ Done!")
    print(f"   Processed: {processed} records")
    print(f"   Skipped:   {skipped} records")
    print(f"   Output saved to: {output_file.resolve()}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Extract ONLY the 'text' field from a JSONL file (ideal for OCR/ingredient datasets)"
    )
    parser.add_argument("input_file", help="Path to your input .jsonl file")
    parser.add_argument("output_file", help="Path to the output .jsonl file (only text kept)")
    
    args = parser.parse_args()
    
    extract_only_text(args.input_file, args.output_file)