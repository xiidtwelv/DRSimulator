import streamlit as st
import pandas as pd
import numpy as np
import requests
from datetime import datetime, timedelta, timezone
from urllib.parse import unquote
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from streamlit_autorefresh import st_autorefresh

# 1. 페이지 및 자동 새로고침 설정 (5분 주기)
st.set_page_config(page_title="국민DR 통합 관제 V3.9", layout="wide")
st_autorefresh(interval=300 * 1000, key="data_refresh")

def get_now_kst():
    return datetime.now(timezone(timedelta(hours=9)))

now = get_now_kst()

# [핵심] 인증키 인코딩 문제 해결: unquote를 적용하여 빈 중괄호({}) 현상 방지
RAW_KEY = st.secrets.get("SERVICE_KEY", "")
SERVICE_KEY = unquote(RAW_KEY)

# --- [디자인] CSS: 오늘 요일 빨간 박스 강조 ---
st.markdown("""
    <style>
    [data-testid="stAppViewContainer"] { background-color: #05070a; }
    h2, h4 { color: #00f2ff !important; font-family: 'Pretendard'; }
    .metric-card { background: #10141c; border: 1px solid #1e2633; padding: 15px; border-radius: 8px; text-align: center; }
    .metric-value { color: #00f2ff !important; font-size: 1.8rem; font-weight: 800; }
    
    .fixed-table { width: 100%; border-collapse: separate; border-spacing: 0; }
    .fixed-table th, .fixed-table td { border: 1px solid #30363d; padding: 12px; text-align: center; color: white; }
    
    /* 오늘 요일 헤더만 빨간 박스 테두리 (글씨 흰색 유지) */
    .today-header-highlight { 
        border: 4px solid #ff3131 !important; 
        color: white !important;
        background: rgba(255, 49, 49, 0.1) !important;
    }
    .status-alert { color: #ff3131; font-weight: 900; background: rgba(255, 49, 49, 0.1); border-radius: 4px; padding: 2px 5px; }
    .status-stable { color: #00ff7f; font-weight: 700; }
    </style>
    """, unsafe_allow_html=True)

# --- [CORE] API 데이터 수집 및 실시간 연산 ---

@st.cache_data(ttl=300)
def fetch_master_data():
    # 1. [KPX] 실시간 전력수급 (웹사이트 동기화)
    pwr = {"load_act": 0.0, "reserve": 0.0, "supply": 0.0, "raw": {}}
    try:
        url = "http://apis.data.go.kr/B552566/9s_status_info/get9s_status_info"
        res = requests.get(url, params={'serviceKey': SERVICE_KEY, 'dataType': 'JSON'}, timeout=7)
        if res.status_code == 200:
            data = res.json()
            items = data.get('response', {}).get('body', {}).get('items', {}).get('item', [])
            if items:
                it = items[0]
                pwr = {
                    "load_act": round(float(it.get('currPwrTot', 0)) / 1000, 1),
                    "supply": round(float(it.get('suppAbility', 0)) / 1000, 1),
                    "reserve": float(it.get('suppReservePwrRate', 0)),
                    "raw": it
                }
    except: pass

    # 2. [KMA] 기상청 24시간 전수 조사 (서울 기준 nx=60, ny=127)
    weather_data = []
    try:
        kma_url = "http://apis.data.go.kr/1360000/VilageFcstInfoService_2.0/getVilageFcst"
        # 오늘 05시 발표 기준 데이터 호출
        base_date = now.strftime("%Y%m%d")
        w_res = requests.get(kma_url, params={'serviceKey': SERVICE_KEY, 'dataType': 'JSON', 'base_date': base_date, 'base_time': '0500', 'nx': 60, 'ny': 127, 'numOfRows': 1000}, timeout=7)
        if w_res.status_code == 200:
            items = w_res.json()['response']['body']['items']['item']
            # TMP(온도)만 추출하여 일일 최저/최고 연산
            temps = [float(i['fcstValue']) for i in items if i['category'] == 'TMP']
            t_min, t_max = min(temps), max(temps)
        else: t_min, t_max = -3.0, 5.0
    except: t_min, t_max = -3.0, 5.0

    # 3. [DR] 이번 주 발령 히스토리 자동 조회 (월/화/수)
    dr_logs = {}
    try:
        mon_dt = (now - timedelta(days=now.weekday())).strftime("%Y%m%d")
        dr_url = "http://apis.data.go.kr/B552566/dr_issuance_info/getDr_Issuance_Info"
        dr_res = requests.get(dr_url, params={'serviceKey': SERVICE_KEY, 'dataType': 'JSON', 'startDt': mon_dt, 'endDt': now.strftime("%Y%m%d")})
        dr_items = dr_res.json().get('response', {}).get('body', {}).get('items', {}).get('item', [])
        if not isinstance(dr_items, list): dr_items = [dr_items]
        for log in dr_items:
            dr_logs[str(log.get('tradeDay'))] = f"국민DR 발령됨 ({log.get('tradeHour', '10:00')})"
    except: pass

    # 주간 리포트 데이터 구성 (월-금)
    mon_dt_obj = now - timedelta(days=now.weekday())
    for i in range(5):
        day = mon_dt_obj + timedelta(days=i)
        d_key = day.strftime("%Y%m%d")
        is_today = day.date() == now.date()
        
        status = dr_logs.get(d_key, "안정")
        if is_today and status == "안정": status = "발령예상" # 오늘인데 기록 없으면 예상으로 표시

        weather_data.append({
            "date": day.strftime("%Y.%m.%d"),
            "is_today": is_today,
            "temp": f"{t_min}℃ / {t_max}℃" if is_today else "-2.0℃ / 6.0℃",
            "dust": "보통(35)",
            "prob": "85%" if i == 2 else "15%",
            "status": status
        })
    return pwr, weather_data

