"""
PDF 导出模块。
将生成的小说文本渲染为排版精美的 PDF 文件。
"""

import os
import re

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, PageBreak,
    Frame, PageTemplate, BaseDocTemplate,
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT

import config as cfg


# ============================================================
# 中文字体注册
# ============================================================

def _find_cjk_font() -> str:
    """
    自动查找系统中的中文字体。
    按优先级：宋体/SimSun > Noto Sans CJK > Source Han > 其他
    """
    search_paths = [
        # macOS
        "/System/Library/Fonts/PingFang.ttc",
        "/System/Library/Fonts/STHeiti Light.ttc",
        "/Library/Fonts/Arial Unicode.ttf",
        # macOS user fonts
        os.path.expanduser("~/Library/Fonts/NotoSansSC-Regular.otf"),
        os.path.expanduser("~/Library/Fonts/NotoSansCJKsc-Regular.otf"),
        os.path.expanduser("~/Library/Fonts/SourceHanSansSC-Regular.otf"),
        # Linux
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/noto-cjk/NotoSansCJK-Regular.ttc",
    ]

    for path in search_paths:
        if os.path.exists(path):
            return path

    # 如果都没有，尝试用 find 搜索
    import subprocess
    try:
        result = subprocess.run(
            ["find", "/", "-name", "*.ttf", "-o", "-name", "*.otf", "-o", "-name", "*.ttc"],
            capture_output=True, text=True, timeout=10,
        )
        for line in result.stdout.strip().split("\n"):
            if line and ("CJK" in line or "Noto" in line or "SourceHan" in line or "SimSun" in line or "SimHei" in line or "PingFang" in line or "STHeiti" in line or "wqy" in line or "WenQuanYi" in line):
                if os.path.exists(line):
                    return line
    except Exception:
        pass

    return None


def register_cjk_font() -> tuple:
    """注册中文字体，返回 (正文字体名, 标题字体名)"""
    font_path = _find_cjk_font()

    if font_path and os.path.exists(font_path):
        try:
            font_name = "CJKFont"
            pdfmetrics.registerFont(TTFont(font_name, font_path))
            pdfmetrics.registerFont(TTFont(font_name + "Bold", font_path))
            print(f"  ✅ 已注册中文字体: {font_path}")
            return font_name, font_name
        except Exception as e:
            print(f"  ⚠ 字体注册失败: {e}，使用默认字体")

    print(f"  ⚠ 未找到中文字体，使用 reportlab 默认字体（中文可能无法显示）")
    return "Helvetica", "Helvetica-Bold"


