from fastapi import APIRouter, UploadFile, File, HTTPException, Form, Query, Request
from fastapi.responses import JSONResponse, FileResponse
import tempfile
import os
import shutil
from typing import Optional
from app.services.document_processor import marker_standard_convert, marker_ocr_only_convert, marker_with_gpt_convert

router = APIRouter(
    prefix="/documents",
    tags=["documents"],
    responses={404: {"description": "Not found"}},
)

SUPPORTED_FORMATS = [
    "pdf", "docx", "doc", "pptx", "ppt", 
    "jpg", "jpeg", "png", "tiff", "tif", "bmp", "gif",
    "epub", "xlsx", "xls", "html", "htm"
]

@router.get("/health")
async def health_check():
    """
    בדיקת תקינות לבדיקה שהשירות פעיל
    """
    return {"status": "ok", "message": "שירות עיבוד המסמכים פעיל ורץ"}

def convert_and_save_markdown(file_path, converter_func, output_dir=None, **kwargs):
    """
    ממיר קובץ למרקדאון ושומר אותו עם אותו שם בתיקייה
    
    Args:
        file_path: נתיב לקובץ המקור
        converter_func: פונקציית ההמרה לשימוש
        output_dir: תיקיית פלט (אופציונלי)
        **kwargs: פרמטרים נוספים לפונקציית ההמרה
        
    Returns:
        (str, str): נתיב לקובץ המרקדאון שנוצר, התוכן של המרקדאון
    """
    try:
        # המרת הקובץ למרקדאון
        markdown_content = converter_func(file_path=file_path, output_format="markdown", **kwargs)
        
        if not markdown_content:
            raise ValueError("תוכן המרקדאון ריק לאחר המרה")
        
        # יצירת שם קובץ הפלט
        base_name = os.path.splitext(os.path.basename(file_path))[0]
        output_path = os.path.join(output_dir if output_dir else os.path.dirname(file_path), f"{base_name}.md")
        
        # שמירת הקובץ
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(markdown_content)
        
        # ודא שהקובץ נוצר
        if not os.path.exists(output_path):
            raise FileNotFoundError(f"הקובץ {output_path} לא נוצר")
            
        return output_path, markdown_content
    except Exception as e:
        print(f"שגיאה בהמרה לקובץ מרקדאון: {str(e)}")
        raise

@router.post("/standard/binary")
async def standard_convert_binary(
    request: Request,
    output_format: str = Query("markdown", enum=["markdown", "json", "html"]),
    file_name: str = Query(..., description="שם הקובץ כולל סיומת")
):
    """
    המרה סטנדרטית של מסמך בקידוד בינארי
    
    הקובץ מועבר ישירות בגוף הבקשה (לא ב-form-data)
    
    פרמטרים:
    - file_name: שם הקובץ כולל סיומת (חובה)
    - output_format: פורמט הפלט (markdown, json, או html)
    """
    # בדיקת סיומת הקובץ
    file_ext = os.path.splitext(file_name)[1][1:].lower()  # הסרת הנקודה
    
    if file_ext not in SUPPORTED_FORMATS:
        raise HTTPException(
            status_code=400, 
            detail=f"פורמט קובץ לא נתמך: {file_ext}. פורמטים נתמכים: {', '.join(SUPPORTED_FORMATS)}"
        )
    
    # שימוש בתיקייה קבועה במקום תיקייה זמנית
    fixed_dir = "/pd"
    temp_file_path = os.path.join(fixed_dir, file_name)
    
    try:
        # קריאת נתוני הקובץ מגוף הבקשה
        file_content = await request.body()
        
        if not file_content:
            raise HTTPException(status_code=400, detail="גוף הבקשה ריק, חסר תוכן הקובץ")
        
        # שמירת הקובץ למיקום קבוע
        with open(temp_file_path, "wb") as buffer:
            buffer.write(file_content)
        
        if output_format == "markdown":
            try:
                # המרה ישירה למרקדאון
                text = marker_standard_convert(
                    file_path=temp_file_path,
                    output_format="markdown"
                )
                
                if not text:
                    raise HTTPException(status_code=500, detail="המרה נכשלה - התוכן ריק")
                
                # שמירת המרקדאון לקובץ
                output_base_name = os.path.splitext(file_name)[0]
                output_path = os.path.join(fixed_dir, f"{output_base_name}.md")
                
                with open(output_path, "w", encoding="utf-8") as f:
                    f.write(text)
                
                # ודא שהקובץ נוצר
                if not os.path.exists(output_path):
                    raise HTTPException(status_code=500, detail=f"הקובץ {output_path} לא נוצר")
                
                print(f"מחזיר קובץ מנתיב: {output_path}")
                
                # החזרת קובץ המרקדאון כתשובה
                return FileResponse(
                    path=output_path,
                    filename=f"{output_base_name}.md",
                    media_type="text/markdown"
                )
            except Exception as e:
                print(f"שגיאה בעיבוד המרקדאון: {str(e)}")
                # מעבר למצב מחזיר טקסט במקום קובץ
                text = marker_standard_convert(
                    file_path=temp_file_path,
                    output_format="markdown"
                )
                return JSONResponse(content={"text": text, "file_type": file_ext})
        else:
            # המרה רגילה לפורמט שנבחר
            text = marker_standard_convert(
                file_path=temp_file_path,
                output_format=output_format
            )
            
            # הכנת נתוני התגובה
            response_data = {
                "text": text,
                "file_type": file_ext,
                "conversion_type": "standard"
            }
            
            # אם פורמט הפלט הוא HTML או JSON, כלול מידע מתאים
            if output_format == "html":
                response_data["html"] = text
            elif output_format == "json":
                response_data["json"] = text
            
            return JSONResponse(content=response_data)
    
    except Exception as e:
        print(f"Exception: {e}")
        raise HTTPException(status_code=500, detail=f"שגיאה בעיבוד הקובץ: {str(e)}")
    
    finally:
        # לא מנקים תיקייה קבועה
        pass