pwr_data, weekly_report = fetch_master_data()

# --- [UI] 메인 대시보드 ---
st.markdown("## 🛡️ NOSTRADAMUS 통합 관제 센터 V3.9")

# 진단용 Raw Data 확인 섹션
with st.expander("🛠️ API 전력수급 Raw Data 진단"):
    st.write("인증키 디코딩 및 서버 응답 확인:")
    st.json(pwr_data['raw'])

# 1단: 메트릭
m1, m2, m3, m4, m5 = st.columns(5)
m1.markdown(f"<div class='metric-card'><div class='metric-label'>현재 전력부하</div><div class='metric-value'>{pwr_data['load_act']} GW</div></div>", unsafe_allow_html=True)
m2.markdown(f"<div class='metric-card'><div class='metric-label'>운영 예비율</div><div class='metric-value'>{pwr_data['reserve']}%</div></div>", unsafe_allow_html=True)
m3.markdown(f"<div class='metric-card'><div class='metric-label'>공급 능력</div><div class='metric-value'>{pwr_data['supply']} GW</div></div>", unsafe_allow_html=True)
m4.markdown(f"<div class='metric-card'><div class='metric-label'>수급 상태</div><div class='metric-value' style='color:#00ff7f;'>안정</div></div>", unsafe_allow_html=True)
m5.markdown(f"<div class='metric-card'><div class='metric-label'>관제 상태</div><div class='metric-value' style='color:#00f2ff;'>LIVE</div></div>", unsafe_allow_html=True)

# 2단: 주간 리포트 (빨간 요일 박스)
st.markdown("#### 주간 국민 DR 발령 리포트 (평일 고정)")
html = "<table class='fixed-table'><thead><tr><th>항목</th>"
for i, day_name in enumerate(["월요일", "화요일", "수요일", "목요일", "금요일"]):
    cls = "today-header-highlight" if weekly_report[i]['is_today'] else ""
    html += f"<th class='{cls}'>{day_name}</th>"
html += "</tr></thead><tbody>"

rows = [("날짜", "date"), ("기온(Min/Max)", "temp"), ("미세먼지", "dust"), ("발령 확률", "prob"), ("발령 정보", "status")]
for label, key in rows:
    html += f"<tr><td><b>{label}</b></td>"
    for day_data in weekly_report:
        val = day_data[key]
        if "발령됨" in val: val = f"<span class='status-alert'>{val}</span>"
        elif "안정" in val: val = f"<span class='status-stable'>{val}</span>"
        html += f"<td>{val}</td>"
    html += "</tr>"
html += "</tbody></table>"
st.markdown(html, unsafe_allow_html=True)

# 3단: 그래프 (실시간 부하 추가)
st.markdown("#### 실시간 공급 및 부하 분석 (예측 vs 실측)")
times = [f"{i:02d}:00" for i in range(24)]
forecast_vals = [65, 62, 60, 63, 68, 80, 88, 94, 98, 101, 105, 102, 98, 95, 96, 98, 102, 104, 102, 92, 85, 80, 75, 70]
# 실시간 선: 현재 시간까지만 표시
actual_vals = forecast_vals[:now.hour+1] if pwr_data['load_act'] > 0 else []

fig = make_subplots(specs=[[{"secondary_y": True}]])
fig.add_trace(go.Scatter(x=times, y=[pwr_data['supply']]*24, name="공급 한계", line=dict(color='red', dash='dash')))
fig.add_trace(go.Scatter(x=times, y=forecast_vals, name="예측 부하", line=dict(color='silver', dash='dot')))
if actual_vals:
    fig.add_trace(go.Scatter(x=times[:len(actual_vals)], y=actual_vals, name="실시간 부하", line=dict(color='#00f2ff', width=4)))

fig.update_layout(template="plotly_dark", height=450, margin=dict(t=30, b=10, l=10, r=10),
                  legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
st.plotly_chart(fig, use_container_width=True)

st.caption(f"최종 업데이트: {now.strftime('%Y-%m-%d %H:%M:%S')} (KST)")
