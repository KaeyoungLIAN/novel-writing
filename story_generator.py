"""
小说生成管线。
将角色设定和故事大纲逐步扩展为完整小说文本。
"""

import json
import os
import time
from typing import Optional

from grok_client import GrokClient
import config as cfg


class NovelGenerator:
    """小说生成器，管理从大纲到正文的完整管线"""

    def __init__(
        self,
        grok_client: GrokClient,
        characters: str,
        plot: str,
        style: str,
        output_dir: str = "outputs",
        save_intermediates: bool = True,
    ):
        self.client = grok_client
        self.characters = characters
        self.plot = plot
        self.style = style
        self.output_dir = output_dir
        self.save_intermediates = save_intermediates

        # 生成过程中的中间产物
        self.chapter_outlines: list[dict] = []       # 10 章大纲
        self.chapter_segments: dict[int, list] = {}  # 每章 10 段情节要点
        self.novel_segments: dict[str, str] = {}     # "章_段" → 正文
        self.full_novel: str = ""                    # 最终拼接文本

        os.makedirs(output_dir, exist_ok=True)

    def _save_json(self, filename: str, data):
        """保存中间产物为 JSON"""
        if not self.save_intermediates:
            return
        path = os.path.join(self.output_dir, filename)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"  💾 已保存: {path}")

    def _save_text(self, filename: str, text: str):
        """保存文本文件"""
        if not self.save_intermediates:
            return
        path = os.path.join(self.output_dir, filename)
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
        print(f"  💾 已保存: {path}")

    # ----------------------------------------------------------
    # 第 1 步：读取用户设定（由外部传入）
    # ----------------------------------------------------------
    # characters, plot, style 直接由 __init__ 接收

    def load_user_inputs(
        self,
        characters_path: str = "user_inputs/characters.txt",
        plot_path: str = "user_inputs/plot.txt",
        style_path: str = "user_inputs/style.txt",
    ):
        """从 txt 文件加载用户设定"""
        with open(characters_path, "r", encoding="utf-8") as f:
            self.characters = f.read()
        with open(plot_path, "r", encoding="utf-8") as f:
            self.plot = f.read()
        with open(style_path, "r", encoding="utf-8") as f:
            self.style = f.read()
        print("📖 已加载用户设定")

    # ----------------------------------------------------------
    # 第 2 步：从 chapters/ 目录加载章节大纲（用户自行编写）
    # ----------------------------------------------------------

    def load_chapters_from_dir(self, dir_path: str = "chapters") -> list[dict]:
        """从目录读取所有章节大纲 .txt 文件"""
        print("\n" + "=" * 60)
        print(f"📂 第 2 步：从 {dir_path} 加载章节大纲")
        print("=" * 60)

        files = sorted(
            f for f in os.listdir(dir_path) if f.endswith(".txt")
        )
        if not files:
            print(f"  ⚠ 目录 {dir_path} 中未找到 .txt 文件")
            self.chapter_outlines = []
            return self.chapter_outlines

        outlines: list[dict] = []
        for i, filename in enumerate(files, start=1):
            filepath = os.path.join(dir_path, filename)
            with open(filepath, "r", encoding="utf-8") as f:
                lines = f.read().strip().split("\n")

            title_line = lines[0].strip() if lines else ""
            outline_text = "\n".join(lines[1:]).strip() if len(lines) > 1 else ""

            # 提取标题（去掉 '# 第X章 ' 前缀）
            title = title_line
            for prefix in ("# ", "## "):
                if title_line.startswith(prefix):
                    title = title_line[len(prefix):]
                    break

            outlines.append({
                "chapter": i,
                "title": title,
                "outline": outline_text,
            })
            print(f"  📄 [{i}/{len(files)}] {title_line}")

        self.chapter_outlines = outlines
        self._save_json("chapter_outlines.json", self.chapter_outlines)
        print(f"\n✅ 已加载 {len(outlines)} 章大纲")
        return self.chapter_outlines

    # ----------------------------------------------------------
    # 第 3 步：每一章拆分为 10 个小段的情节要点
    # ----------------------------------------------------------

    def split_chapter_into_segments(self, chapter_idx: int) -> list[dict]:
        """将单章大纲拆分为 10 小段的情节要点"""
        ch = self.chapter_outlines[chapter_idx]
        ch_num = ch.get("chapter", chapter_idx + 1)
        ch_title = ch.get("title", f"第{ch_num}章")
        ch_outline = ch.get("outline", "")

        # 获取上一章结尾（如果有）
        prev_ending = ""
        if chapter_idx > 0:
            prev_ch = self.chapter_outlines[chapter_idx - 1]
            prev_ending = prev_ch.get("outline", "")[-100:]

        prompt = cfg.PROMPT_SPLIT_CHAPTER_INTO_SEGMENTS.format(
            chapter_number=ch_num,
            chapter_title=ch_title,
            chapter_outline=ch_outline,
            previous_chapter_ending=prev_ending,
        )

        messages = [
            {"role": "system", "content": cfg.SYSTEM_PROMPT_WRITER},
            {"role": "user", "content": prompt},
        ]

        result = self.client.chat_completion_json(messages)

        if isinstance(result, dict):
            for v in result.values():
                if isinstance(v, list):
                    segments = v
                    break
            else:
                segments = []
        else:
            segments = result

        # 验证段数
        if len(segments) != 10:
            print(f"  ⚠ 本章生成 {len(segments)} 段（期望 10），继续执行")

        self.chapter_segments[chapter_idx] = segments
        return segments

    def generate_all_segments(self):
        """为所有章节生成分段要点"""
        print("\n" + "=" * 60)
        print("📋 第 3 步：每章拆分为 10 小段要点")
        print("=" * 60)

        for idx in range(len(self.chapter_outlines)):
            ch = self.chapter_outlines[idx]
            ch_num = ch.get("chapter", idx + 1)
            ch_title = ch.get("title", f"第{ch_num}章")
            print(f"\n  📝 第 {ch_num} 章《{ch_title}》分段中...")

            segments = self.split_chapter_into_segments(idx)

            self._save_json(
                f"chapter_{ch_num}_segments.json", segments
            )

            print(f"    ✓ 已拆分为 {len(segments)} 段")

    # ----------------------------------------------------------
    # 第 4 步：逐段生成正文
    # ----------------------------------------------------------

    def write_segment(
        self,
        chapter_idx: int,
        segment_idx: int,
        previous_text: str = "",
    ) -> str:
        """生成单段正文（约 800 字）"""
        ch = self.chapter_outlines[chapter_idx]
        ch_num = ch.get("chapter", chapter_idx + 1)
        ch_title = ch.get("title", f"第{ch_num}章")
        segment = self.chapter_segments[chapter_idx][segment_idx]
        seg_num = segment.get("segment", segment_idx + 1)
        key_point = segment.get("key_point", "")

        prompt = cfg.PROMPT_WRITE_SEGMENT.format(
            chapter_number=ch_num,
            chapter_title=ch_title,
            segment_number=seg_num,
            segment_key_point=key_point,
            style=self.style,
            characters=self.characters,
            previous_segment_ending=previous_text[-500:] if previous_text else "(开头段，无上文)",
        )

        messages = [
            {"role": "system", "content": cfg.SYSTEM_PROMPT_WRITER},
            {"role": "user", "content": prompt},
        ]

        text = self.client.chat_completion(messages)

        return text

    def write_chapter(self, chapter_idx: int) -> str:
        """逐段生成单章所有 10 段正文"""
        ch = self.chapter_outlines[chapter_idx]
        ch_num = ch.get("chapter", chapter_idx + 1)
        ch_title = ch.get("title", f"第{ch_num}章")

        print(f"\n    ✍️  开始写作第 {ch_num} 章《{ch_title}》")

        chapter_text = f"\n\n# 第{ch_num}章 {ch_title}\n\n"
        previous_text = ""

        for seg_idx in range(len(self.chapter_segments[chapter_idx])):
            seg_num = seg_idx + 1
            print(f"      段 {seg_num}/10...", end=" ", flush=True)

            text = self.write_segment(
                chapter_idx, seg_idx, previous_text
            )

            # 保存到字典
            key = f"{ch_num}_{seg_num}"
            self.novel_segments[key] = text

            chapter_text += text + "\n\n"
            previous_text = text

            # 每段间小延迟，避免触达 API 限流
            if seg_idx < 9:
                time.sleep(0.5)

            print(f"✓ ({len(text)} 字)")

        # 保存本章
        self._save_text(f"chapter_{ch_num}_full.txt", chapter_text)

        print(f"    ✅ 第 {ch_num} 章完成 ({len(chapter_text)} 字)")

        return chapter_text

    def write_all_chapters(self):
        """逐章生成全部 10 章正文"""
        print("\n" + "=" * 60)
        print("✍️  第 4 步：逐段写作全部章节")
        print("=" * 60)

        for idx in range(len(self.chapter_outlines)):
            ch = self.chapter_outlines[idx]
            ch_num = ch.get("chapter", idx + 1)

            print(f"\n  📖 第 {ch_num}/{len(self.chapter_outlines)} 章")
            print(f"  {'─' * 40}")

            self.write_chapter(idx)

        # 第 5 步：拼接全文
        self.assemble_novel()

    # ----------------------------------------------------------
    # 第 5 步：拼接完整小说
    # ----------------------------------------------------------

    def assemble_novel(self) -> str:
        """将所有章节拼接为完整小说文本"""
        print("\n" + "=" * 60)
        print("📄 第 5 步：拼接完整小说")
        print("=" * 60)

        parts = [
            "=" * 60,
            "",
            f"  {self.plot.strip().split(chr(10))[0] if self.plot.strip() else '无题'}",
            "",
            "=" * 60,
            "",
        ]

        for idx in range(len(self.chapter_outlines)):
            ch = self.chapter_outlines[idx]
            ch_num = ch.get("chapter", idx + 1)
            ch_title = ch.get("title", f"第{ch_num}章")

            parts.append(f"# 第{ch_num}章 {ch_title}")
            parts.append("")

            segments = self.chapter_segments.get(idx, [])
            for seg_idx in range(len(segments)):
                key = f"{ch_num}_{seg_idx + 1}"
                text = self.novel_segments.get(key, "")
                if text:
                    parts.append(text)
                    parts.append("")

        self.full_novel = "\n".join(parts)

        self._save_text("novel_full.txt", self.full_novel)

        total_chars = len(self.full_novel)
        print(f"\n📄 小说全文已完成！")
        print(f"   总字数：约 {total_chars} 字")
        print(f"   总章节：{len(self.chapter_outlines)} 章")
        print(f"   总段数：{len(self.novel_segments)} 段")

        return self.full_novel
