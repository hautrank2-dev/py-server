"""
Chạy dev server cho dễ:

    python run.py

Tương đương: uvicorn main:app --app-dir src --reload
"""
import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        app_dir="src",   # code nằm trong src/
        host="127.0.0.1",
        port=8000,
        reload=True,     # tự reload khi sửa code
    )
