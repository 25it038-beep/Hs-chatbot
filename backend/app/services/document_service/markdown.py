def generate_markdown(title: str, sections: list, output_path: str):
    lines = [f"# {title}", ""]
    for sec in sections:
        heading = sec.get('heading', '')
        content = sec.get('content', '')
        if heading:
            lines.append(f"## {heading}")
            lines.append("")
        lines.append(content)
        lines.append("")
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
    return output_path

def generate_simple_markdown(title: str, text: str, output_path: str):
    content = f"# {title}\n\n{text}"
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(content)
    return output_path
