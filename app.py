import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta, timezone

# 1. 페이지 설정 및 다크 테마 커스텀 스타일
st.set_page_config(page_title="국민DR Simulator", layout="wide", initial_sidebar_state="expanded")

# 한국 시간(KST) 설정
def get_now_kst():
    return datetime.now(timezone(timedelta(hours=9)))

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@500;700&display=swap');
    
    /* 배경 및 기본 폰트 설정 */
    [data-testid="stAppViewContainer"] { background-color: #05070a; }
    [data-testid="stSidebar"] { background-color: #0d1117; border-right: 1px solid #30363d; }
    
    /* 텍스트 크기 강제 고정 (가독성 확보) */
    .stMarkdown, p, span, label { font-size: 1rem !important; color: #ffffff !important; }
    h2 { font-size: 2rem !important; color: #00f2ff !important; margin-bottom: 0 !important; }
    h4 { font-size: 1.2rem !important; color: #00f2ff !important; margin-top: 2rem !important; border-left: 4px solid #00f2ff; padding-left: 10px; }
    
    /* 메트릭 카드 디자인 */
    .metric-card {
        background: #10141c;
        border: 1px solid #1e2633;
        padding: 20px;
        border-radius: 8px;
        text-align: center;
        margin-bottom: 10px;
    }
    .metric-label { color: #8a94a6 !important; font-size: 0.8rem !important; font-weight: 700; }
    .metric-value { color: #00f2ff !important; font-family: 'JetBrains Mono', monospace; font-size: 2rem !important; font-weight: 700; }
    
    /* 테이블 스타일 고정 */
    .fixed-table { width: 100%; border-collapse: collapse; margin-top: 10px; table-layout: fixed; }
    .fixed-table th { background: #161b22; color: #58a6ff !important; padding: 12px; border: 1px solid #30363d; font-size: 0.9rem; }
    .fixed-table td { padding: 12px; border: 1px solid #30363d; text-align: center; color: #c9d1d9 !important; font-size: 0.85rem; }
    .highlight-dr { color: #ff3131 !important; font-weight: 800; }
    </style>
    """, unsafe_allow_html=True)

# [설정] API 키 연동
try:
    SERVICE_KEY = st.secrets["SERVICE_KEY"]
except:
    SERVICE_KEY = "DEMO_MODE"

# --- 데이터 준비 ---
now = get_now_kst()
this_monday = now - timedelta(days=now.weekday())

# 휴일 설정 세션 상태
if 'custom_holidays' not in st.session_state:
    st.session_state.custom_holidays = ["2026.02.16", "2026.02.17", "2026.02.18"]

# --- [사이드바] 휴일 편집 ---
with st.sidebar:
    st.markdown("### ⚙️ SYSTEM CONFIG")
    st.markdown("#### 📅 휴일 및 선거일 관리")
    new_hday = st.date_input("휴일 추가", value=None)
    if st.button("즉시 등록") and new_hday:
        h_str = new_hday.strftime("%Y.%m.%d")
        if h_str not in st.session_state.custom_holidays:
            st.session_state.custom_holidays.append(h_str)
            st.rerun()
    
    st.write("---")
    st.caption("등록된 휴일 목록 (클릭 시 삭제)")
    for h in sorted(st.session_state.custom_holidays):
        if st.button(f"🗑️ {h}", key=h):
            st.session_state.custom_holidays.remove(h)
            st.rerun()

# --- [화면 상단] 헤더 및 지표 ---
st.markdown(f"<h2>국민DR <span style='color:white; font-weight:200;'>Simulator</span></h2>", unsafe_allow_html=True)
st.markdown(f"<p style='color:#8a94a6 !important; font-size:0.8rem !important;'>LAST SYNC: {now.strftime('%Y-%m-%d %H:%M:%S')} (KST) | STATUS: ● ONLINE</p>", unsafe_allow_html=True)

m1, m2, m3, m4 = st.columns(4)
with m1: st.markdown(f"<div class='metric-card'><div class='metric-label'>CURRENT LOAD</div><div class='metric-value'>78.5G</div></div>", unsafe_allow_html=True)
with m2: st.markdown(f"<div class='metric-card'><div class='metric-label'>RESERVE RATE</div><div class='metric-value'>30.8%</div></div>", unsafe_allow_html=True)
with m3: st.markdown(f"<div class='metric-card'><div class='metric-label'>MIN TEMP</div><div class='metric-value' style='color:white !important;'>-8.0℃</div></div>", unsafe_allow_html=True)
with m4:
    is_active = (now.strftime("%Y.%m.%d") == "2026.02.09" and 10 <= now.hour <= 12)
    status_color = "#ff3131" if is_active else "#8a94a6"
    status_text = "DR ACTIVE (100%)" if is_active else "NORMAL"
    st.markdown(f"<div class='metric-card'><div class='metric-label'>DR STATUS</div><div class='metric-value' style='color:{status_color} !important; font-size:1.2rem !important; padding-top:10px;'>{status_text}</div></div>", unsafe_allow_html=True)

# --- [주간 리포트] ---
st.markdown("#### WEEKLY DR FORECAST REPORT")

# 테이블 데이터 생성
week_days = ["월(MON)", "화(TUE)", "수(WED)", "목(THU)", "금(FRI)"]
table_rows = ["DATE", "AIR QUALITY", "TEMP(MIN/MAX)", "PROBABILITY", "DETAILS"]
table_content = "<table class='fixed-table'><thead><tr><th>ITEM</th>"
for wd in week_days: table_content += f"<th>{wd}</th>"
table_content += "</tr></thead><tbody>"

for row_label in table_rows:
    table_content += f"<tr><td><b>{row_label}</b></td>"
    for i in range(5):
        day_obj = this_monday + timedelta(days=i)
        d_str = day_obj.strftime("%Y.%m.%d")
        is_hday = d_str in st.session_state.custom_holidays or day_obj.weekday() >= 5
        
        if row_label == "DATE": val = d_str
        elif row_label == "AIR QUALITY": val = "나쁨" if i == 2 else "보통"
        elif row_label == "TEMP(MIN/MAX)": val = "-8.0° / 5.0°" if i == 0 else "예보 확인중"
        elif row_label == "PROBABILITY": val = "0%" if is_hday else ("100%" if d_str == "2026.02.09" else "20%")
        elif row_label == "DETAILS":
            if d_str == "2026.02.09": val = "<span class='highlight-dr'>DR발령됨(10:00)</span>"
            elif is_hday: val = "휴일(발령없음)"
            else: val = "평시 수급 안정"
        
        table_content += f"<td>{val}</td>"
    table_content += "</tr>"
table_content += "</tbody></table>"

st.markdown(table_content, unsafe_allow_html=True)

# --- [그래프 분석] ---
st.markdown("#### REAL-TIME SUPPLY & LOAD ANALYSIS")

times = [f"{i:02d}:00" for i in range(24)]
load_forecast = [65, 62, 60, 63, 68, 80, 88, 94, 98, 101, 102, 98, 92, 90, 92, 95, 100, 102, 100, 92, 85, 80, 75, 70]
now_hour = now.hour
actual_load = [l + np.random.uniform(-1.0, 1.0) if i <= now_hour else None for i, l in enumerate(load_forecast)]
reserve_gw = [102.7 - (a if a is not None else f) for a, f in zip(actual_load, load_forecast)]

fig = make_subplots(specs=[[{"secondary_y": True}]])
fig.add_trace(go.Scatter(x=times, y=load_forecast, name="Forecast", fill='tozeroy', line=dict(color='rgba(0, 242, 255, 0.4)', width=2), fillcolor='rgba(0, 242, 255, 0.1)'))
fig.add_trace(go.Scatter(x=times, y=[102.7]*24, name="Supply", line=dict(color='#ff3131', dash='dash', width=2)))
fig.add_trace(go.Scatter(x=times[:now_hour+1], y=actual_load[:now_hour+1], name="Actual", line=dict(color='#FFFFFF', width=4), mode='lines+markers'))
fig.add_trace(go.Bar(x=times, y=reserve_gw, name="Reserve (GW)", marker_color='rgba(0, 255, 127, 0.2)'), secondary_y=True)

fig.update_layout(template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', height=450, margin=dict(l=0, r=0, t=30, b=0),
                  yaxis=dict(range=[50, 115]), yaxis2=dict(range=[0, 65], showgrid=False), hovermode="x unified")
st.plotly_chart(fig, use_container_width=True)

st.info("💡 **운영 참고:** 현재 한국 시간(KST)을 기준으로 실시간 데이터를 분석 중입니다. 사이드바가 보이지 않으면 왼쪽 상단의 '>' 화살표를 눌러주세요.")
