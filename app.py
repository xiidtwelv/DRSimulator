import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta

# 1. 페이지 설정 및 전문가용 다크 테마 디자인
st.set_page_config(page_title="국민DR Simulator", layout="wide")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@500;700&display=swap');
    
    [data-testid="stAppViewContainer"] { background-color: #05070a; }
    header { visibility: hidden; }
    h1, h2, h3, h4, p, span, label { color: #ffffff !important; font-family: 'Pretendard', sans-serif; }

    /* 반응형 메트릭 카드: 모바일 대응 */
    .metric-container {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
        gap: 12px;
        margin-bottom: 25px;
    }
    .metric-card {
        background: #10141c;
        border: 1px solid #1e2633;
        padding: 15px;
        border-radius: 4px;
        text-align: center;
    }
    .metric-label { color: #8a94a6; font-size: 0.7rem; font-weight: 700; text-transform: uppercase; }
    .metric-value { color: #00f2ff; font-family: 'JetBrains Mono', monospace; font-size: 1.6rem; font-weight: 700; }
    
    /* 주간 리포트 표: 모든 칸 너비 균등 고정 */
    .table-wrapper { overflow-x: auto; margin-top: 15px; }
    .fixed-table { 
        width: 100%; 
        table-layout: fixed; 
        border-collapse: collapse; 
        font-size: 0.8rem; 
        color: #c9d1d9;
    }
    .fixed-table th, .fixed-table td { 
        width: 16.66% !important; 
        padding: 10px 5px; 
        border: 1px solid #30363d; 
        text-align: center; 
        word-break: keep-all;
    }
    .fixed-table th { background: #161b22; color: #58a6ff; }
    .highlight-dr { color: #ff3131; font-weight: 800; }
    .holiday-text { color: #8a94a6; font-style: italic; }

    /* 모바일 폰트 크기 조정 */
    @media (max-width: 768px) {
        .metric-value { font-size: 1.2rem; }
        .fixed-table { font-size: 0.65rem; }
    }
    </style>
    """, unsafe_allow_html=True)

# [설정] 사용자 인증키
SERVICE_KEY = "a1129557f628d0e92794f5e8a914013df1817e58db885156d58037d70a27be40"

# --- [기능] 휴일 편집 시스템 (사이드바) ---
if 'custom_holidays' not in st.session_state:
    st.session_state.custom_holidays = ["2026.02.16", "2026.02.17", "2026.02.18"]

with st.sidebar:
    st.header("⚙️ SYSTEM CONFIG")
    st.subheader("📅 휴일/선거일 관리")
    new_hday = st.date_input("추가할 휴일 선택", value=None)
    if st.button("휴일 등록") and new_hday:
        h_str = new_hday.strftime("%Y.%m.%d")
        if h_str not in st.session_state.custom_holidays:
            st.session_state.custom_holidays.append(h_str)
            st.rerun()
    
    st.write("---")
    st.caption("현재 등록된 휴일 (클릭 시 삭제)")
    for h in sorted(st.session_state.custom_holidays):
        if st.button(f"🗑️ {h}", key=h):
            st.session_state.custom_holidays.remove(h)
            st.rerun()

def get_holiday_status(day_obj):
    if day_obj.weekday() >= 5: return True, "주말 (발령없음)"
    d_str = day_obj.strftime("%Y.%m.%d")
    if d_str in st.session_state.custom_holidays: return True, "휴일/연휴 (발령없음)"
    return False, ""

# --- [데이터] 데이터 엔진 ---
now = datetime.now()
# 이번 주 월요일 자동 계산
this_monday = now - timedelta(days=now.weekday())

# 현재 데이터 시뮬레이션 (API 연동 대기)
data = {
    "load": 78.5,
    "supply": 102.7,
    "reserve": 30.8,
    "temp_min": -8.0,
    "is_dr_active": True if now.strftime("%Y.%m.%d") == "2026.02.09" and now.hour >= 10 else False
}

# --- [화면] 상단 헤더 및 메트릭 ---
st.markdown("<h2 style='color:#00f2ff; margin-bottom:0;'>국민DR  <span style='color:white; font-weight:200;'>Simulator</span></h2>", unsafe_allow_html=True)
st.markdown(f"<p style='color:#8a94a6; font-size:11px; margin-bottom:20px;'>SYNC: {now.strftime('%H:%M:%S')} | STATUS: <span style='color:#00ff7f;'>● ONLINE</span></p>", unsafe_allow_html=True)

st.markdown(f"""
    <div class="metric-container">
        <div class="metric-card"><div class="metric-label">LOAD</div><div class="metric-value">{data['load']}G</div></div>
        <div class="metric-card"><div class="metric-label">RESERVE</div><div class="metric-value">{data['reserve']}%</div></div>
        <div class="metric-card"><div class="metric-label">TEMP</div><div class="metric-value" style="color:white;">{data['temp_min']}℃</div></div>
        <div class="metric-card"><div class="metric-label">DR STATUS</div><div class="metric-value" style="color:#ff3131; font-size:1rem; padding-top:8px;">{'ACTIVE' if data['is_dr_active'] else 'NORMAL'}</div></div>
    </div>
    """, unsafe_allow_html=True)

# --- [화면] 주간 리포트 (균등 너비 표) ---
st.markdown("<h4 style='border-left:4px solid #00f2ff; padding-left:10px; font-size:14px; margin-bottom:15px;'>WEEKLY DR FORECAST REPORT</h4>", unsafe_allow_html=True)

week_days = ["MON", "TUE", "WED", "THU", "FRI"]
report_labels = ["DATE", "AIR", "TEMP", "PROB", "DETAILS"]

table_html = "<div class='table-wrapper'><table class='fixed-table'><thead><tr><th>ITEM</th>"
for wd in week_days: table_html += f"<th>{wd}</th>"
table_html += "</tr></thead><tbody>"

for label in report_labels:
    table_html += f"<tr><td>{label}</td>"
    for i in range(5):
        target_day = this_monday + timedelta(days=i)
        is_off, msg = get_holiday_status(target_day)
        d_str = target_day.strftime("%Y.%m.%d")
        
        # 행별 데이터 로직
        if label == "DATE": val = d_str
        elif label == "AIR": val = "나쁨" if i == 2 else "보통"
        elif label == "TEMP": val = "-8°/5°" if i == 0 else "예보중"
        elif label == "PROB": 
            if is_off: val = "0%"
            else: val = "100%" if d_str == "2026.02.09" else ("40%" if i == 2 else "20%")
        elif label == "DETAILS":
            if d_str == "2026.02.09": val = "<span class='highlight-dr'>DR발령됨(10:00)</span>"
            elif is_off: val = f"<span class='holiday-text'>{msg}</span>"
            elif i == 2: val = "기온하강/미세먼지"
            else: val = "평시 안정"
            
        table_html += f"<td>{val}</td>"
    table_html += "</tr>"
table_html += "</tbody></table></div>"

st.markdown(table_html, unsafe_allow_html=True)

# --- [화면] 그래프 (오류 수정 완료) ---
st.markdown("<h4 style='margin-top:40px; border-left:4px solid #00f2ff; padding-left:10px; font-size:14px; margin-bottom:15px;'>SUPPLY & LOAD TREND</h4>", unsafe_allow_html=True)

times = [f"{i:02d}:00" for i in range(24)]
load_forecast = [65, 62, 60, 63, 68, 80, 88, 94, 98, 101, 102, 98, 92, 90, 92, 95, 100, 102, 100, 92, 85, 80, 75, 70]
supply_val = data['supply']

# [Actual Load] 실시간 연장
now_hour = now.hour
actual_load = [l + np.random.uniform(0.5, 2.0) if i <= now_hour else None for i, l in enumerate(load_forecast)]

# [운영 예비력] 변수명: reserve_gw (그래프 호출부와 통일)
reserve_gw = [supply_val - l for l in load_forecast]

fig = make_subplots(specs=[[{"secondary_y": True}]])

# 1. 예보 부하 영역
fig.add_trace(go.Scatter(x=times, y=load_forecast, name="Forecast", fill='tozeroy', 
                         line=dict(color='rgba(0, 242, 255, 0.4)', width=2), fillcolor='rgba(0, 242, 255, 0.1)'), secondary_y=False)
# 2. 공급 한계
fig.add_trace(go.Scatter(x=times, y=[supply_val]*24, name="Supply", 
                         line=dict(color='#ff3131', dash='dash', width=2)), secondary_y=False)
# 3. 실제 부하 (흰색 실선)
fig.add_trace(go.Scatter(x=times[:now_hour+1], y=actual_load[:now_hour+1], name="Actual", 
                         line=dict(color='#FFFFFF', width=3.5)), secondary_y=False)
# 4. 운영 예비력 (바 차트) - 변수명 오류 수정됨
fig.add_trace(go.Bar(x=times, y=reserve_gw, name="운영 예비력", 
                     marker_color='rgba(0, 255, 127, 0.15)'), secondary_y=True)

fig.update_layout(
    template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
    height=400, margin=dict(l=0, r=0, t=20, b=0),
    legend=dict(orientation="h", yanchor="bottom", y=1.05, xanchor="right", x=1, font=dict(size=10)),
    yaxis=dict(title="Power (GW)", range=[50, 115], showgrid=True, gridcolor='#1e2633'),
    yaxis2=dict(title="Reserve (GW)", overlaying='y', side='right', range=[0, 60], showgrid=False),
    xaxis=dict(showgrid=False)
)
st.plotly_chart(fig, use_container_width=True)

st.warning("⚠️ **ANALYTICS:** 오전 10시 실제 부하가 예보치를 상회하여 DR이 발령되었습니다. 17시 피크 시간대 추가 위험이 존재합니다.")