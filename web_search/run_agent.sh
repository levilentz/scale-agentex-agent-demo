#!/bin/bash

if [ -n "$GEMINI" ]; then
    uvicorn project.acp_gemini:acp --host 0.0.0.0 --port 8000
else
    uvicorn project.acp:acp --host 0.0.0.0 --port 8000
fi
