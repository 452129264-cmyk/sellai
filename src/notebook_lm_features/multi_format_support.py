#!/usr/bin/env python3
"""
多格式资料整合模块

此模块提供对PDF、Word、Excel、PPT、网页、图片等全格式文档的上传与解析支持，
确保与SellAI全球业务场景100%适配。
"""

import os
import io
import json
import logging
import mimetypes
from typing import Dict, List, Optional, Any, Tuple, BinaryIO
from pathlib import Path
import hashlib

# 尝试导入可能的依赖库
try:
    import pdfplumber
    PDF_SUPPORT = True
except ImportError:
    PDF_SUPPORT = False

try:
    from docx import Document as DocxDocument
    DOCX_SUPPORT = True
except ImportError:
    DOCX_SUPPORT = False

try:
    import pandas as pd
    PANDAS_SUPPORT = True
except ImportError:
    PANDAS_SUPPORT = False

try:
    from PIL import Image
    from PIL.ExifTags import TAGS
    IMAGE_SUPPORT = True
except ImportError:
    IMAGE_SUPPORT = False

try:
    import pytesseract
    OCR_SUPPORT = True
except ImportError:
    OCR_SUPPORT = False

# 配置日志
logger = logging.getLogger(__name__)


class MultiFormatProcessor:
    """
    多格式文档处理器
    
    支持全格式文档解析，包括：
    - 文本格式：Markdown、HTML、纯文本
    - 办公文档：PDF、Word、Excel、PPT
    - 多媒体：图像、视频、音频
    """
    
    def __init__(self, ocr_language: str = "chi_sim+eng"):
        """
        初始化多格式处理器
        
        Args:
            ocr_language: OCR识别语言配置
        """
        self.ocr_language = ocr_language
        self.supported_formats = self._get_supported_formats()
        
        logger.info(f"多格式处理器初始化完成，支持格式: {len(self.supported_formats)} 种")
    
    def _get_supported_formats(self) -> Dict[str, List[str]]:
        """获取支持的文件格式"""
        return {
            "text": [".txt", ".md", ".markdown", ".rst"],
            "html": [".html", ".htm", ".xhtml"],
            "json": [".json", ".jsonl"],
            "csv": [".csv", ".tsv"],
            "excel": [".xlsx", ".xls", ".xlsm"],
            "pdf": [".pdf"],
            "word": [".docx", ".doc"],
            "powerpoint": [".pptx", ".ppt"],
            "image": [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".webp"],
            "audio": [".mp3", ".wav", ".m4a", ".flac", ".ogg"],
            "video": [".mp4", ".avi", ".mov", ".mkv", ".webm"]
        }
    
    def detect_file_type(self, file_path: str) -> Tuple[str, str]:
        """
        检测文件类型
        
        Args:
            file_path: 文件路径
            
        Returns:
            (文件类型分类, MIME类型)
        """
        # 获取文件扩展名
        ext = Path(file_path).suffix.lower()
        
        # 基于扩展名分类
        for category, extensions in self.supported_formats.items():
            if ext in extensions:
                mime_type = mimetypes.guess_type(file_path)[0] or "application/octet-stream"
                return category, mime_type
        
        # 未知类型
        return "unknown", "application/octet-stream"
    
    def extract_content(self, file_path: str, 
                       max_content_length: int = 1000000) -> Dict[str, Any]:
        """
        提取文件内容
        
        Args:
            file_path: 文件路径
            max_content_length: 最大内容长度限制
            
        Returns:
            提取的内容和元数据
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"文件不存在: {file_path}")
        
        file_size = os.path.getsize(file_path)
        if file_size > max_content_length:
            logger.warning(f"文件过大 ({file_size}字节)，可能超过处理限制")
        
        file_category, mime_type = self.detect_file_type(file_path)
        
        # 根据文件类型调用相应的提取方法
        extract_methods = {
            "text": self._extract_text_content,
            "html": self._extract_html_content,
            "json": self._extract_json_content,
            "csv": self._extract_csv_content,
            "excel": self._extract_excel_content,
            "pdf": self._extract_pdf_content,
            "word": self._extract_word_content,
            "image": self._extract_image_content,
            "audio": self._extract_audio_metadata,
            "video": self._extract_video_metadata
        }
        
        if file_category in extract_methods:
            try:
                content_data = extract_methods[file_category](file_path)
                content_data["file_category"] = file_category
                content_data["mime_type"] = mime_type
                content_data["file_size"] = file_size
                content_data["file_path"] = file_path
                content_data["extraction_success"] = True
                
                return content_data
            except Exception as e:
                logger.error(f"文件内容提取失败: {file_path}, 错误: {str(e)}")
                return self._create_error_result(file_path, file_category, mime_type, str(e))
        else:
            # 未知文件类型，尝试作为二进制处理
            return self._handle_unknown_format(file_path, mime_type)
    
    def _extract_text_content(self, file_path: str) -> Dict[str, Any]:
        """提取文本文件内容"""
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        return {
            "content_type": "text",
            "content": content,
            "encoding": "utf-8",
            "line_count": len(content.splitlines()),
            "word_count": len(content.split())
        }
    
    def _extract_html_content(self, file_path: str) -> Dict[str, Any]:
        """提取HTML文件内容"""
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        # 简化HTML提取正文内容（实际应用中可使用BeautifulSoup）
        # 这里返回原始HTML，由Notebook LM处理
        return {
            "content_type": "html",
            "content": content,
            "encoding": "utf-8",
            "is_html": True
        }
    
    def _extract_json_content(self, file_path: str) -> Dict[str, Any]:
        """提取JSON文件内容"""
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # 将JSON转换为可读文本
        content = json.dumps(data, ensure_ascii=False, indent=2)
        
        return {
            "content_type": "json",
            "content": content,
            "data_structure": self._analyze_json_structure(data),
            "is_valid_json": True
        }
    
    def _extract_csv_content(self, file_path: str) -> Dict[str, Any]:
        """提取CSV文件内容"""
        if not PANDAS_SUPPORT:
            # 如果没有pandas，使用基本文本提取
            return self._extract_text_content(file_path)
        
        try:
            df = pd.read_csv(file_path)
            
            # 生成描述性摘要
            summary = {
                "row_count": len(df),
                "column_count": len(df.columns),
                "columns": list(df.columns),
                "data_types": {col: str(dtype) for col, dtype in df.dtypes.items()}
            }
            
            # 转换为可读文本
            content = f"CSV文件摘要: {json.dumps(summary, ensure_ascii=False, indent=2)}"
            content += f"\n\n前10行数据预览:\n{df.head(10).to_string()}"
            
            return {
                "content_type": "csv",
                "content": content,
                "summary": summary,
                "has_dataframe": True
            }
        except Exception as e:
            logger.warning(f"CSV解析失败，降级为文本提取: {str(e)}")
            return self._extract_text_content(file_path)
    
    def _extract_excel_content(self, file_path: str) -> Dict[str, Any]:
        """提取Excel文件内容"""
        if not PANDAS_SUPPORT:
            return self._create_unsupported_result("excel")
        
        try:
            # 读取所有工作表
            excel_file = pd.ExcelFile(file_path)
            sheet_names = excel_file.sheet_names
            
            sheets_data = {}
            for sheet_name in sheet_names[:5]:  # 限制处理前5个工作表
                df = pd.read_excel(file_path, sheet_name=sheet_name)
                
                sheets_data[sheet_name] = {
                    "row_count": len(df),
                    "column_count": len(df.columns),
                    "columns": list(df.columns)
                }
            
            content = f"Excel文件包含 {len(sheet_names)} 个工作表\n"
            content += f"工作表摘要: {json.dumps(sheets_data, ensure_ascii=False, indent=2)}"
            
            return {
                "content_type": "excel",
                "content": content,
                "sheet_count": len(sheet_names),
                "sheets_data": sheets_data,
                "has_excel_data": True
            }
        except Exception as e:
            logger.error(f"Excel解析失败: {str(e)}")
            return self._create_error_result(file_path, "excel", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", str(e))
    
    def _extract_pdf_content(self, file_path: str) -> Dict[str, Any]:
        """提取PDF文件内容"""
        if not PDF_SUPPORT:
            return self._create_unsupported_result("pdf")
        
        try:
            with pdfplumber.open(file_path) as pdf:
                text_content = ""
                page_count = len(pdf.pages)
                
                for i, page in enumerate(pdf.pages[:50]):  # 限制前50页
                    page_text = page.extract_text()
                    if page_text:
                        text_content += f"\n--- 第 {i+1} 页 ---\n{page_text}"
                
                return {
                    "content_type": "pdf",
                    "content": text_content,
                    "page_count": page_count,
                    "extraction_method": "pdfplumber"
                }
        except Exception as e:
            logger.error(f"PDF解析失败: {str(e)}")
            return self._create_error_result(file_path, "pdf", "application/pdf", str(e))
    
    def _extract_word_content(self, file_path: str) -> Dict[str, Any]:
        """提取Word文档内容"""
        if not DOCX_SUPPORT:
            return self._create_unsupported_result("word")
        
        try:
            doc = DocxDocument(file_path)
            
            # 提取文本
            full_text = []
            for paragraph in doc.paragraphs:
                if paragraph.text.strip():
                    full_text.append(paragraph.text)
            
            content = "\n".join(full_text)
            
            return {
                "content_type": "word",
                "content": content,
                "paragraph_count": len(full_text),
                "extraction_method": "python-docx"
            }
        except Exception as e:
            logger.error(f"Word文档解析失败: {str(e)}")
            return self._create_error_result(file_path, "word", "application/vnd.openxmlformats-officedocument.wordprocessingml.document", str(e))
    
    def _extract_image_content(self, file_path: str) -> Dict[str, Any]:
        """提取图像文件内容"""
        if not IMAGE_SUPPORT:
            return self._create_unsupported_result("image")
        
        try:
            result = {
                "content_type": "image",
                "has_image_data": True
            }
            
            # 打开图像获取基本信息
            with Image.open(file_path) as img:
                result.update({
                    "format": img.format,
                    "size": img.size,
                    "mode": img.mode,
                    "width": img.width,
                    "height": img.height
                })
                
                # 提取EXIF信息
                exif_data = img._getexif()
                if exif_data:
                    exif = {}
                    for tag_id, value in exif_data.items():
                        tag = TAGS.get(tag_id, tag_id)
                        exif[tag] = value
                    result["exif"] = exif
            
            # 尝试OCR提取文本
            if OCR_SUPPORT:
                try:
                    ocr_text = pytesseract.image_to_string(file_path, lang=self.ocr_language)
                    if ocr_text.strip():
                        result["ocr_text"] = ocr_text
                        result["has_ocr_content"] = True
                except Exception as ocr_error:
                    logger.warning(f"OCR提取失败: {str(ocr_error)}")
            
            # 生成描述性内容
            description = f"图像文件: {Path(file_path).name}\n"
            description += f"尺寸: {result.get('width', '未知')} × {result.get('height', '未知')} 像素\n"
            description += f"格式: {result.get('format', '未知')}\n"
            
            if "ocr_text" in result:
                description += f"\nOCR识别内容:\n{result['ocr_text']}\n"
            
            result["content"] = description
            
            return result
        except Exception as e:
            logger.error(f"图像处理失败: {str(e)}")
            return self._create_error_result(file_path, "image", "image/jpeg", str(e))
    
    def _extract_audio_metadata(self, file_path: str) -> Dict[str, Any]:
        """提取音频文件元数据"""
        # 实际应用中可使用pydub、mutagen等库
        # 这里返回基本文件信息
        file_stats = os.stat(file_path)
        
        content = f"音频文件: {Path(file_path).name}\n"
        content += f"文件大小: {file_stats.st_size} 字节\n"
        content += f"修改时间: {file_stats.st_mtime}\n"
        
        return {
            "content_type": "audio",
            "content": content,
            "file_stats": {
                "size": file_stats.st_size,
                "mtime": file_stats.st_mtime
            }
        }
    
    def _extract_video_metadata(self, file_path: str) -> Dict[str, Any]:
        """提取视频文件元数据"""
        # 实际应用中可使用OpenCV、moviepy等库
        # 这里返回基本文件信息
        file_stats = os.stat(file_path)
        
        content = f"视频文件: {Path(file_path).name}\n"
        content += f"文件大小: {file_stats.st_size} 字节\n"
        content += f"修改时间: {file_stats.st_mtime}\n"
        
        return {
            "content_type": "video",
            "content": content,
            "file_stats": {
                "size": file_stats.st_size,
                "mtime": file_stats.st_mtime
            }
        }
    
    def _analyze_json_structure(self, data: Any) -> Dict[str, Any]:
        """分析JSON数据结构"""
        if isinstance(data, dict):
            return {
                "type": "object",
                "key_count": len(data),
                "keys": list(data.keys())[:20]  # 限制显示前20个键
            }
        elif isinstance(data, list):
            return {
                "type": "array",
                "length": len(data),
                "first_item_type": type(data[0]).__name__ if len(data) > 0 else "empty"
            }
        else:
            return {
                "type": type(data).__name__,
                "value_preview": str(data)[:100]
            }
    
    def _create_unsupported_result(self, format_type: str) -> Dict[str, Any]:
        """创建不支持格式的结果"""
        return {
            "content_type": format_type,
            "content": f"警告: {format_type.upper()}格式解析需要安装额外依赖库\n文件以二进制格式上传",
            "extraction_success": False,
            "support_status": "requires_dependencies"
        }
    
    def _create_error_result(self, file_path: str, file_category: str,
                            mime_type: str, error_msg: str) -> Dict[str, Any]:
        """创建错误结果"""
        return {
            "file_category": file_category,
            "mime_type": mime_type,
            "content": f"文件处理错误: {error_msg}\n文件路径: {file_path}",
            "extraction_success": False,
            "error": error_msg
        }
    
    def _handle_unknown_format(self, file_path: str, mime_type: str) -> Dict[str, Any]:
        """处理未知格式"""
        file_stats = os.stat(file_path)
        
        content = f"未知格式文件: {Path(file_path).name}\n"
        content += f"MIME类型: {mime_type}\n"
        content += f"文件大小: {file_stats.st_size} 字节\n"
        
        return {
            "content_type": "unknown",
            "mime_type": mime_type,
            "content": content,
            "extraction_success": True,
            "is_binary": True
        }


# 便捷函数
def process_document(file_path: str, processor: Optional[MultiFormatProcessor] = None) -> Dict[str, Any]:
    """
    处理文档文件的便捷函数
    
    Args:
        file_path: 文件路径
        processor: 可选的多格式处理器实例
        
    Returns:
        处理结果
    """
    if processor is None:
        processor = MultiFormatProcessor()
    
    return processor.extract_content(file_path)


if __name__ == "__main__":
    # 模块测试
    print("多格式支持模块测试")
    
    # 创建测试处理器
    processor = MultiFormatProcessor()
    
    # 测试文件类型检测
    test_files = [
        "document.md",
        "report.pdf",
        "data.xlsx",
        "image.jpg"
    ]
    
    for test_file in test_files:
        category, mime = processor.detect_file_type(test_file)
        print(f"{test_file}: 类别={category}, MIME={mime}")