@router.post("/ocr/binary")
async def ocr_convert_binary(
    request: Request,
    output_format: str = Query("markdown", enum=["markdown", "json", "html"]),
    file_name: str = Query(..., description="שם הקובץ כולל סיומת")
):
    """
    המרת מסמך עם OCR בקידוד בינארי
    
    הקובץ מועבר ישירות בגוף הבקשה (לא ב-form-data)
    
    פרמטרים:
    - file_name: שם הקובץ כולל סיומת (חובה)
    - output_format: פורמט הפלט (markdown, json, או html)
    """
    # בדיקת סיומת הקובץ
    file_ext = os.path.splitext(file_name)[1][1:].lower()  # הסרת הנקודה
    
    if file_ext not in SUPPORTED_FORMATS:
        raise HTTPException(
            status_code=400, 
            detail=f"פורמט קובץ לא נתמך: {file_ext}. פורמטים נתמכים: {', '.join(SUPPORTED_FORMATS)}"
        )
    
    # שימוש בתיקייה קבועה במקום תיקייה זמנית
    fixed_dir = "/pd"
    temp_file_path = os.path.join(fixed_dir, file_name)
    
    try:
        # קריאת נתוני הקובץ מגוף הבקשה
        file_content = await request.body()
        
        if not file_content:
            raise HTTPException(status_code=400, detail="גוף הבקשה ריק, חסר תוכן הקובץ")
        
        # שמירת הקובץ למיקום קבוע
        with open(temp_file_path, "wb") as buffer:
            buffer.write(file_content)
        
        if output_format == "markdown":
            try:
                # המרה ישירה למרקדאון
                text = marker_ocr_only_convert(
                    file_path=temp_file_path,
                    output_format="markdown"
                )
                
                if not text:
                    raise HTTPException(status_code=500, detail="המרה נכשלה - התוכן ריק")
                
                # שמירת המרקדאון לקובץ
                output_base_name = os.path.splitext(file_name)[0]
                output_path = os.path.join(fixed_dir, f"{output_base_name}.md")
                
                with open(output_path, "w", encoding="utf-8") as f:
                    f.write(text)
                
                # ודא שהקובץ נוצר
                if not os.path.exists(output_path):
                    raise HTTPException(status_code=500, detail=f"הקובץ {output_path} לא נוצר")
                
                print(f"מחזיר קובץ מנתיב: {output_path}")
                
                # החזרת קובץ המרקדאון כתשובה
                return FileResponse(
                    path=output_path,
                    filename=f"{output_base_name}.md",
                    media_type="text/markdown"
                )
            except Exception as e:
                print(f"שגיאה בעיבוד המרקדאון: {str(e)}")
                # מעבר למצב מחזיר טקסט במקום קובץ
                text = marker_ocr_only_convert(
                    file_path=temp_file_path,
                    output_format="markdown"
                )
                return JSONResponse(content={"text": text, "file_type": file_ext})
        else:
            # המרה רגילה לפורמט שנבחר
            text = marker_ocr_only_convert(
                file_path=temp_file_path,
                output_format=output_format
            )
            
            # הכנת נתוני התגובה
            response_data = {
                "text": text,
                "file_type": file_ext,
                "conversion_type": "ocr"
            }
            
            # אם פורמט הפלט הוא HTML או JSON, כלול מידע מתאים
            if output_format == "html":
                response_data["html"] = text
            elif output_format == "json":
                response_data["json"] = text
            
            return JSONResponse(content=response_data)
    
    except Exception as e:
        print(f"Exception: {e}")
        raise HTTPException(status_code=500, detail=f"שגיאה בעיבוד הקובץ: {str(e)}")
    
    finally:
        # לא מנקים תיקייה קבועה
        pass

