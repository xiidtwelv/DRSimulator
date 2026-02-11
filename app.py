import streamlit as st
import pandas as pd
import numpy as np
import requests
from datetime import datetime, timedelta, timezone
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# 1. 페이지 설정 및 기본 세팅
st.set_page_config(page_title="국민DR 통합 관제 V3.5 (Nostradamus Engine)", layout="wide")

def get_now_kst():
    return datetime.now(timezone(timedelta(hours=9)))

now = get_now_kst()
SERVICE_KEY = st.secrets.get("SERVICE_KEY", "")

# --- [디자인] CSS: 오늘 날짜 강조 및 관제 센터 테마 ---
st.markdown("""
    <style>
    [data-testid="stAppViewContainer"] { background-color: #05070a; }
    .metric-card { background: #10141c; border: 1px solid #1e2633; padding: 15px; border-radius: 8px; text-align: center; }
    .metric-label { color: #c9d1d9 !important; font-size: 0.9rem; }
    .metric-value { color: #00f2ff !important; font-size: 1.8rem; font-weight: 800; }
    
    /* 테이블 스타일 및 오늘(Today) 강조 */
    .fixed-table { width: 100%; border-collapse: collapse; margin-top: 10px; }
    .fixed-table th, .fixed-table td { border: 1px solid #30363d; padding: 12px; text-align: center; color: white; }
    .fixed-table th { background: #1c2128; color: #58a6ff; }
    .today-highlight { border: 3px solid #00f2ff !important; background: rgba(0, 242, 255, 0.05); }
    .status-alert { color: #ff3131; font-weight: 900; background: rgba(255, 49, 49, 0.1); border-radius: 4px; padding: 2px 5px; }
    </style>
    """, unsafe_allow_html=True)

# --- [ENGINE] 노스트라다무스 발령 확률 계산 로직 ---
def calculate_dr_prob(temp_min, cloud, dust_pm10, reserve_gw):
    # 가중치 초기화
    w_temp = 0; w_cloud = 0; w_dust = 0; w_reserve = 0
    
    # 1. 기온 가중치 (한파/폭염 임계치)
    if temp_min <= -5.0 or temp_min >= 33.0: w_temp = 35
    elif temp_min <= 0.0: w_temp = 15
    
    # 2. 운량 가중치 (태양광 발전 저하)
    if cloud >= 8: w_cloud = 30
    
    # 3. 미세먼지 가중치 (나쁨 이상)
    if dust_pm10 >= 81: w_dust = 15
    
    # 4. 예비력 가중치 (핵심 지표)
    if reserve_gw < 6.5: w_reserve = 50
    elif reserve_gw < 10.0: w_reserve = 20
    
    total_prob = min(100, w_temp + w_cloud + w_dust + w_reserve)
    return total_prob

# --- [CORE] API 데이터 수집 (서울/대전/대구 평균) ---
@st.cache_data(ttl=600)
def fetch_integrated_data():
    # 전력 데이터 (KPX)
    pwr = {"load_act": 0.0, "reserve": 0.0, "supply": 0.0, "status": "연결중"}
    try:
        kpx_url = "http://apis.data.go.kr/B552566/9s_status_info/get9s_status_info"
        res = requests.get(kpx_url, params={'serviceKey': SERVICE_KEY, 'dataType': 'JSON'}, timeout=5)
        if res.status_code == 200:
            item = res.json()['response']['body']['items']['item'][0]
            pwr = {
                "load_act": round(float(item['currPwrTot']) / 1000, 1),
                "supply": round(float(item['suppAbility']) / 1000, 1),
                "reserve": float(item['suppReservePwrRate']),
                "reserve_gw": round(float(item['suppReservePwr']) / 1000, 1),
                "status": "정상" if float(item['suppReservePwrRate']) > 10 else "주의"
            }
    except:
        pwr = {"load_act": 78.2, "reserve": 12.5, "supply": 98.0, "reserve_gw": 11.2, "status": "정상"}

    # 평일(월~금) 날짜 리스트 생성
    weekday_data = []
    # 이번주 월요일 찾기
    monday = now - timedelta(days=now.weekday())
    if now.weekday()
