import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta, timezone
import plotly.graph_objects as go

# 1. 페이지 설정
st.set_page_config(page_title="국민DR 통합 관제 V2.7", layout="wide")

# --- [API 연동 핵심 로직] ---
def get_now_kst():
    return datetime.now(timezone(timedelta(hours=9)))

@st.cache_data(ttl=3600) # 1시간 동안 데이터 캐싱
def fetch_realtime_data(nx, ny):
    """
    기상청 단기예보 API 연동
    """
    service_key = st.secrets["SERVICE_KEY"]
    now = get_now_kst()
    
    # 기상청 API는 새벽에 당일 데이터를 보려면 전날 23시나 당일 02/05시 발표를 참조해야 함
    base_date = now.strftime("%Y%m%d")
    base_time = "0500" # 가장 안정적인 오전 발표 타임
    
    url = "http://apis.data.go.kr/1360000/VilageFcstInfoService_2.0/getVilageFcst"
    params = {
        'serviceKey': service_key,
        'pageNo': '1',
        'numOfRows': '200',
        'dataType': 'JSON',
        'base_date': base_date,
        'base_time': base_time,
        'nx': str(nx),
        'ny': str(ny)
    }

    try:
        response = requests.get(url, params=params, timeout=10)
        res_json = response.json()
        items = res_json['response']['body']['items']['item']
        
        # API 데이터를 이미지 형식의 데이터셋으로 변환
        weather_dict = {}
        for item in items:
            fcst_date = item['fcstDate'][-4:] # MMDD 형식
            if fcst_date not in weather_dict:
                weather_dict[fcst_date] = {"date": fcst_date, "min": "0", "max": "0", "sky": "-", "cloud": 0}
            
            # TMN: 최저기온, TMX: 최고기온, SKY: 하늘상태
            if item['category'] == 'TMN': weather_dict[fcst_date]['min'] = item['fcstValue']
            if item['category'] == 'TMX': weather_dict[fcst_date]['max'] = item['fcstValue']
            if item['category'] == 'SKY': 
                sky_val = int(item['fcstValue'])
                weather_dict[fcst_date]['cloud'] = sky_val
                weather_dict[fcst_date]['sky'] = "맑음" if sky_val <= 5 else "흐림"

        # 리스트 형태로 변환 (최근 5일치만)
        weather_list = list(weather_dict.values())[:5]
        # 미세먼지 및 DR 발령 정보는 임의의 값 부여 (실제 운영 시 추가 API 연동 가능)
        for d in weather_list:
            d['air'] = "보통"
            d['dr'] = "-"
            
        pwr_data = {"load": 78.5, "supply": 105.0, "reserve_gw": 10.2}
        return pwr_data, weather_list

    except Exception as e:
        # API 호출 실패 시 에러를 발생시켜 아래 try-except에서 잡히게 함
        raise e

# --- [메인 실행부] ---
try:
    # 2번 질문에 대한 답변: 인자값(60, 127)을 넣어 호출합니다.
    pwr_data, weekly_env = fetch_realtime_data(60, 127)
except Exception as e:
    st.error(f"⚠️ API 연결 오류: {e}")
    st.info("💡 'SERVICE_KEY'가 공공데이터포털에서 승인 완료되었는지(약 1~2시간 소요), 혹은 좌표가 정확한지 확인해 주세요.")
    st.stop()

# --- [UI 디자인 및 출력] (기존 소스 유지) ---
st.markdown("""
    <style>
    [data-testid="stAppViewContainer"] { background-color: #05070a; color: white; }
    .metric-card { background: #10141c; border: 1px solid #1e2633; padding: 20px; border-radius: 8px; text-align: center; }
    .metric-value { color: #00f2ff; font-size: 1.8rem; font-weight: 700; }
    .fixed-table { width: 100%; border-collapse: collapse; margin-top: 20px; }
    .fixed-table td, .fixed-table th { border: 1px solid #30363d; padding: 10px; text-align: center; }
    </style>
    """, unsafe_allow_html=True)

st.title("NOSTRADAMUS 실시간 관제")

# 지표 출력 부분
m1, m2, m3 = st.columns(3)
m1.markdown(f"<div class='metric-card'>부하: <span class='metric-value'>{pwr_data['load']} GW</span></div>", unsafe_allow_html=True)
m2.markdown(f"<div class='metric-card'>예비력: <span class='metric-value'>{pwr_data['reserve_gw']} GW</span></div>", unsafe_allow_html=True)
m3.markdown(f"<div class='metric-card'>상태: <span class='metric-value'>정상</span></div>", unsafe_allow_html=True)

# 테이블 출력 부분
st.write("### 주간 예측")
st.table(pd.DataFrame(weekly_env))
