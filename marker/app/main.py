from fastapi import FastAPI
from app.routes import document_processing

app = FastAPI()

# Include the PDF processing router
app.include_router(document_processing.router)
