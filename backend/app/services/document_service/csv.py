import csv
from typing import List

def generate_csv(data: List[List], output_path: str):
    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerows(data)
    return output_path

def generate_simple_csv(headers: List[str], rows: List[List], output_path: str):
    data = [headers] + rows
    return generate_csv(data, output_path)
