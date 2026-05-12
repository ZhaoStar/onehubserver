@echo off
cd /d d:\mywork\onehubserver
C:\Users\zhaos\AppData\Local\Programs\Python\Python311\python.exe -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
