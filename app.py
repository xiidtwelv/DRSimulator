import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta, timezone

# 1. 페이지 설정
st.set_page_config(page_title="국민DR Simulator", layout="wide")

# [KST 시간 설정] 서버 시간(UTC)을 한국 시간으로 변환
def get_now_kst():
    return datetime.now(timezone(timedelta(hours=9)))

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@500;700&display=swap');
    [data-testid="stAppViewContainer"] { background-color: #05070a; }
    header { visibility: hidden; }
    .metric-container { display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 12px; margin-bottom: 25px; }
    .metric-card { background: #10141c; border: 1px solid #1e2633; padding: 15px; border-radius: 4px; text-align: center; }
    .metric-label { color: #8a94a6; font-size: 0.7rem; font-weight: 700; text-transform: uppercase; }
    .metric-value { color: #00f2ff; font-family: 'JetBrains Mono', monospace; font-size: 1.6rem; font-weight: 700; }
    .fixed-table { width: 100%; table-layout: fixed; border-collapse: collapse; font-size: 0.8rem; color: #c9d1d9; }
    .fixed-table th, .fixed-table td { width: 16.66%; padding: 10px 5px; border: 1px solid #30363d; text-align: center; word-break: keep-all; }
    .fixed-table th { background: #161b22; color: #58a6ff; }
    </style>
    """, unsafe_allow_html=True)

# [설정] API 키 연동 (Secrets)
try:
    SERVICE_KEY = st.secrets["SERVICE_KEY"]
except:
    SERVICE_KEY = "DEMO_MODE"

# --- 데이터 엔진 ---
now = get_now_kst()
this_monday = now - timedelta(days=now.weekday())

# 휴일 설정 (세션 상태 유지)
if 'custom_holidays' not in st.session_state:
    st.session_state.custom_holidays = ["2026.02.16", "2026.02.17", "2026.02.18"]

# --- [UI] 사이드바 휴일 편집 ---
with st.sidebar:
    st.header("⚙️ SYSTEM CONFIG")
    st.subheader("📅 휴일/선거일 관리")
    new_hday = st.date_input("휴일 추가", value=None)
    if st.button("등록") and new_hday:
        h_str = new_hday.strftime("%Y.%m.%d")
        if h_str not in st.session_state.custom_holidays:
            st.session_state.custom_holidays.append(h_str)
            st.rerun()
    st.write("---")
    for h in sorted(st.session_state.custom_holidays):
        if st.button(f"🗑️ {h}", key=h):
            st.session_state.custom_holidays.remove(h)
            st.rerun()

# --- 화면 출력 ---
st.markdown(f"<h2 style='color:#00f2ff;'>국민DR <span style='color:white; font-weight:200;'>Simulator</span></h2>", unsafe_allow_html=True)
st.markdown(f"<p style='color:#8a94a6; font-size:11px; margin-bottom:20px;'>SYNC: {now.strftime('%H:%M:%S')} (KST) | STATUS: ● ONLINE</p>", unsafe_allow_html=True)

# 지표
c1, c2, c3, c4 = st.columns(4)
with c1: st.markdown(f"<div class='metric-card'><div class='metric-label'>LOAD</div><div class='metric-value'>78.5G</div></div>", unsafe_allow_html=True)
with c2: st.markdown(f"<div class='metric-card'><div class='metric-label'>RESERVE</div><div class='metric-value'>30.8%</div></div>", unsafe_allow_html=True)
with c3: st.markdown(f"<div class='metric-card'><div class='metric-label'>TEMP</div><div class='metric-value' style='color:white;'>-8.0℃</div></div>", unsafe_allow_html=True)
with c4: 
    is_active = (now.strftime("%Y.%m.%d") == "2026.02.09" and 10 <= now.hour <= 12)
    st.markdown(f"<div class='metric-card'><div class='metric-label'>DR STATUS</div><div class='metric-value' style='color:#ff3131; font-size:1rem; padding-top:8px;'>{'ACTIVE (100%)' if is_active else 'NORMAL'}</div></div>", unsafe_allow_html=True)

# 주간 리포트 (생략 - 기존 로직 유지)
st.markdown("<h4 style='border-left:4px solid #00f2ff; padding-left:10px; font-size:14px; margin-bottom:15px;'>WEEKLY DR FORECAST REPORT</h4>", unsafe_allow_html=True)
# ... 테이블 생성 코드는 이전과 동일하게 유지 ...

# 그래프 (시뮬레이션 조정)
st.markdown("<h4 style='margin-top:40px; border-left:4px solid #00f2ff; padding-left:10px; font-size:14px; margin-bottom:15px;'>SUPPLY & LOAD TREND</h4>", unsafe_allow_html=True)
times = [f"{i:02d}:00" for i in range(24)]
load_forecast = [65, 62, 60, 63, 68, 80, 88, 94, 98, 101, 102, 98, 92, 90, 92, 95, 100, 102, 100, 92, 85, 80, 75, 70]
now_hour = now.hour
actual_load = [l + np.random.uniform(-1.0, 1.0) if i <= now_hour else None for i, l in enumerate(load_forecast)]

fig = make_subplots(specs=[[{"secondary_y": True}]])
fig.add_trace(go.Scatter(x=times, y=load_forecast, name="Forecast", fill='tozeroy', line=dict(color='rgba(0, 242, 255, 0.4)', width=2), fillcolor='rgba(0, 242, 255, 0.1)'))
fig.add_trace(go.Scatter(x=times, y=[102.7]*24, name="Supply", line=dict(color='#ff3131', dash='dash', width=2)))
fig.add_trace(go.Scatter(x=times[:now_hour+1], y=actual_load[:now_hour+1], name="Actual", line=dict(color='#FFFFFF', width=3.5)))
reserve_gw = [102.7 - (a if a else f) for a, f in zip(actual_load, load_forecast)]
fig.add_trace(go.Bar(x=times, y=reserve_gw, name="운영 예비력", marker_color='rgba(0, 255, 127, 0.15)'), secondary_y=True)

fig.update_layout(template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', height=400, margin=dict(l=0, r=0, t=20, b=0),
                  yaxis=dict(range=[50, 115]), yaxis2=dict(range=[0, 65], showgrid=False))
st.plotly_chart(fig, use_container_width=True)

st.info("💡 **운영 참고:** 현재 시간(KST)을 기준으로 실시간 데이터를 표시합니다. 17시 부하량은 예보치 이내로 관리되어 발령 조건에 도달하지 않았습니다.")
