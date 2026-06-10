#!/data/data/com.termux/files/usr/bin/bash
set -e

echo "=== Instalando dependencias core ==="
pip install --quiet networkx 2>&1 | tail -1
pip install --quiet google-genai 2>&1 | tail -1
pip install --quiet plotly 2>&1 | tail -1

echo "=== Streamlit (sem pandas/pyarrow/pillow) ==="
pip install --quiet streamlit --no-deps 2>&1 | tail -1

echo "=== Dependencias manuais do Streamlit ==="
pip install --quiet tornado altair blinker cachetools click gitpython packaging protobuf pydeck pydantic requests rich tenacity toml typing_extensions starlette uvicorn anyio websockets python-multipart httptools itsdangerous 2>&1 | tail -1

echo ""
echo "=== VERIFICANDO ==="
python3 -c "
import streamlit; print(f'streamlit {streamlit.__version__}')
import plotly; print(f'plotly {plotly.__version__}')
import networkx; print(f'networkx {networkx.__version__}')
import google.genai; print('google-genai OK')
print('Tudo certo!')
"
echo ""
echo "=== Para rodar ==="
echo "streamlit run app.py --server.headless true"