@router.post("/gpt/binary")
async def gpt_convert_binary(
    request: Request,
    output_format: str = Query("markdown", enum=["markdown", "json", "html"]),
    file_name: str = Query(..., description="שם הקובץ כולל סיומת"),
    api_key: str = Query(..., description="מפתח API של OpenAI"),
    model_name: str = Query("gpt-4o", description="שם המודל של OpenAI")
):
    """
    המרת מסמך עם GPT בקידוד בינארי
    
    הקובץ מועבר ישירות בגוף הבקשה (לא ב-form-data)
    
    פרמטרים:
    - file_name: שם הקובץ כולל סיומת (חובה)
    - output_format: פורמט הפלט (markdown, json, או html)
    - api_key: מפתח API של OpenAI (חובה)
    - model_name: שם המודל של OpenAI (ברירת מחדל: gpt-4o)
    """
    # בדיקת סיומת הקובץ
    file_ext = os.path.splitext(file_name)[1][1:].lower()  # הסרת הנקודה
    
    if file_ext not in SUPPORTED_FORMATS:
        raise HTTPException(
            status_code=400, 
            detail=f"פורמט קובץ לא נתמך: {file_ext}. פורמטים נתמכים: {', '.join(SUPPORTED_FORMATS)}"
        )
    
    # שימוש בתיקייה קבועה במקום תיקייה זמנית
    fixed_dir = "/pd"
    temp_file_path = os.path.join(fixed_dir, file_name)
    
    try:
        # קריאת נתוני הקובץ מגוף הבקשה
        file_content = await request.body()
        
        if not file_content:
            raise HTTPException(status_code=400, detail="גוף הבקשה ריק, חסר תוכן הקובץ")
        
        # שמירת הקובץ למיקום קבוע
        with open(temp_file_path, "wb") as buffer:
            buffer.write(file_content)
        
        if output_format == "markdown":
            try:
                # המרה ישירה למרקדאון
                text = marker_with_gpt_convert(
                    file_path=temp_file_path,
                    api_key=api_key,
                    model_name=model_name,
                    output_format="markdown"
                )
                
                if not text:
                    raise HTTPException(status_code=500, detail="המרה נכשלה - התוכן ריק")
                
                # שמירת המרקדאון לקובץ
                output_base_name = os.path.splitext(file_name)[0]
                output_path = os.path.join(fixed_dir, f"{output_base_name}.md")
                
                with open(output_path, "w", encoding="utf-8") as f:
                    f.write(text)
                
                # ודא שהקובץ נוצר
                if not os.path.exists(output_path):
                    raise HTTPException(status_code=500, detail=f"הקובץ {output_path} לא נוצר")
                
                print(f"מחזיר קובץ מנתיב: {output_path}")
                
                # החזרת קובץ המרקדאון כתשובה
                return FileResponse(
                    path=output_path,
                    filename=f"{output_base_name}.md",
                    media_type="text/markdown"
                )
            except Exception as e:
                print(f"שגיאה בעיבוד המרקדאון: {str(e)}")
                # מעבר למצב מחזיר טקסט במקום קובץ
                text = marker_with_gpt_convert(
                    file_path=temp_file_path,
                    api_key=api_key,
                    model_name=model_name,
                    output_format="markdown"
                )
                return JSONResponse(content={
                    "text": text, 
                    "file_type": file_ext,
                    "conversion_type": "gpt"
                })
        else:
            # המרה רגילה לפורמט שנבחר
            text = marker_with_gpt_convert(
                file_path=temp_file_path,
                api_key=api_key,
                model_name=model_name,
                output_format=output_format
            )
            
            # הכנת נתוני התגובה
            response_data = {
                "text": text,
                "file_type": file_ext,
                "conversion_type": "gpt",
                "model": model_name
            }
            
            # אם פורמט הפלט הוא HTML או JSON, כלול מידע מתאים
            if output_format == "html":
                response_data["html"] = text
            elif output_format == "json":
                response_data["json"] = text
            
            return JSONResponse(content=response_data)
    
    except Exception as e:
        print(f"Exception: {e}")
        raise HTTPException(status_code=500, detail=f"שגיאה בעיבוד הקובץ: {str(e)}")
    
    finally:
        # לא מנקים תיקייה קבועה
        pass

