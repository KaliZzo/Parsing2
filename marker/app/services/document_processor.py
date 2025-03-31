import os
from marker.converters.pdf import PdfConverter
from marker.models import create_model_dict
from marker.output import text_from_rendered
from marker.config.parser import ConfigParser
from marker.services.openai import OpenAIService


def marker_standard_convert(file_path: str, output_format: str = "markdown") -> str:
    """המרת קובץ עם Marker ללא GPT וללא OCR"""
    converter = PdfConverter(
        artifact_dict=create_model_dict(),
        config={"output_format": output_format}
    )
    rendered = converter(file_path)
    text, _, _ = text_from_rendered(rendered)
    return text


def marker_ocr_only_convert(file_path: str, output_format: str = "markdown") -> str:
    """המרת קובץ עם OCR בלבד"""
    converter = PdfConverter(
        artifact_dict=create_model_dict(),
        config={
            "output_format": output_format,
            "force_ocr": True,
            "use_llm": False,
        }
    )
    rendered = converter(file_path)
    text, _, _ = text_from_rendered(rendered)
    return text


def marker_with_gpt_convert(file_path: str, api_key: str, model_name: str = "gpt-4o", output_format: str = "markdown") -> str:
    """המרת קובץ עם GPT (תיאור לתמונות)"""
    os.environ["OPENAI_API_KEY"] = api_key
    os.environ["OPENAI_MODEL"] = model_name

    config = {
        "output_format": output_format,
        "use_llm": True,
        "disable_image_extraction": True,
        "openai_api_key": api_key,
        "openai_model": model_name,
        "llm_service": "marker.services.openai.OpenAIService"
    }

    config_parser = ConfigParser(config)

    converter = PdfConverter(
        artifact_dict=create_model_dict(),
        config=config_parser.generate_config_dict(),
        llm_service=config_parser.get_llm_service()
    )

    rendered = converter(file_path)
    text, _, _ = text_from_rendered(rendered)
    return text
