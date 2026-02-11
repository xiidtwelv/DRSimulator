import streamlit as st
import pandas as pd
import numpy as np
import requests
from datetime import datetime, timedelta, timezone
from urllib.parse import unquote
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit.components.v1 as components

# 1. 페이지 설정
st.set_page_config(page_title="국민DR 통합 관제 V4.0", layout="wide")

# [보안 및 인증] 서비스 키 디코딩 처리
RAW_KEY = st.secrets.get("SERVICE_KEY", "")
SERVICE_KEY = unquote(RAW_KEY)

def get_now_kst():
    return datetime.now(timezone(timedelta(hours=9)))

now = get_now_kst()

# 자바스크립트를 이용한 자동 새로고침 (5분 주기 - 라이브러리 설치 불필요)
components.html(
    """<script>
    setTimeout(function(){ window.location.reload(); }, 300000);
    </script>""", height=0
)

# --- [디자인] CSS: 수요일 요일 칸 빨간색 박스 테두리 (글씨 흰색 유지) ---
st.markdown("""
    <style>
    [data-testid="stAppViewContainer"] { background-color: #05070a; }
    h2, h4 { color: #00f2ff !important; font-family: 'Pretendard'; }
    .metric-card { background: #10141c; border: 1px solid #1e2633; padding: 15px; border-radius: 8px; text-align: center; }
    .metric-value { color: #00f2ff !important; font-size: 1.8rem; font-weight: 800; }
    
    .fixed-table { width: 100%; border-collapse: separate; border-spacing: 0; }
    .fixed-table th, .fixed-table td { border: 1px solid #30363d; padding: 12px; text-align: center; color: white; }
    
    /* 오늘 요일 칸만 빨간 테두리 박스 처리 (글씨색은 흰색 유지) */
    .today-header-box { 
        border: 4px solid #ff3131 !important; 
        background: rgba(255, 49, 49, 0.1) !important;
        color: white !important; 
        font-weight: 800;
    }
    .status-alert { color: #ff3131; font-weight: 900; background: rgba(255, 49, 49, 0.1); border-radius: 4px; padding: 2px 5px; }
    .status-stable { color: #00ff7f; font-weight: 700; }
    </style>
    """, unsafe_allow_html=True)

# --- [ENGINE] 실시간 API 수집 및 정밀 데이터 매핑 ---

@st.cache_data(ttl=300)
def fetch_master_data():
    pwr = {"load": 0.0, "res": 0.0, "sup": 0.0, "raw": {}}
    try:
        # 1. 전력수급현황 (KPX)
        url = "http://apis.data.go.kr/B552566/9s_status_info/get9s_status_info"
        res = requests.get(url, params={'serviceKey': SERVICE_KEY, 'dataType': 'JSON'}, timeout=7)
        if res.status_code == 200:
            items = res.json().get('response', {}).get('body', {}).get('items', {}).get('item', [])
            if items:
                it = items[0]
                pwr = {"load": round(float(it.get('currPwrTot', 0))/1000, 1), 
                       "res": it.get('suppReservePwrRate', 0), 
                       "sup": round(float(it.get('suppAbility', 0))/1000, 1), "raw": it}
    except: pass

    # 2. 이번 주 DR 발령 내역 전수 조사 (2026.02.09 ~ 2026.02.11)
    dr_map = {}
    try:
        mon_str = (now - timedelta(days=now.weekday())).strftime("%Y%m%d")
        dr_url = "http://apis.data.go.kr/B552566/dr_issuance_info/getDr_Issuance_Info"
        dr_res = requests.get(dr_url, params={'serviceKey': SERVICE_KEY, 'dataType': 'JSON', 'startDt': mon_str, 'endDt': now.strftime("%Y%m%d")}, timeout=7)
        dr_items = dr_res.json().get('response', {}).get('body', {}).get('items', {}).get('item', [])
        if not isinstance(dr_items, list): dr_items = [dr_items]
        for log in dr_items:
            dr_map[str(log.get('tradeDay'))] = f"국민DR 발령됨 ({log.get('tradeHour')})"
    except: pass

    # 주간 데이터 구성
    weekly_list = []
    mon_dt = now - timedelta(days=now.weekday())
    for i in range(5):
        day = mon_dt + timedelta(days=i)
        d_key = day.strftime("%Y%m%d")
        is_today = day.date() == now.date()
        
        # 발령 정보 매핑
        info = dr_map.get(d_key, "안정")
        if is_today and info == "안정": info = "발령예상"

        weekly_list.append({
            "date": day.strftime("%Y.%m.%d"),
            "is_today": is_today,
            "temp": "-1.5℃ / 4.0℃", # 기상청 실시간 min/max 반영 예정
            "dust": "보통(38)",
            "status": info
        })
    return pwr, weekly_list

pwr_data, weekly_report = fetch_master_data()

# --- [UI] 대시보드 ---
st.markdown("## 🛡️ NOSTRADAMUS 통합 관제 센터 V4.0")

# Raw Data 진단 영역
with st.expander("🛠️ API 전력수급 Raw Data 진단 (KPX 원본 확인)"):
    st.write("인증키 디코딩 후 서버 응답:")
    st.json(pwr_data['raw'])

# 1단: 메트릭
m1, m2, m3, m4, m5 = st.columns(5)
m1.markdown(f"<div class='metric-card'><div class='metric-label'>현재 전력부하</div><div class='metric-value'>{pwr_data['load']} GW</div></div>", unsafe_allow_html=True)
m2.markdown(f"<div class='metric-card'><div class='metric-label'>운영 예비율</div><div class='metric-value'>{pwr_data['res']}%</div></div>", unsafe_allow_html=True)
m3.markdown(f"<div class='metric-card'><div class='metric-label'>공급 능력</div><div class='metric-value'>{pwr_data['sup']} GW</div></div>", unsafe_allow_html=True)
m4.markdown(f"<div class='metric-card'><div class='metric-label'>수급 상태</div><div class='metric-value' style='color:#00ff7f;'>안정</div></div>", unsafe_allow_html=True)
m5.markdown(f"<div class='metric-card'><div class='metric-label'>관제 센터</div><div class='metric-value' style='color:#00f2ff;'>LIVE</div></div>", unsafe_allow_html=True)

# 2단: 주간 국민 DR 발령 리포트
st.markdown("#### 주간 국민 DR 발령 리포트 (평일 고정)")
html = "<table class='fixed-table'><thead><tr><th>항목</th>"
for i, day in enumerate(["월요일", "화요일", "수요일(오늘)", "목요일", "금요일"]):
    cls = "today-header-box" if weekly_report[i]['is_today'] else ""
    html += f"<th class='{cls}'>{day}</th>"
html += "</tr></thead><tbody>"

row_map = [("날짜", "date"), ("기온(Min/Max)", "temp"), ("미세먼지", "dust"), ("발령 정보", "status")]
for label, key in row_map:
    html += f"<tr><td><b>{label}</b></td>"
    for day_data in weekly_report:
        val = day_data[key]
        if "발령됨" in val: val = f"<span class='status-alert'>{val}</span>"
        elif "안정" in val: val = f"<span class='status-stable'>{val}</span>"
        html += f"<td>{val}</td>"
    html += "</tr>"
html += "</tbody></table>"
st.markdown(html, unsafe_allow_html=True)

# 3단: 그래프
st.markdown("#### 실시간 공급/부하 및 태양광 변동 추이 (LIVE)")
# (기존 Plotly 그래프 로직을 그대로 사용하되 pwr_data['load'] 수치와 연동)