@router.post("/standard")
async def standard_convert_endpoint(
    file: UploadFile = File(...),
    output_format: str = Form("markdown")
):
    """
    המרה סטנדרטית של מסמך ללא OCR וללא GPT
    
    פרמטרים:
    - file: קובץ המסמך לעיבוד
    - output_format: פורמט הפלט (markdown, json, או html)
    """
   
    filename = file.filename.lower()
    file_ext = os.path.splitext(filename)[1][1:]  
    
    if file_ext not in SUPPORTED_FORMATS:
        raise HTTPException(
            status_code=400, 
            detail=f"פורמט קובץ לא נתמך: {file_ext}. פורמטים נתמכים: {', '.join(SUPPORTED_FORMATS)}"
        )
    
   
    if output_format not in ["markdown", "json", "html"]:
        raise HTTPException(status_code=400, detail="פורמט הפלט חייב להיות markdown, json, או html")
    

    temp_dir = tempfile.mkdtemp()
    temp_file_path = os.path.join(temp_dir, file.filename)
    
    try:
    
        with open(temp_file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        

        text = marker_standard_convert(
            file_path=temp_file_path,
            output_format=output_format
        )
        
        if text is None:
            raise HTTPException(status_code=500, detail="כשל בעיבוד המסמך")
        
  
        response_data = {
            "text": text,
            "file_type": file_ext,
            "conversion_type": "standard"
        }
        
 
        if output_format == "html":
            response_data["html"] = text
        elif output_format == "json":
            response_data["json"] = text
        
        return JSONResponse(content=response_data)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"שגיאה בעיבוד הקובץ: {str(e)}")
    
    finally:
 
        shutil.rmtree(temp_dir, ignore_errors=True)

@router.post("/ocr")
async def ocr_convert_endpoint(
    file: UploadFile = File(...),
    output_format: str = Form("markdown")
):
    """
    המרת מסמך עם OCR בלבד
    
    פרמטרים:
    - file: קובץ המסמך לעיבוד
    - output_format: פורמט הפלט (markdown, json, או html)
    """
    # בדיקת סיומת הקובץ
    filename = file.filename.lower()
    file_ext = os.path.splitext(filename)[1][1:]  # הסרת הנקודה
    
    if file_ext not in SUPPORTED_FORMATS:
        raise HTTPException(
            status_code=400, 
            detail=f"פורמט קובץ לא נתמך: {file_ext}. פורמטים נתמכים: {', '.join(SUPPORTED_FORMATS)}"
        )
    
    # בדיקת פורמט הפלט
    if output_format not in ["markdown", "json", "html"]:
        raise HTTPException(status_code=400, detail="פורמט הפלט חייב להיות markdown, json, או html")
    
    # יצירת קובץ זמני
    temp_dir = tempfile.mkdtemp()
    temp_file_path = os.path.join(temp_dir, file.filename)
    
    try:
        # שמירת הקובץ שהועלה למיקום זמני
        with open(temp_file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # המרה עם OCR
        text = marker_ocr_only_convert(
            file_path=temp_file_path,
            output_format=output_format
        )
        
        if text is None:
            raise HTTPException(status_code=500, detail="כשל בעיבוד המסמך")
        
        # הכנת נתוני התגובה
        response_data = {
            "text": text,
            "file_type": file_ext,
            "conversion_type": "ocr"
        }
        
        # אם פורמט הפלט הוא HTML או JSON, כלול מידע מתאים
        if output_format == "html":
            response_data["html"] = text
        elif output_format == "json":
            response_data["json"] = text
        
        return JSONResponse(content=response_data)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"שגיאה בעיבוד הקובץ: {str(e)}")
    
    finally:
        # ניקוי תיקיית הזמני
        shutil.rmtree(temp_dir, ignore_errors=True)

