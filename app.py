import streamlit as st
import pandas as pd
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# 1. 페이지 설정
st.set_page_config(page_title="국민DR 통합 관제 V2.7", layout="wide")

# --- [내부 함수: 데이터 가져오기] ---
def get_now_kst():
    return datetime.now(timezone(timedelta(hours=9)))

@st.cache_data(ttl=3600)
def fetch_realtime_data():
    """
    공공데이터포털 API 연동 함수
    """
    service_key = st.secrets["SERVICE_KEY"]
    now = get_now_kst()
    base_date = now.strftime("%Y%m%d")
    
    # [A] 기상청 단기예보 (예시 좌표: 서울 60, 127)
    # 실제로는 더 정밀한 파싱이 필요하지만, 여기서는 구조적 예시를 구현합니다.
    weather_url = "http://apis.data.go.kr/1360000/VilageFcstInfoService_2.0/getVilageFcst"
    params = {
        'serviceKey': service_key,
        'pageNo': '1',
        'numOfRows': '100',
        'dataType': 'JSON',
        'base_date': base_date,
        'base_time': '0500', # 오전 5시 발표 기준
        'nx': '60',
        'ny': '127'
    }
    
    try:
        # 실제 운영시에는 아래 주석을 해제하여 API를 호출하세요.
        # response = requests.get(weather_url, params=params, timeout=10).json()
        # items = response['response']['body']['items']['item']
        
        # 테스트용 가상 데이터 (API 연결 실패 시 대비)
        weather_list = []
        for i in range(5):
            target_date = (now + timedelta(days=i)).strftime("%m.%d")
            weather_list.append({
                "date": target_date,
                "min": f"-{5+i}.0",
                "max": f"{2+i}.5",
                "sky": "맑음" if i % 2 == 0 else "흐림",
                "cloud": 2 if i % 2 == 0 else 8,
                "air": "보통" if i < 2 else "나쁨",
                "dr": "발령 대기" if i == 1 else "-"
            })
    except:
        weather_list = [] # 에러 시 빈 리스트

    # [B] 전력 수급 데이터 (가상 샘플)
    pwr_data = {"load": 78.5, "supply": 105.0, "reserve_gw": 10.2}
    
    return pwr_data, weather_list

# 데이터 로드
try:
    pwr_data, weekly_env = fetch_realtime_data()
except Exception as e:
    st.error("API 키가 설정되지 않았거나 연결에 문제가 있습니다.")
    st.stop()

# --- [UI 디자인: CSS] ---
st.markdown("""
    <style>
    [data-testid="stAppViewContainer"] { background-color: #05070a; }
    h2 { color: #00f2ff !important; font-family: 'Pretendard'; }
    .metric-card { background: #10141c; border: 1px solid #1e2633; padding: 20px; border-radius: 8px; text-align: center; }
    .metric-label { color: #a9d1d9; font-size: 0.9rem; font-weight: 700; }
    .metric-value { color: #00f2ff; font-size: 1.8rem; font-weight: 700; }
    .fixed-table { width: 100%; border-collapse: collapse; margin-top: 15px; color: white; }
    .fixed-table th, .fixed-table td { border: 1px solid #30363d; padding: 12px; text-align: center; }
    .prob-critical { color: #ff3131; font-weight: bold; }
    .prob-safe { color: #00f2ff; }
    </style>
    """, unsafe_allow_html=True)

# --- [UI 출력] ---
st.markdown("<h2>NOSTRADAMUS 실시간 전력 관제</h2>", unsafe_allow_html=True)

# 상단 지표
cols = st.columns(5)
metrics = [
    ("현재 전력부하", f"{pwr_data['load']} GW"),
    ("운영 예비력", f"{pwr_data['reserve_gw']} GW"),
    ("오늘 기온", f"{weekly_env[0]['min']}°C / {weekly_env[0]['max']}°C"),
    ("수급 상태", "정상" if pwr_data['reserve_gw'] > 10 else "주의"),
    ("예측 성공률", "92.5%")
]

for col, (label, val) in zip(cols, metrics):
    col.markdown(f"""<div class='metric-card'><div class='metric-label'>{label}</div><div class='metric-value'>{val}</div></div>""", unsafe_allow_html=True)

# 주간 리포트 테이블
st.markdown("#### 주간 DR 발령 예측 및 검증")
table_html = "<table class='fixed-table'><tr><th>항목</th>"
for d in weekly_env: table_html += f"<th>{d['date']}</th>"
table_html += "</tr>"

labels = ["기상", "운량", "미세먼지", "발령 확률"]
for label in labels:
    table_html += f"<tr><td>{label}</td>"
    for day in weekly_env:
        if label == "기상": val = f"{day['min']}°/{day['max']}°"
        elif label == "운량": val = f"{day['cloud']} ({day['sky']})"
        elif label == "미세먼지": val = day['air']
        elif label == "발령 확률":
            prob = 20 + (day['cloud'] * 5)
            color_class = "prob-critical" if prob > 50 else "prob-safe"
            val = f"<span class='{color_class}'>{prob}%</span>"
        table_html += f"<td>{val}</td>"
    table_html += "</tr>"
table_html += "</table>"
st.markdown(table_html, unsafe_allow_html=True)

# 그래프 섹션
st.markdown("#### 실시간 순부하 및 태양광 변동 추이")
fig = go.Figure()
fig.add_trace(go.Scatter(x=list(range(24)), y=[60+i for i in range(24)], name="예측 부하", line=dict(color='#00f2ff', width=3)))
fig.update_layout(template='plotly_dark', height=400, margin=dict(l=20, r=20, t=20, b=20))
st.plotly_chart(fig, use_container_width=True)
