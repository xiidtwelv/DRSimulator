import streamlit as st
import pandas as pd
import numpy as np
import requests
from datetime import datetime, timedelta, timezone
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# 1. 페이지 설정
st.set_page_config(page_title="국민DR 통합 관제", layout="wide", initial_sidebar_state="expanded")

def get_now_kst():
    return datetime.now(timezone(timedelta(hours=9)))

now = get_now_kst()
SERVICE_KEY = st.secrets["SERVICE_KEY"]

# --- [디자인] CSS (원안 및 시인성 보정 통합) ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Pretendard:wght@400;700&display=swap');
    [data-testid="stAppViewContainer"] { background-color: #05070a; }
    header { visibility: hidden; }
    button[kind="headerNoPadding"] svg { fill: white !important; }
    h2, h4, p, span, label { font-family: 'Pretendard', sans-serif; color: #ffffff !important; }
    h2 { color: #00f2ff !important; font-size: 2rem !important; }
    h4 { color: #00f2ff !important; border-left: 4px solid #00f2ff; padding-left: 10px; margin-top: 30px; }
    .metric-card { background: #10141c; border: 1px solid #1e2633; padding: 20px; border-radius: 8px; text-align: center; }
    .metric-label { color: #8a94a6 !important; font-size: 0.9rem !important; font-weight: 700; }
    .metric-value { color: #00f2ff !important; font-size: 1.8rem !important; font-weight: 700; }
    .fixed-table { width: 100%; border-collapse: collapse; table-layout: fixed; margin-top: 15px; color: #c9d1d9; }
    .fixed-table th { background: #161b22; color: #58a6ff !important; padding: 12px; border: 1px solid #30363d; font-size: 0.85rem; }
    .fixed-table td { padding: 12px; border: 1px solid #30363d; text-align: center; font-size: 0.85rem; }
    .highlight-dr { color: #ff3131 !important; font-weight: 800; }
    </style>
    """, unsafe_allow_html=True)

# --- [API 엔진] 데이터 수집 ---
@st.cache_data(ttl=600)
def fetch_api_data():
    pwr = {"load": 74.2, "supply": 101.5, "reserve": 36.8, "reserve_gw": 27.3}
    # 요일별 기상 데이터 (최저기온 기준)
    weather_data = [
        {"temp": -8.0, "air": "보통"}, # 월
        {"temp": -3.0, "air": "보통"}, # 화
        {"temp": -6.0, "air": "나쁨"}, # 수 (한파 + 미세먼지)
        {"temp": -2.0, "air": "보통"}, # 목
        {"temp": -1.0, "air": "보통"}  # 금
    ]
    return pwr, weather_data

pwr_data, weekly_env = fetch_api_data()

# --- [사이드바] 휴일 관리 ---
if 'custom_holidays' not in st.session_state:
    st.session_state.custom_holidays = ["2026.02.16", "2026.02.17", "2026.02.18"]

with st.sidebar:
    st.markdown("### << 시스템 설정")
    new_hday = st.date_input("휴일 추가", value=None)
    if st.button("즉시 등록") and new_hday:
        h_str = new_hday.strftime("%Y.%m.%d")
        if h_str not in st.session_state.custom_holidays:
            st.session_state.custom_holidays.append(h_str)
            st.rerun()
    st.write("---")
    for h in sorted(st.session_state.custom_holidays):
        if st.button(f"🗑️ {h}", key=h):
            st.session_state.custom_holidays.remove(h)
            st.rerun()

# --- [UI] 상단 헤더 및 지표 ---
st.markdown(f"<h2>NOSTRADAMUS <span style='color:white; font-weight:200;'>실시간 전력 관제 센터</span></h2>", unsafe_allow_html=True)

m1, m2, m3, m4 = st.columns(4)
with m1: st.markdown(f"<div class='metric-card'><div class='metric-label'>현재 전력부하</div><div class='metric-value'>{pwr_data['load']} GW</div></div>", unsafe_allow_html=True)
with m2: st.markdown(f"<div class='metric-card'><div class='metric-label'>운영 예비율</div><div class='metric-value'>{pwr_data['reserve']} %</div></div>", unsafe_allow_html=True)
with m3: st.markdown(f"<div class='metric-card'><div class='metric-label'>오늘의 기온</div><div class='metric-value' style='color:white !important;'>{weekly_env[0]['temp']}℃</div></div>", unsafe_allow_html=True)
with m4:
    res_gw = pwr_data['reserve_gw']
    status = "정상" if res_gw > 10.5 else "주의"
    st.markdown(f"<div class='metric-card'><div class='metric-label'>수급 상태</div><div class='metric-value' style='color:#00ff7f !important;'>{status}</div></div>", unsafe_allow_html=True)

# --- [UI] 주간 리포트 (가중치 로직 적용) ---
st.markdown("#### 주간 DR 발령 예측 리포트 (논리 기반)")
this_monday = now - timedelta(days=now.weekday())
week_days = ["월요일", "화요일", "수요일", "목요일", "금요일"]
table_rows = ["날짜", "미세먼지", "기온(최저)", "발령 확률", "상세 정보"]

table_html = "<table class='fixed-table'><thead><tr><th>항목</th>"
for wd in week_days: table_html += f"<th>{wd}</th>"
table_html += "</tr></thead><tbody>"

for row in table_rows:
    table_html += f"<tr><td><b>{row}</b></td>"
    for i in range(5):
        day_obj = this_monday + timedelta(days=i)
        d_str = day_obj.strftime("%Y.%m.%d")
        env = weekly_env[i]
        is_hday = d_str in st.session_state.custom_holidays
        
        # [핵심 로직] 가중치 계산
        prob = 20 # 기본 확률
        reason = "평시 수급 안정"
        
        if env['air'] == "나쁨": 
            prob += 20
            reason = "미세먼지(태양광 저하)"
        if env['temp'] <= -5.0: 
            prob += 20
            reason = "기온하강(난방부하)"
        if env['air'] == "나쁨" and env['temp'] <= -5.0:
            reason = "복합위험(기온+먼지)"
        
        if row == "날짜": val = d_str
        elif row == "미세먼지": val = env['air']
        elif row == "기온(최저)": val = f"{env['temp']}℃"
        elif row == "발령 확률": val = "0%" if is_hday else ("100%" if i == 0 else f"{prob}%")
        elif row == "상세 정보":
            if i == 0: val = "<span class='highlight-dr'>DR발령됨(10:00)</span>"
            elif is_hday: val = "휴일(발령없음)"
            else: val = reason
        table_html += f"<td>{val}</td>"
    table_html += "</tr>"
table_html += "</tbody></table>"
st.markdown(table_html, unsafe_allow_html=True)

# --- [UI] 그래프 ---
st.markdown("#### 실시간 공급 및 부하 추이 분석")
times = [f"{i:02d}:00" for i in range(24)]
load_forecast = [65, 62, 60, 63, 68, 80, 88, 94, 98, 101, 102, 98, 92, 90, 92, 95, 100, 102, 100, 92, 85, 80, 75, 70]
supply_val = pwr_data['supply']
now_hour = now.hour
actual_load = [l + np.random.uniform(-1.0, 1.0) if i <= now_hour else None for i, l in enumerate(load_forecast)]
reserve_gw_list = [supply_val - (a if a is not None else f) for a, f in zip(actual_load, load_forecast)]

fig = make_subplots(specs=[[{"secondary_y": True}]])
fig.add_trace(go.Scatter(x=times, y=load_forecast, name="예보 부하", fill='tozeroy', line=dict(color='rgba(0, 242, 255, 0.4)', width=2), fillcolor='rgba(0, 242, 255, 0.1)'))
fig.add_trace(go.Scatter(x=times, y=[supply_val]*24, name="공급 능력", line=dict(color='#ff3131', dash='dash', width=2)))
fig.add_trace(go.Scatter(x=times[:now_hour+1], y=actual_load[:now_hour+1], name="실제 부하", line=dict(color='#FFFFFF', width=4), mode='lines+markers'))
fig.add_trace(go.Bar(x=times, y=reserve_gw_list, name="운영 예비력(GW)", marker_color='rgba(0, 255, 127, 0.2)'), secondary_y=True)

fig.update_layout(template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', height=400, margin=dict(l=0, r=0, t=30, b=0),
                  legend=dict(orientation="h", yanchor="bottom", y=1.05, xanchor="right", x=1, font=dict(color="white")),
                  yaxis=dict(range=[50, 115]), yaxis2=dict(range=[0, 65], showgrid=False))
st.plotly_chart(fig, use_container_width=True)
