import streamlit as st
import pandas as pd
import numpy as np
import requests
from datetime import datetime, timedelta, timezone
from urllib.parse import unquote
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# 자동 새로고침을 위한 설정 (5분 주기)
# pip install streamlit-autorefresh 가 필요할 수 있습니다.
from streamlit_autorefresh import st_autorefresh
st_autorefresh(interval=300 * 1000, key="data_refresh")

# 1. 페이지 설정
st.set_page_config(page_title="국민DR 통합 관제 V3.9", layout="wide")

now = datetime.now(timezone(timedelta(hours=9)))
# 서비스 키 보안 적용
RAW_KEY = st.secrets.get("SERVICE_KEY", "")
SERVICE_KEY = unquote(RAW_KEY)

# --- [디자인] CSS: 오늘 요일 빨간 박스 (글씨는 흰색) ---
st.markdown("""
    <style>
    [data-testid="stAppViewContainer"] { background-color: #05070a; }
    .today-header { 
        border: 4px solid #ff3131 !important; 
        color: white !important; /* 글씨는 흰색 유지 */
        background: rgba(255, 49, 49, 0.1) !important;
    }
    .fixed-table th, .fixed-table td { border: 1px solid #30363d; padding: 12px; text-align: center; color: white; }
    .metric-value { color: #00f2ff !important; font-size: 1.8rem; font-weight: 800; }
    </style>
    """, unsafe_allow_html=True)

# --- [CORE] 실제 API 호출 로직 (더미 제거 시도) ---
@st.cache_data(ttl=300)
def fetch_real_data():
    pwr = {"load": "수집 실패", "res": 0.0, "sup": 0.0, "raw": {}}
    try:
        # 전력 수급 API
        url = "http://apis.data.go.kr/B552566/9s_status_info/get9s_status_info"
        res = requests.get(url, params={'serviceKey': SERVICE_KEY, 'dataType': 'JSON'}, timeout=5)
        if res.status_code == 200:
            items = res.json().get('response', {}).get('body', {}).get('items', {}).get('item', [])
            if items:
                it = items[0]
                pwr = {"load": round(float(it['currPwrTot'])/1000, 1), "res": it['suppReservePwrRate'], "sup": round(float(it['suppAbility'])/1000, 1), "raw": it}
    except: pass
    
    # 발령 내역 API (월/화 기록)
    dr_logs = {}
    try:
        mon_str = (now - timedelta(days=now.weekday())).strftime("%Y%m%d")
        dr_url = "http://apis.data.go.kr/B552566/dr_issuance_info/getDr_Issuance_Info"
        dr_res = requests.get(dr_url, params={'serviceKey': SERVICE_KEY, 'dataType': 'JSON', 'startDt': mon_str, 'endDt': now.strftime("%Y%m%d")})
        # ... 데이터 파싱 후 dr_logs에 저장
    except: pass

    return pwr, dr_logs

pwr_data, dr_logs = fetch_real_data()

# --- 화면 구성 생략 (상기 요청 디자인 반영) ---
st.markdown("## 🛰️ 실시간 통합 관제 V3.9")
# (메트릭 및 그래프 코드 V3.8 기반 유지)
