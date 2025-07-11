import json
from pathlib import Path
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import normalize

def split_into_chunks(text, max_len=300):
    """将文本按句号切分为小段"""
    sentences = text.split("。")
    chunks, current = [], ""
    for sentence in sentences:
        if len(current) + len(sentence) < max_len:
            current += sentence + "。"
        else:
            if current:
                chunks.append(current.strip())
            current = sentence + "。"
    if current:
        chunks.append(current.strip())
    return chunks

def generate_embeddings(input_path, output_path):
    # 加载原始博客数据
    with open(input_path, "r", encoding="utf-8") as f:
        blogs = json.load(f)

    documents = []
    for blog in blogs:
        chunks = split_into_chunks(blog["content"])
        for chunk in chunks:
            documents.append({
                "title": blog["title"],
                "text": chunk
            })

    # 使用 TF-IDF 构建 embedding
    texts = [doc["text"] for doc in documents]
    vectorizer = TfidfVectorizer(max_features=512)
    X = vectorizer.fit_transform(texts)
    X = normalize(X)

    # 向文档中添加 embedding 向量
    vectors = X.toarray().tolist()
    for i, doc in enumerate(documents):
        doc["embedding"] = vectors[i]

    # 保存为 JSON 文件
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(documents, f, ensure_ascii=False, indent=2)

    print(f"✅ 成功生成 embedding 文件：{output_path}，共 {len(documents)} 条。")

if __name__ == "__main__":
    generate_embeddings("./blogs.json", "./embeddings.json")
