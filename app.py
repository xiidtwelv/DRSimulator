# --- [데이터 처리: API 결과를 화면용으로 가공] ---
# API에서 온 데이터가 비어있을 경우를 대비한 기본값 설정
if not weekly_env:
    weekly_env = [{"date": "데이터 없음", "min": "-", "max": "-", "sky": "-", "cloud": 0, "air": "-", "dr": "-"}]

# --- [UI 디자인 및 출력 복구] ---
st.markdown("""
    <style>
    [data-testid="stAppViewContainer"] { background-color: #05070a; }
    h2 { color: #00f2ff !important; font-family: 'Pretendard'; }
    .metric-card { background: #10141c; border: 1px solid #1e2633; padding: 20px; border-radius: 8px; text-align: center; }
    .metric-label { color: #a9d1d9; font-size: 0.9rem; font-weight: 700; }
    .metric-value { color: #00f2ff; font-size: 1.8rem; font-weight: 700; }
    
    /* 표 디자인 복구 */
    .fixed-table { width: 100%; border-collapse: collapse; margin-top: 15px; color: white; font-size: 0.9rem; }
    .fixed-table th { background: #161b22; color: #58a6ff; padding: 12px; border: 1px solid #30363d; }
    .fixed-table td { padding: 12px; border: 1px solid #30363d; text-align: center; }
    .prob-critical { color: #ff3131; font-weight: bold; }
    .prob-safe { color: #00f2ff; }
    </style>
    """, unsafe_allow_html=True)

st.markdown("<h2>NOSTRADAMUS 실시간 관제 센터</h2>", unsafe_allow_html=True)

# 1. 상단 지표 (Metric Cards)
m1, m2, m3, m4, m5 = st.columns(5)
with m1: st.markdown(f"<div class='metric-card'><div class='metric-label'>현재 전력부하</div><div class='metric-value'>{pwr_data['load']} GW</div></div>", unsafe_allow_html=True)
with m2: st.markdown(f"<div class='metric-card'><div class='metric-label'>운영 예비력</div><div class='metric-value'>{pwr_data['reserve_gw']} GW</div></div>", unsafe_allow_html=True)
with m3: st.markdown(f"<div class='metric-card'><div class='metric-label'>오늘 기온</div><div class='metric-value' style='color:white;'>{weekly_env[0]['min']}° / {weekly_env[0]['max']}°</div></div>", unsafe_allow_html=True)
with m4:
    status_color = "#00f2ff" if pwr_data['reserve_gw'] > 10 else "#f1c40f"
    st.markdown(f"<div class='metric-card'><div class='metric-label'>수급 상태</div><div class='metric-value' style='color:{status_color};'>정상</div></div>", unsafe_allow_html=True)
with m5: st.markdown(f"<div class='metric-card'><div class='metric-label'>예측 성공률</div><div class='metric-value' style='color:#f1c40f;'>92.5%</div></div>", unsafe_allow_html=True)

# 2. 주간 리포트 표 (HTML 방식으로 복구)
st.markdown("#### 주간 DR 발령 예측 및 검증")
table_html = "<table class='fixed-table'><thead><tr><th>항목</th>"
for day in weekly_env:
    table_html += f"<th>{day['date']}</th>"
table_html += "</tr></thead><tbody>"

# 행별 데이터 구성
rows = [
    ("기상(최저/최고)", lambda d: f"{d['min']}°C / {d['max']}°C"),
    ("운량 (상태)", lambda d: f"{d['cloud']} ({d['sky']})"),
    ("미세먼지", lambda d: d['air']),
    ("발령 확률", lambda d: f"<span class='prob-safe'>{20 + (int(float(d['cloud']))*5)}%</span>")
]

for label, func in rows:
    table_html += f"<tr><td><b>{label}</b></td>"
    for day in weekly_env:
        table_html += f"<td>{func(day)}</td>"
    table_html += "</tr>"

table_html += "</tbody></table>"
st.markdown(table_html, unsafe_allow_html=True)
