#!/bin/bash
cd d:/mywork/onehubserver
/c/Users/zhaos/AppData/Local/Programs/Python/Python311/python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
