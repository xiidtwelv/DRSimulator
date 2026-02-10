import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta, timezone
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# 1. 페이지 설정
st.set_page_config(page_title="국민DR 통합 관제 V2.5", layout="wide", initial_sidebar_state="collapsed")

def get_now_kst():
    return datetime.now(timezone(timedelta(hours=9)))

now = get_now_kst()

# --- [디자인] CSS (확률 색상 및 범례 시인성 개선) ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Pretendard:wght@400;700&display=swap');
    [data-testid="stAppViewContainer"] { background-color: #05070a; }
    header { visibility: hidden; }
    h2, h4, p, span, label { font-family: 'Pretendard', sans-serif; color: #ffffff !important; }
    h2 { color: #00f2ff !important; font-size: 2rem !important; margin-bottom: 5px !important; }
    h4 { color: #00f2ff !important; border-left: 4px solid #00f2ff; padding-left: 10px; margin-top: 30px; margin-bottom: 15px; }
    
    .metric-card { background: #10141c; border: 1px solid #1e2633; padding: 15px; border-radius: 8px; text-align: center; }
    .metric-label { color: #c9d1d9 !important; font-size: 0.85rem !important; font-weight: 700; }
    .metric-value { color: #00f2ff !important; font-size: 1.5rem !important; font-weight: 700; }
    
    .fixed-table { width: 100%; border-collapse: collapse; table-layout: fixed; margin-top: 10px; }
    .fixed-table th { background: #161b22; color: #58a6ff !important; padding: 10px; border: 1px solid #30363d; font-size: 0.85rem; }
    .fixed-table td { padding: 10px; border: 1px solid #30363d; text-align: center; font-size: 0.85rem; height: 60px; color: #e6edf3 !important; }
    
    /* 발령 확률 단계별 색상 클래스 */
    .prob-safe { color: #00f2ff !important; font-weight: 700; }     /* 0-30% */
    .prob-warn { color: #f1c40f !important; font-weight: 700; }     /* 31-60% */
    .prob-danger { color: #e67e22 !important; font-weight: 700; }   /* 61-80% */
    .prob-critical { color: #ff3131 !important; font-weight: 800; } /* 81-100% */
    
    .strike { text-decoration: line-through; color: #b0b8c4 !important; font-size: 0.8rem; }
    .miss-note { background: rgba(255, 49, 49, 0.1); border: 1px solid #ff3131; padding: 15px; border-radius: 8px; margin-top: 10px; }
    .logic-tag { background: #1e2633; padding: 2px 6px; border-radius: 4px; font-size: 0.75rem; color: #00f2ff !important; margin: 2px; display: inline-block; }
    </style>
    """, unsafe_allow_html=True)

# --- [데이터] 날씨 데이터 (최저/최고 기온 추가) ---
pwr_data = {"load": 78.5, "reserve": 12.4, "success_rate": 92.5}
weather_data = [
    {"min": -8.0, "max": 2.1, "prob": 100},
    {"min": -3.0, "max": 5.4, "prob": 100}, # 오늘 발령 반영
    {"min": -6.0, "max": -1.2, "prob": 75},
    {"min": -2.0, "max": 6.0, "prob": 20},
    {"min": -1.0, "max": 4.5, "prob": 35}
]

def get_prob_class(prob):
    if prob <= 30: return "prob-safe"
    elif prob <= 60: return "prob-warn"
    elif prob <= 80: return "prob-danger"
    else: return "prob-critical"

# --- [UI] 헤더 및 지표 ---
st.markdown(f"<h2>NOSTRADAMUS <span style='color:white; font-weight:200;'>실시간 전력 관제 센터</span></h2>", unsafe_allow_html=True)
c1, c2, c3, c4, c5 = st.columns(5)
with c1: st.markdown(f"<div class='metric-card'><div class='metric-label'>현재 전력부하</div><div class='metric-value'>{pwr_data['load']} GW</div></div>", unsafe_allow_html=True)
with c2: st.markdown(f"<div class='metric-card'><div class='metric-label'>운영 예비율</div><div class='metric-value'>{pwr_data['reserve']}%</div></div>", unsafe_allow_html=True)
with c3: # 기온 정보 확장
    st.markdown(f"<div class='metric-card'><div class='metric-label'>오늘의 기온(최저/최고)</div><div class='metric-value'>{weather_data[1]['min']}℃ / {weather_data[1]['max']}℃</div></div>", unsafe_allow_html=True)
with c4: st.markdown(f"<div class='metric-card'><div class='metric-label'>수급 상태</div><div class='metric-value' style='color:#00ff7f !important;'>정상</div></div>", unsafe_allow_html=True)
with c5: st.markdown(f"<div class='metric-card'><div class='metric-label'>최근 30일 예측 성공률</div><div class='metric-value' style='color:#f1c40f !important;'>{pwr_data['success_rate']}%</div></div>", unsafe_allow_html=True)

# --- [UI] 주간 리포트 ---
st.markdown("#### 주간 DR 발령 예측 및 검증 (Explainable Logic)")
week_days = ["월요일(02.09)", "화요일(오늘)", "수요일(02.11)", "목요일(02.12)", "금요일(02.13)"]

table_html = "<table class='fixed-table'><thead><tr><th>항목</th>"
for wd in week_days: table_html += f"<th>{wd}</th>"
table_html += "</tr></thead><tbody>"

# 행 데이터 구성 (발령 확률 색상 입히기)
rows = [
    ("기온(최저/최고)", [f"{d['min']}℃ / {d['max']}℃" for d in weather_data]),
    ("발령 확률", [
        f"<span class='{get_prob_class(100)}'>100%</span>",
        f"<span class='strike'>20%</span> → <span class='{get_prob_class(100)}'><b>100%</b></span>",
        f"<span class='{get_prob_class(75)}'>75%</span>",
        f"<span class='{get_prob_class(20)}'>20%</span>",
        f"<span class='{get_prob_class(35)}'>35%</span>"
    ]),
    ("산출 근거", [
        "<span class='logic-tag'>한파</span>", 
        "<span class='logic-tag'>평시</span><br>+<span class='logic-tag' style='background:#ff3131'>일사량 급감</span>", 
        "<span class='logic-tag'>한파</span><span class='logic-tag'>폭설</span>",
        "<span class='logic-tag'>평시</span>",
        "<span class='logic-tag'>미세먼지</span>"
    ]),
    ("상태 정보", ["DR발령완료", "<span class='prob-critical'>발령(10:00~11:00)</span>", "주의단계", "수급안정", "모니터링"])
]

for label, values in rows:
    table_html += f"<tr><td><b>{label}</b></td>"
    for v in values: table_html += f"<td>{v}</td>"
    table_html += "</tr>"
table_html += "</tbody></table>"
st.markdown(table_html, unsafe_allow_html=True)

# --- [UI] 오답노트 ---
st.markdown("""
    <div class='miss-note'>
        <b style='color:#ff3131;'>⚠️ [오답노트] 2월 10일(화) 발령 원인 분석</b><br>
        <span>- <b>예측 실패 원인:</b> 전국적인 구름 유입으로 인한 <b>태양광 발전량(BTM) 급감</b> 미반영.</span><br>
        <span>- <b>향후 보완:</b> 미세먼지 외 '운량(Cloud Cover)' 가중치를 기존 10%에서 40%로 상향 조정 예정.</span>
    </div>
    """, unsafe_allow_html=True)

# --- [UI] 그래프 (범례 시인성 개선) ---
st.markdown("#### 실시간 순부하(Net Load) 및 태양광 변동 추이")
times = [f"{i:02d}:00" for i in range(24)]
total_load = [65, 62, 60, 63, 68, 80, 88, 94, 98, 101, 105, 102, 98, 95, 96, 98, 102, 104, 102, 92, 85, 80, 75, 70]
solar_gen = [0, 0, 0, 0, 0, 0, 2, 8, 15, 18, 12, 10, 8, 7, 5, 2, 0, 0, 0, 0, 0, 0, 0, 0]
net_load = [t - s for t, s in zip(total_load, solar_gen)]

fig = make_subplots(specs=[[{"secondary_y": True}]])
fig.add_trace(go.Scatter(x=times, y=total_load, name="총 부하(예상)", line=dict(color='rgba(150,150,150,0.5)', dash='dot', width=1.5)))
fig.add_trace(go.Scatter(x=times, y=solar_gen, name="태양광 발전(추정)", fill='tozeroy', line=dict(color='rgba(255, 215, 0, 0.8)'), fillcolor='rgba(255, 215, 0, 0.1)'), secondary_y=True)
fig.add_trace(go.Scatter(x=times, y=net_load, name="순부하(Net Load)", line=dict(color='#00f2ff', width=3.5)))
fig.add_trace(go.Scatter(x=times, y=[105]*24, name="공급 능력 한계", line=dict(color='#ff3131', dash='dash', width=2)))

# 그래프 레이아웃 및 범례 설정 강화
fig.update_layout(
    template="plotly_dark", 
    paper_bgcolor='rgba(0,0,0,0)', 
    plot_bgcolor='rgba(0,0,0,0)', 
    height=450, 
    margin=dict(l=10, r=10, t=50, b=10),
    legend=dict(
        orientation="h", 
        yanchor="bottom", y=1.02, 
        xanchor="right", x=1,
        font=dict(size=13, color="#ffffff"),  # 범례 글자 크기 키움 & 흰색 고정
        bgcolor="rgba(0,0,0,0)"
    ),
    yaxis=dict(range=[50, 120], title="부하 (GW)", gridcolor='rgba(255,255,255,0.05)', tickfont=dict(color="#e6edf3")),
    yaxis2=dict(range=[0, 30], showgrid=False, title="태양광 (GW)", tickfont=dict(color="#f1c40f")),
    hovermode="x unified"
)
st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False}) # 툴바 숨김으로 깔끔하게 처리

st.info("💡 **Twin-Day 분석:** 오늘의 부하 패턴은 **2024.01.15(DR 발령일)**과 94% 유사합니다.")
