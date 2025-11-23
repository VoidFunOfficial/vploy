import json

def strip_values(data):
    if isinstance(data, dict):
        return {k: strip_values(v) for k, v in data.items()}
    # 数组：递归处理每个元素（保留数组结构）
    elif isinstance(data, list):
        return [strip_values(item) for item in data]
    # 原始值：只保留 key，用 null 占位
    else:
        return None 


# 处理
original = json.load(open("r.json", "r", encoding="utf-8"))
skeleton = strip_values(original)
print(original)
# 写回新文件
with open("output.json", "w", encoding="utf-8") as f:
    json.dump(skeleton, f, ensure_ascii=False, indent=2)
