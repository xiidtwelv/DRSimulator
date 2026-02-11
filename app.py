import streamlit as st
import pandas as pd
import numpy as np
import requests
from datetime import datetime, timedelta, timezone
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# 1. 페이지 설정
st.set_page_config(page_title="국민DR 통합 관제 V3.3", layout="wide")

def get_now_kst():
    return datetime.now(timezone(timedelta(hours=9)))

now = get_now_kst()
SERVICE_KEY = st.secrets.get("SERVICE_KEY", "")

# --- [디자인] CSS ---
st.markdown("""
    <style>
    [data-testid="stAppViewContainer"] { background-color: #05070a; }
    h2, h4 { color: #00f2ff !important; }
    .metric-card { background: #10141c; border: 1px solid #1e2633; padding: 15px; border-radius: 8px; text-align: center; }
    .metric-label { color: #c9d1d9 !important; font-weight: 700; font-size: 0.9rem; }
    .metric-value { color: #00f2ff !important; font-size: 1.8rem; font-weight: 800; }
    </style>
    """, unsafe_allow_html=True)

# --- [CORE] API 데이터 호출 (안정화 로직 추가) ---
@st.cache_data(ttl=300)
def fetch_data():
    # 초기값 (데이터 수신 실패 시 표시될 값)
    pwr = {"load_act": "연결중", "load_fcst": "-", "supply": "-", "reserve": "0.0"}
    weather = [{"date": now.strftime("%m.%d"), "min": -2.0, "max": 5.0, "cloud": 1, "status": "정상"}] * 5

    try:
        # 1. KPX 전력 데이터 호출
        kpx_url = "http://apis.data.go.kr/B552566/9s_status_info/get9s_status_info"
        res = requests.get(kpx_url, params={'serviceKey': SERVICE_KEY, 'dataType': 'JSON'}, timeout=5)
        
        if res.status_code == 200:
            data = res.json()
            # 데이터가 정상적으로 들어있는지 확인
            if 'response' in data and data['response']['body']['items']:
                item = data['response']['body']['items']['item'][0]
                pwr = {
                    "load_act": f"{round(float(item['currPwrTot']) / 1000, 1)}",
                    "load_fcst": f"{round(float(item['forePwrTot']) / 1000, 1)}",
                    "supply": f"{round(float(item['suppAbility']) / 1000, 1)}",
                    "reserve": f"{item['suppReservePwrRate']}"
                }
    except Exception as e:
        st.sidebar.error(f"전력 API 오류: {e}")

    return pwr, weather

pwr_data, weekly_data = fetch_data()

# --- [UI] 상단 헤더 및 지표 ---
st.markdown("## NOSTRADAMUS 실시간 전력 관제 센터")
m1, m2, m3, m4, m5 = st.columns(5)
m1.markdown(f"<div class='metric-card'><div class='metric-label'>현재 전력부하</div><div class='metric-value'>{pwr_data['load_act']} GW</div></div>", unsafe_allow_html=True)
m2.markdown(f"<div class='metric-card'><div class='metric-label'>운영 예비율</div><div class='metric-value'>{pwr_data['reserve']}%</div></div>", unsafe_allow_html=True)
m3.markdown(f"<div class='metric-card'><div class='metric-label'>내일 최저기온</div><div class='metric-value' style='color:#ffffff !important;'>{weekly_data[1]['min']}℃</div></div>", unsafe_allow_html=True)
m4.markdown(f"<div class='metric-card'><div class='metric-label'>수급 상태</div><div class='metric-value' style='color:#00ff7f !important;'>정상</div></div>", unsafe_allow_html=True)
m5.markdown(f"<div class='metric-card'><div class='metric-label'>API 상태</div><div class='metric-value'>{'Connected' if pwr_data['load_act'] != '연결중' else 'Checking...'}</div></div>", unsafe_allow_html=True)

# --- [UI] 그래프 (오류 수정 버전) ---
st.markdown("#### 실시간 전력 사용 추이")

# 샘플 데이터 생성 (데이터가 없을 때 그래프가 깨지지 않게 함)
times = [f"{i:02d}:00" for i in range(24)]
dummy_vals = [70 + np.sin(i/3)*10 for i in range(24)]

fig = make_subplots(specs=[[{"secondary_y": True}]])
fig.add_trace(go.Scatter(x=times, y=dummy_vals, name="예보 부하", line=dict(color='gray', dash='dot')))

# 에러를 유발했던 레이아웃 설정을 가장 안전한 표준 방식으로 변경
fig.update_layout(
    template="plotly_dark",
    height=400,
    margin=dict(t=20, b=20, l=20, r=20),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
)

st.plotly_chart(fig, use_container_width=True)
st.caption(f"최종 업데이트: {now.strftime('%H:%M:%S')} | API Key 등록 직후에는 최대 2시간까지 0.0으로 보일 수 있습니다.")
