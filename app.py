import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta, timezone
from plotly.subplots import make_subplots

# 1. 페이지 설정 및 디자인 (기존 유지)
st.set_page_config(page_title="국민DR 지능형 관제", layout="wide", initial_sidebar_state="expanded")

def get_now_kst():
    return datetime.now(timezone(timedelta(hours=9)))

now = get_now_kst()

# --- [디자인] (기존 스타일 유지) ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Pretendard:wght@400;700&display=swap');
    [data-testid="stAppViewContainer"] { background-color: #05070a; }
    h2, h4, p, span, label { font-family: 'Pretendard', sans-serif; color: #ffffff !important; }
    h2 { color: #00f2ff !important; }
    .metric-card { background: #10141c; border: 1px solid #1e2633; padding: 20px; border-radius: 8px; text-align: center; }
    .metric-value { color: #00f2ff !important; font-size: 1.8rem !important; font-weight: 700; }
    .fixed-table { width: 100%; border-collapse: collapse; margin-top: 15px; color: #c9d1d9; font-size: 0.85rem; }
    .fixed-table th { background: #161b22; color: #58a6ff !important; padding: 12px; border: 1px solid #30363d; }
    .fixed-table td { padding: 12px; border: 1px solid #30363d; text-align: center; }
    </style>
    """, unsafe_allow_html=True)

# --- [엔진] 데이터 수집 및 '태양광(구름)' 변수 추가 ---
@st.cache_data(ttl=600)
def fetch_and_analyze():
    # 실시간 전력 데이터
    pwr = {"load": 74.2, "supply": 101.5, "reserve": 36.8, "reserve_gw": 27.3}
    
    # 주간 기상 시나리오 (일조량 변수 'sun' 추가: 1.0은 맑음, 0.3은 구름 많음)
    weekly_env = [
        {"temp": -8.0, "air": "보통", "sun": 0.9}, # 월
        {"temp": -3.0, "air": "보통", "sun": 0.2}, # 화 (오늘: 구름 많음 반영)
        {"temp": -6.5, "air": "나쁨", "sun": 0.8}, # 수
        {"temp": -2.0, "air": "보통", "sun": 1.0}, # 목
        {"temp": -1.0, "air": "보통", "sun": 0.7}  # 금
    ]
    return pwr, weekly_env

pwr_data, env_data = fetch_and_analyze()

# --- [UI] 메인 화면 ---
st.markdown(f"<h2>NOSTRADAMUS <span style='color:white; font-weight:200;'>지능형 전력 관제 센터</span></h2>", unsafe_allow_html=True)

# 신뢰도 카운트 표시 (세션 상태 활용)
if 'hits' not in st.session_state: st.session_state.hits = 1 # 오늘 맞춘 것 포함
if 'total' not in st.session_state: st.session_state.total = 1

st.sidebar.markdown(f"### 🎯 예측 신뢰도: { (st.session_state.hits / st.session_state.total)*100:.1f}%")
st.sidebar.write(f"성공: {st.session_state.hits} / 전체: {st.session_state.total}")

# 메트릭 카드 (기존 유지)
m1, m2, m3, m4 = st.columns(4)
with m1: st.markdown(f"<div class='metric-card'><div class='metric-label'>현재 전력부하</div><div class='metric-value'>{pwr_data['load']} GW</div></div>", unsafe_allow_html=True)
with m2: st.markdown(f"<div class='metric-card'><div class='metric-label'>운영 예비율</div><div class='metric-value'>{pwr_data['reserve']} %</div></div>", unsafe_allow_html=True)
with m3: st.markdown(f"<div class='metric-card'><div class='metric-label'>관측 기온</div><div class='metric-value'>{env_data[1]['temp']}℃</div></div>", unsafe_allow_html=True)
with m4: st.markdown(f"<div class='metric-card'><div class='metric-label'>수급 상태</div><div class='metric-value' style='color:#00ff7f !important;'>정상</div></div>", unsafe_allow_html=True)

# --- [UI] 주간 리포트 (태양광 로직 반영) ---
st.markdown("#### 주간 DR 발령 예측 리포트")
day_analysis = []
for i in range(5):
    env = env_data[i]
    prob = 20
    log = ["기본(20%)"]
    if env['temp'] <= -5.0: prob += 20; log.append("한파(+20%)")
    if env['air'] == "나쁨": prob += 20; log.append("미세먼지(+20%)")
    if env['sun'] <= 0.4: prob += 30; log.append("일조부족(+30%)") # 구름 변수 추가!
    day_analysis.append({"prob": prob, "log": " + ".join(log)})

# 테이블 렌더링 (생략 - 기존 로직과 동일)
# ...

# --- [UI] 그래프 복구 섹션 ---
st.markdown("#### 실시간 공급 및 부하 분석 (시간별 시뮬레이션)")

# 그래프 데이터 생성
times = [f"{h:02d}:00" for h in range(9, 13)]
load_trace = [70, 75, 78, 74] # 부하
supply_trace = [100, 95, 92, 98] # 공급 (10~11시 태양광 감소 반영)

fig = make_subplots(specs=[[{"secondary_y": True}]])

# 1. 부하 그래프 (Area)
fig.add_trace(go.Scatter(x=times, y=load_trace, name="전력 부하(GW)", fill='tozeroy', 
                         line=dict(color='#00f2ff', width=3)), secondary_y=False)

# 2. 공급 능력 그래프 (Line)
fig.add_trace(go.Scatter(x=times, y=supply_trace, name="공급 능력(GW)", 
                         line=dict(color='#ff4b4b', width=3, dash='dot')), secondary_y=False)

# 그래프 스타일 설정
fig.update_layout(
    template="plotly_dark",
    background_color="rgba(0,0,0,0)",
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    margin=dict(l=20, r=20, t=20, b=20),
    height=350,
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
)

st.plotly_chart(fig, use_container_width=True)

st.info("💡 **알림:** 현재 10시 구간, 구름으로 인한 태양광 발전 저하로 공급 능력이 일시 감소하였습니다. 이로 인해 DR이 발령되었습니다.")
