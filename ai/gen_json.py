import os
import yaml
import json
import re

def markdown_to_json(markdown_text):
    match = re.match(r'^---\n(.*?)\n---\n(.*)', markdown_text, re.DOTALL)
    if not match:
        return None  # 忽略不包含 YAML front matter 的文件
    yaml_part, body = match.groups()
    metadata = yaml.safe_load(yaml_part)
    if metadata["draft"]:
        return None
    content = body.strip()
    return {
        "title": metadata['title'],
        "date": metadata['date'].isoformat(),
        "categories": metadata['categories'],
        "content": content,
    }

def convert_all_md_to_json(input_dir, output_json_path):
    result = []
    for filename in os.listdir(input_dir):
        if not filename.endswith(".md"):
            continue
        filepath = os.path.join(input_dir, filename)
        with open(filepath, "r", encoding="utf-8") as f:
            md_text = f.read()
            data = markdown_to_json(md_text)
            if not data:
                continue
            data["filename"] = filename
            result.append(data)

    with open(output_json_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"✅ 转换完成，共 {len(result)} 篇文章写入 {output_json_path}")

if __name__ == "__main__":
    input_directory = "../content/cn/posts"
    output_file = "blogs.json"
    convert_all_md_to_json(input_directory, output_file)
