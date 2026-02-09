import streamlit as st
import pandas as pd
import numpy as np
import requests
from datetime import datetime, timedelta, timezone
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# 1. 페이지 설정 (사이드바 기본 확장 상태)
st.set_page_config(page_title="국민DR 통합 관제", layout="wide", initial_sidebar_state="expanded")

def get_now_kst():
    return datetime.now(timezone(timedelta(hours=9)))

now = get_now_kst()
SERVICE_KEY = st.secrets["SERVICE_KEY"]

# --- [디자인] CSS 보정 (사이드바 아이콘 및 글자색) ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Pretendard:wght@400;700&display=swap');
    [data-testid="stAppViewContainer"] { background-color: #05070a; }
    header { visibility: hidden; }
    
    /* 사이드바 토글 아이콘 흰색으로 강제 고정 */
    button[kind="headerNoPadding"] svg { fill: white !important; }
    
    h2, h4, p, span, label { font-family: 'Pretendard', sans-serif; color: #ffffff !important; }
    h2 { color: #00f2ff !important; font-size: 2rem !important; }
    h4 { color: #00f2ff !important; border-left: 4px solid #00f2ff; padding-left: 10px; margin-top: 30px; }
    
    /* 지표 카드 디자인 */
    .metric-card { background: #10141c; border: 1px solid #1e2633; padding: 20px; border-radius: 8px; text-align: center; }
    .metric-label { color: #8a94a6 !important; font-size: 0.9rem !important; font-weight: 700; }
    .metric-value { color: #00f2ff !important; font-size: 1.8rem !important; font-weight: 700; }
    
    /* 테이블 디자인 */
    .fixed-table { width: 100%; border-collapse: collapse; table-layout: fixed; margin-top: 15px; color: #c9d1d9; }
    .fixed-table th { background: #161b22; color: #58a6ff !important; padding: 12px; border: 1px solid #30363d; font-size: 0.85rem; }
    .fixed-table td { padding: 12px; border: 1px solid #30363d; text-align: center; font-size: 0.85rem; }
    .highlight-dr { color: #ff3131 !important; font-weight: 800; }
    </style>
    """, unsafe_allow_html=True)

# --- [API 엔진] 데이터 수집 ---
@st.cache_data(ttl=600)
def fetch_api_data():
    # 실제 API 연동 시 주석 해제하여 사용
    pwr = {"load": 74.2, "supply": 101.5, "reserve": 36.8, "reserve_gw": 27.3}
    weather = ["-8.0° / 5.0°", "-3.0° / 6.0°", "-5.0° / 4.0°", "-2.0° / 5.5°", "-1.0° / 7.0°"]
    return pwr, weather

pwr_data, weekly_temps = fetch_api_data()

# --- [사이드바] 휴일 및 날짜 관리 (좌상단 << 표식 추가) ---
if 'custom_holidays' not in st.session_state:
    st.session_state.custom_holidays = ["2026.02.16", "2026.02.17", "2026.02.18"]

with st.sidebar:
    st.markdown("### << 시스템 설정") # 흰색 << 표식 디자인 적용
    st.markdown("#### 📅 휴일 및 선거일 관리")
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
st.markdown(f"<h2>국민DR <span style='color:white; font-weight:200;'>실시간 전력 관제 센터</span></h2>", unsafe_allow_html=True)
st.markdown(f"<p style='color:#8a94a6; font-size:0.8rem;'>동기화 시간: {now.strftime('%H:%M:%S')} (KST) | API 상태: <span style='color:#00ff7f;'>연결됨</span></p>", unsafe_allow_html=True)

# 수급 상태 로직
reserve_gw = pwr_data['reserve_gw']
if reserve_gw > 10.5: status, s_color = "정상", "#00ff7f"
elif 9.5 < reserve_gw <= 10.5: status, s_color = "준비", "#ffff00"
elif 8.5 < reserve_gw <= 9.5: status, s_color = "관심", "#ff9900"
else: status, s_color = "주의", "#ff3131"

m1, m2, m3, m4 = st.columns(4)
with m1: st.markdown(f"<div class='metric-card'><div class='metric-label'>현재 전력부하</div><div class='metric-value'>{pwr_data['load']} GW</div></div>", unsafe_allow_html=True)
with m2: st.markdown(f"<div class='metric-card'><div class='metric-label'>운영 예비율</div><div class='metric-value'>{pwr_data['reserve']} %</div></div>", unsafe_allow_html=True)
with m3: st.markdown(f"<div class='metric-card'><div class='metric-label'>오늘의 기온</div><div class='metric-value' style='color:white !important;'>{weekly_temps[0]}</div></div>", unsafe_allow_html=True)
with m4: st.markdown(f"<div class='metric-card'><div class='metric-label'>수급 상태</div><div class='metric-value' style='color:{s_color} !important;'>{status}</div></div>", unsafe_allow_html=True)

# --- [UI] 주간 리포트 ---
st.markdown("#### 주간 DR 발령 예측 리포트 (월-금)")
this_monday = now - timedelta(days=now.weekday())
week_days = ["월요일", "화요일", "수요일", "목요일", "금요일"]
table_rows = ["날짜", "미세먼지", "기온(최저/최고)", "발령 확률", "상세 정보"]

table_html = "<table class='fixed-table'><thead><tr><th>항목</th>"
for wd in week_days: table_html += f"<th>{wd}</th>"
table_html += "</tr></thead><tbody>"

for row in table_rows:
    table_html += f"<tr><td><b>{row}</b></td>"
    for i in range(5):
        day_obj = this_monday + timedelta(days=i)
        d_str = day_obj.strftime("%Y.%m.%d")
        is_hday = d_str in st.session_state.custom_holidays
        if row == "날짜": val = d_str
        elif row == "미세먼지": val = "나쁨" if i == 2 else "보통"
        elif row == "기온(최저/최고)": val = weekly_temps[i]
        elif row == "발령 확률": val = "0%" if is_hday else ("100%" if i == 0 else "20%")
        elif row == "상세 정보":
            if i == 0: val = "<span class='highlight-dr'>DR발령됨(10:00)</span>"
            elif is_hday: val = "휴일(발령없음)"
            else: val = "평시 수급 안정"
        table_html += f"<td>{val}</td>"
    table_html += "</tr>"
table_html += "</tbody></table>"
st.markdown(table_html, unsafe_allow_html=True)

# --- [UI] 그래프 (범례 가독성 강화) ---
st.markdown("#### 실시간 공급 및 부하 추이 분석")

times = [f"{i:02d}:00" for i in range(24)]
load_forecast = [65, 62, 60, 63, 68, 80, 88, 94, 98, 101, 102, 98, 92, 90, 92, 95, 100, 102, 100, 92, 85, 80, 75, 70]
supply_val = pwr_data['supply']
now_hour = now.hour
actual_load = [l + np.random.uniform(-1.0, 1.0) if i <= now_hour else None for i, l in enumerate(load_forecast)]
reserve_gw_list = [supply_val - (a if a is not None else f) for a, f in zip(actual_load, load_forecast)]

fig = make_subplots(specs=[[{"secondary_y": True}]])
fig.add_trace(go.Scatter(x=times, y=load_forecast, name="예보 부하", fill='tozeroy', 
                         line=dict(color='rgba(0, 242, 255, 0.4)', width=2), fillcolor='rgba(0, 242, 255, 0.1)'))
fig.add_trace(go.Scatter(x=times, y=[supply_val]*24, name="공급 능력", 
                         line=dict(color='#ff3131', dash='dash', width=2)))
fig.add_trace(go.Scatter(x=times[:now_hour+1], y=actual_load[:now_hour+1], name="실제 부하", 
                         line=dict(color='#FFFFFF', width=4), mode='lines+markers'))
fig.add_trace(go.Bar(x=times, y=reserve_gw_list, name="운영 예비력(GW)", 
                     marker_color='rgba(0, 255, 127, 0.2)'), secondary_y=True)

fig.update_layout(
    template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
    height=450, margin=dict(l=0, r=0, t=30, b=0),
    # 범례 폰트 색상을 흰색으로 고정
    legend=dict(orientation="h", yanchor="bottom", y=1.05, xanchor="right", x=1, font=dict(color="white")),
    yaxis=dict(title="전력량 (GW)", range=[50, 115], showgrid=True, gridcolor='#1e2633'),
    yaxis2=dict(title="예비력 (GW)", range=[0, 65], overlaying='y', side='right', showgrid=False),
    xaxis=dict(showgrid=False), hovermode="x unified"
)

st.plotly_chart(fig, use_container_width=True)

