#!/data/data/com.termux/files/usr/bin/bash
echo "=== Instalando dependencias ==="
pip install networkx 2>&1 | tail -1
pip install google-genai 2>&1 | tail -1
echo "=== Streamlit (pulando pyarrow/pillow) ==="
pip install streamlit --no-deps 2>&1 | tail -1
echo "=== Dependencias do Streamlit ==="
pip install tornado altair blinker cachetools click gitpython packaging protobuf pydeck pydantic requests rich tenacity toml typing_extensions starlette uvicorn anyio websockets python-multipart httptools itsdangerous 2>&1 | tail -1
echo "=== Plotly (graficos) ==="
pip install plotly 2>&1 | tail -1
echo "=== PRONTO! ==="
