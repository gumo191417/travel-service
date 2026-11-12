from pathlib import Path


def load_prompt(name: str) -> str:
    """
    根据模板名称加载 jinja2 提示词模板文本
    :param name: 模板文件名（不带后缀 .jinja2）
    :return: 模板原始字符串
    """
    file = Path(__file__).parent / "jinja2" / f"{name}.jinja2"
    return file.read_text(encoding="utf-8")


if __name__ == "__main__":
    # 测试加载提示词模板
    print(load_prompt("knowledge_respond"))