@router.post("/gpt")
async def gpt_convert_endpoint(
    file: UploadFile = File(...),
    output_format: str = Form("markdown"),
    api_key: str = Form(...),
    model_name: str = Form("gpt-4o")
):
    """
    המרת מסמך עם GPT לשיפור איכות ותיאור תמונות
    
    פרמטרים:
    - file: קובץ המסמך לעיבוד
    - output_format: פורמט הפלט (markdown, json, או html)
    - api_key: מפתח API של OpenAI
    - model_name: שם המודל של OpenAI לשימוש (ברירת מחדל: gpt-4o)
    """
    # בדיקת סיומת הקובץ
    filename = file.filename.lower()
    file_ext = os.path.splitext(filename)[1][1:]  # הסרת הנקודה
    
    if file_ext not in SUPPORTED_FORMATS:
        raise HTTPException(
            status_code=400, 
            detail=f"פורמט קובץ לא נתמך: {file_ext}. פורמטים נתמכים: {', '.join(SUPPORTED_FORMATS)}"
        )
    
    # בדיקת פורמט הפלט
    if output_format not in ["markdown", "json", "html"]:
        raise HTTPException(status_code=400, detail="פורמט הפלט חייב להיות markdown, json, או html")
    
    # יצירת קובץ זמני
    temp_dir = tempfile.mkdtemp()
    temp_file_path = os.path.join(temp_dir, file.filename)
    
    try:
        # שמירת הקובץ שהועלה למיקום זמני
        with open(temp_file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # המרה עם GPT
        text = marker_with_gpt_convert(
            file_path=temp_file_path,
            api_key=api_key,
            model_name=model_name,
            output_format=output_format
        )
        
        if text is None:
            raise HTTPException(status_code=500, detail="כשל בעיבוד המסמך")
        
        # הכנת נתוני התגובה
        response_data = {
            "text": text,
            "file_type": file_ext,
            "conversion_type": "gpt",
            "model": model_name
        }
        
        # אם פורמט הפלט הוא HTML או JSON, כלול מידע מתאים
        if output_format == "html":
            response_data["html"] = text
        elif output_format == "json":
            response_data["json"] = text
        
        return JSONResponse(content=response_data)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"שגיאה בעיבוד הקובץ: {str(e)}")
    
    finally:
        # ניקוי תיקיית הזמני
        shutil.rmtree(temp_dir, ignore_errors=True)

@router.post("/parse")
async def parse_document_endpoint(
    file: UploadFile = File(...),
    output_format: str = Form("markdown"),
    use_llm: bool = Form(False),
    force_ocr: bool = Form(False),
    openai_api_key: Optional[str] = Form(None),
    model_name: str = Form("gpt-4o")
):
    """
    המרת מסמך לטקסט (נקודת קצה לתאימות לאחור)
    
    פרמטרים:
    - file: קובץ המסמך לעיבוד
    - output_format: פורמט הפלט (markdown, json, או html)
    - use_llm: שימוש ב-LLM (GPT) לשיפור דיוק
    - force_ocr: אילוץ עיבוד OCR על כל המסמך
    - openai_api_key: מפתח API של OpenAI (נדרש אם use_llm=True)
    - model_name: שם המודל של OpenAI (ברירת מחדל: gpt-4o)
    """
    if use_llm:
        if not openai_api_key:
            raise HTTPException(status_code=400, detail="מפתח API של OpenAI נדרש כאשר use_llm=True")
        return await gpt_convert_endpoint(
            file=file, 
            output_format=output_format, 
            api_key=openai_api_key,
            model_name=model_name
        )
    elif force_ocr:
        return await ocr_convert_endpoint(
            file=file, 
            output_format=output_format
        )
    else:
        return await standard_convert_endpoint(
            file=file, 
            output_format=output_format
        )

@router.post("/parse-pdf")
async def parse_pdf_endpoint(
    file: UploadFile = File(...),
    output_format: str = Form("markdown"),
    use_llm: bool = Form(False),
    force_ocr: bool = Form(False),
    openai_api_key: Optional[str] = Form(None),
    model_name: str = Form("gpt-4o")
):
    """
    המרת מסמך PDF (כינוי לתאימות לאחור)
    """
    # בדיקה שהקובץ הוא PDF
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="הקובץ חייב להיות PDF")
    
    return await parse_document_endpoint(
        file=file,
        output_format=output_format,
        use_llm=use_llm,
        force_ocr=force_ocr,
        openai_api_key=openai_api_key,
        model_name=model_name
    )
