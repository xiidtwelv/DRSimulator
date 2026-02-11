import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta, timezone
import plotly.graph_objects as go

# 1. 페이지 설정
st.set_page_config(page_title="국민DR 통합 관제 V2.7", layout="wide")

# --- [내부 함수: 데이터 가져오기] ---
def get_now_kst():
    return datetime.now(timezone(timedelta(hours=9)))

@st.cache_data(ttl=3600)
def fetch_realtime_data(nx, ny):
    service_key = st.secrets.get("SERVICE_KEY", "YOUR_KEY_HERE")
    now = get_now_kst()
    base_date = now.strftime("%Y%m%d")
    
    # 기상청 단기예보 API
    url = "http://apis.data.go.kr/1360000/VilageFcstInfoService_2.0/getVilageFcst"
    params = {
        'serviceKey': service_key,
        'pageNo': '1', 'numOfRows': '300', 'dataType': 'JSON',
        'base_date': base_date, 'base_time': '0500', 'nx': str(nx), 'ny': str(ny)
    }

    try:
        response = requests.get(url, params=params, timeout=10)
        items = response.json()['response']['body']['items']['item']
        
        weather_dict = {}
        for item in items:
            date_key = item['fcstDate'][-4:]
            if date_key not in weather_dict:
                weather_dict[date_key] = {"date": date_key, "min": "0", "max": "0", "sky": "-", "cloud": 0, "air": "보통", "dr": "-"}
            
            if item['category'] == 'TMN': weather_dict[date_key]['min'] = item['fcstValue']
            if item['category'] == 'TMX': weather_dict[date_key]['max'] = item['fcstValue']
            if item['category'] == 'SKY':
                val = int(item['fcstValue'])
                weather_dict[date_key]['cloud'] = val
                weather_dict[date_key]['sky'] = "맑음" if val <= 5 else "흐림"
        
        return {"load": 78.5, "reserve_gw": 10.2}, list(weather_dict.values())[:5]
    except:
        # API 실패 시 보여줄 샘플 데이터 (에러 방지용)
        sample_weather = [{"date": (now + timedelta(days=i)).strftime("%m%d"), "min": "-2", "max": "5", "sky": "맑음", "cloud": 2, "air": "보통", "dr": "-"} for i in range(5)]
        return {"load": 78.5, "reserve_gw": 10.2}, sample_weather

# --- [데이터 로드] ---
# 여기서 weekly_env를 확실하게 정의합니다.
pwr_data, weekly_env = fetch_realtime_data(60, 127)

# --- [디자인: CSS] ---
st.markdown("""
    <style>
    [data-testid="stAppViewContainer"] { background-color: #05070a; }
    h2 { color: #00f2ff !important; font-family: 'Pretendard'; }
    .metric-card { background: #10141c; border: 1px solid #1e2633; padding: 20px; border-radius: 8px; text-align: center; margin-bottom: 10px; }
    .metric-label { color: #a9d1d9; font-size: 0.9rem; font-weight: 700; }
    .metric-value { color: #00f2ff; font-size: 1.8rem; font-weight: 700; }
    .fixed-table { width: 100%; border-collapse: collapse; margin-top: 20px; color: white; }
    .fixed-table th { background: #161b22; color: #58a6ff; padding: 12px; border: 1px solid #30363d; }
    .fixed-table td { padding: 12px; border: 1px solid #30363d; text-align: center; }
    .prob-critical { color: #ff3131; font-weight: bold; }
    .prob-safe { color: #00f2ff; }
    </style>
    """, unsafe_allow_html=True)

# --- [UI 출력] ---
st.markdown("<h2>NOSTRADAMUS 실시간 관제</h2>", unsafe_allow_html=True)

# 1. 상단 지표
m1, m2, m3, m4, m5 = st.columns(5)
with m1: st.markdown(f"<div class='metric-card'><div class='metric-label'>현재 전력부하</div><div class='metric-value'>{pwr_data['load']} GW</div></div>", unsafe_allow_html=True)
with m2: st.markdown(f"<div class='metric-card'><div class='metric-label'>운영 예비력</div><div class='metric-value'>{pwr_data['reserve_gw']} GW</div></div>", unsafe_allow_html=True)
with m3: st.markdown(f"<div class='metric-card'><div class='metric-label'>오늘 기온</div><div class='metric-value' style='color:white;'>{weekly_env[0]['min']}° / {weekly_env[0]['max']}°</div></div>", unsafe_allow_html=True)
with m4: st.markdown(f"<div class='metric-card'><div class='metric-label'>수급 상태</div><div class='metric-value'>정상</div></div>", unsafe_allow_html=True)
with m5: st.markdown(f"<div class='metric-card'><div class='metric-label'>성공률</div><div class='metric-value'>92.5%</div></div>", unsafe_allow_html=True)

# 2. 주간 예측 표 (이미지 디자인 복구)
st.markdown("#### 주간 DR 발령 예측 및 검증")
if weekly_env:
    table_html = "<table class='fixed-table'><thead><tr><th>항목</th>"
    for d in weekly_env: table_html += f"<th>{d['date']}</th>"
    table_html += "</tr></thead><tbody>"
    
    # 각 행 생성
    row_configs = [
        ("기상(최저/최고)", lambda x: f"{x['min']}°C / {x['max']}°C"),
        ("운량 (상태)", lambda x: f"{x['cloud']} ({x['sky']})"),
        ("미세먼지", lambda x: x['air']),
        ("발령 확률", lambda x: f"<span class='prob-safe'>{20 + (int(float(x['cloud']))*5)}%</span>")
    ]
    
    for label, formatter in row_configs:
        table_html += f"<tr><td><b>{label}</b></td>"
        for d in weekly_env:
            table_html += f"<td>{formatter(d)}</td>"
        table_html += "</tr>"
    
    table_html += "</tbody></table>"
    st.markdown(table_html, unsafe_allow_html=True)
else:
    st.warning("데이터를 불러오는 중입니다...")

# 3. 그래프 (시인성 강화)
st.markdown("#### 실시간 순부하 변동 추이")
fig = go.Figure()
fig.add_trace(go.Scatter(x=list(range(24)), y=[65, 62, 60, 63, 68, 80, 88, 94, 98, 101, 105, 102, 98, 95, 96, 98, 102, 104, 102, 92, 85, 80, 75, 70], 
                         name="순부하(Net Load)", line=dict(color='#00f2ff', width=4)))
fig.update_layout(template='plotly_dark', paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', height=400)
st.plotly_chart(fig, use_container_width=True)