def export_novel_to_pdf(
    novel_text: str,
    chapter_outlines: list[dict],
    output_path: str = "outputs/novel.pdf",
    title: str = "长篇小说",
    author: str = "Grok 自动写作",
):
    """
    将完整小说文本渲染为 PDF。

    Args:
        novel_text: 完整小说文本
        chapter_outlines: 章节大纲列表（用于提取章节标题）
        output_path: PDF 输出路径
        title: 小说标题
        author: 作者
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    print(f"\n📄 正在生成 PDF...")

    body_font, title_font = register_cjk_font()

    # 构建文档
    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        leftMargin=cfg.PDF_MARGIN_MM * mm,
        rightMargin=cfg.PDF_MARGIN_MM * mm,
        topMargin=cfg.PDF_MARGIN_MM * mm,
        bottomMargin=cfg.PDF_MARGIN_MM * mm,
        title=title,
        author=author,
    )

    # 定义样式
    styles = getSampleStyleSheet()

    style_title = ParagraphStyle(
        "NovelTitle",
        parent=styles["Title"],
        fontName=title_font + "Bold" if title_font != "Helvetica" else title_font,
        fontSize=cfg.PDF_TITLE_FONT_SIZE,
        leading=cfg.PDF_TITLE_FONT_SIZE * 1.5,
        alignment=TA_CENTER,
        spaceAfter=20 * mm,
    )

    style_chapter = ParagraphStyle(
        "ChapterTitle",
        parent=styles["Heading1"],
        fontName=title_font + "Bold" if title_font != "Helvetica" else title_font,
        fontSize=cfg.PDF_CHAPTER_FONT_SIZE,
        leading=cfg.PDF_CHAPTER_FONT_SIZE * 1.5,
        alignment=TA_CENTER,
        spaceBefore=15 * mm,
        spaceAfter=10 * mm,
    )

    style_body = ParagraphStyle(
        "NovelBody",
        parent=styles["Normal"],
        fontName=body_font,
        fontSize=cfg.PDF_BODY_FONT_SIZE,
        leading=cfg.PDF_BODY_FONT_SIZE * cfg.PDF_LINE_SPACING,
        alignment=TA_JUSTIFY,
        spaceAfter=4 * mm,
        firstLineIndent=24,  # 首行缩进两字符
    )

    # 从章节大纲提取标题映射
    chapter_titles = {}
    for ch in chapter_outlines:
        ch_num = ch.get("chapter", 0)
        ch_title = ch.get("title", f"第{ch_num}章")
        chapter_titles[ch_num] = ch_title

    # 解析文本，构建 PDF 元素流
    elements = []

    # --- 封面 ---
    elements.append(Spacer(1, 60 * mm))
    elements.append(Paragraph(title, style_title))
    elements.append(Paragraph(f"作者：{author}", ParagraphStyle(
        "Author", parent=style_body, alignment=TA_CENTER, fontSize=14,
    )))
    elements.append(Spacer(1, 10 * mm))

    # 生成时间
    from datetime import datetime
    elements.append(Paragraph(
        f"生成于 {datetime.now().strftime('%Y年%m月%d日')}",
        ParagraphStyle("Date", parent=style_body, alignment=TA_CENTER, fontSize=10),
    ))

    elements.append(PageBreak())

    # --- 目录页 ---
    elements.append(Paragraph("目 录", style_chapter))
    elements.append(Spacer(1, 10 * mm))

    for ch in chapter_outlines:
        ch_num = ch.get("chapter", 0)
        ch_title = ch.get("title", f"第{ch_num}章")
        outline_preview = ch.get("outline", "")[:60] + "..." if len(ch.get("outline", "")) > 60 else ch.get("outline", "")
        elements.append(Paragraph(
            f"第{ch_num}章　{ch_title}",
            ParagraphStyle("TOC", parent=style_body, fontSize=11, spaceAfter=2 * mm),
        ))
        if outline_preview:
            elements.append(Paragraph(
                f"<i>{outline_preview}</i>",
                ParagraphStyle("TOCDesc", parent=style_body, fontSize=9, textColor="#666666", spaceAfter=4 * mm),
            ))

    elements.append(PageBreak())

    # --- 正文 ---
    lines = novel_text.strip().split("\n")

    for line in lines:
        stripped = line.strip()

        if not stripped:
            continue

        # 章节标题（格式：# 第X章 标题）
        chapter_match = re.match(r"^#\s*第(\d+)章\s*(.*)", stripped)
        if chapter_match:
            ch_num = int(chapter_match.group(1))
            ch_title = chapter_match.group(2) or chapter_titles.get(ch_num, f"第{ch_num}章")
            elements.append(PageBreak())
            elements.append(Spacer(1, 20 * mm))
            elements.append(Paragraph(
                f"第{ch_num}章",
                ParagraphStyle("ChapterNum", parent=style_chapter, fontSize=14, textColor="#888888", spaceAfter=2 * mm),
            ))
            elements.append(Paragraph(ch_title, style_chapter))
            continue

        # 普通段落 - 按双换行分段
        elements.append(Paragraph(stripped, style_body))

    # 尾页
    elements.append(Spacer(1, 20 * mm))
    elements.append(PageBreak())
    elements.append(Spacer(1, 60 * mm))
    elements.append(Paragraph("— 全文完 —", ParagraphStyle(
        "Ending", parent=style_body, alignment=TA_CENTER, fontSize=14, spaceBefore=20 * mm,
    )))

    # 生成 PDF
    doc.build(elements)

    file_size = os.path.getsize(output_path) / 1024
    print(f"  ✅ PDF 已生成: {output_path}")
    print(f"    大小: {file_size:.1f} KB")
    print(f"    页码: 自动分页")

    return output_path
