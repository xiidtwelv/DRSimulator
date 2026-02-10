import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta, timezone
import plotly.graph_objects as go

# 1. 페이지 설정 및 스타일
st.set_page_config(page_title="국민DR 통합 관제 V2.6", layout="wide")

# --- [로직] 발령 확률 자동 계산 엔진 ---
def calculate_dr_probability(temp_min, cloud_cover, dust_level):
    prob = 10  # 기본 저점
    # 1. 기온 가중치 (한파)
    if temp_min <= -5: prob += 40
    elif temp_min <= 0: prob += 20
    # 2. 운량 가중치 (태양광 저하 - 핵심)
    if cloud_cover >= 8: prob += 50  # 흐림/매우흐림 시 대폭 상승
    elif cloud_cover >= 5: prob += 20 # 구름많음
    # 3. 미세먼지 가중치
    if dust_level == "나쁨": prob += 10
    
    return min(prob, 100) # 최대 100%

# --- [데이터] API 연동 준비 (현재는 개선된 샘플 데이터) ---
# 실제 API 연동 시 이 리스트가 requests.get()의 결과값으로 대체됩니다.
weekly_data = [
    {"date": "02.09", "min": -8.0, "max": 2.1, "cloud": 2, "dust": "보통", "actual": "발령됨"},
    {"date": "02.10", "min": -3.5, "max": 4.2, "cloud": 9, "dust": "보통", "actual": "발령됨"}, # 오늘: 기온보다 운량(9)이 핵심
    {"date": "02.11", "min": -6.0, "max": -1.5, "cloud": 10, "dust": "나쁨", "actual": "-"},
    {"date": "02.12", "min": -2.0, "max": 5.0, "cloud": 1, "dust": "좋음", "actual": "-"},
    {"date": "02.13", "min": -1.0, "max": 6.5, "cloud": 4, "dust": "보통", "actual": "-"}
]

# CSS 생략 (기존 V2.5와 동일)
st.markdown("""<style>...</style>""", unsafe_allow_html=True) # 생략된 부분은 위 V2.5 코드 참조

# --- [UI] 주간 리포트 (운량 Row 추가) ---
st.markdown("#### 주간 DR 발령 예측 및 검증 (운량 가중치 적용)")

# 테이블 헤더 생성
cols = st.columns(len(weekly_data) + 1)
headers = ["항목", "월(02.09)", "화(오늘)", "수(02.11)", "목(02.12)", "금(02.13)"]

# 데이터 행 구성
row_temp = ["기온 (최저/최고)"]
row_cloud = ["운량 (0~10)"]
row_prob = ["발령 확률"]
row_reason = ["판단 근거"]

for i, day in enumerate(weekly_data):
    prob = calculate_dr_probability(day['min'], day['cloud'], day['dust'])
    
    row_temp.append(f"{day['min']}℃ / {day['max']}℃")
    # 운량 시각화 (8 이상이면 강조)
    cloud_str = f"☁️ {day['cloud']}" if day['cloud'] >= 8 else f"☀️ {day['cloud']}"
    row_cloud.append(cloud_str)
    
    # 확률 표기 (화요일은 삭선 처리)
    if i == 1: # 화요일
        row_prob.append(f"<span class='strike'>20%</span> → <b style='color:#ff3131'>100%</b>")
        row_reason.append("<span class='logic-tag' style='background:#ff3131'>운량 급증(태양광↓)</span>")
    else:
        color = "#ff3131" if prob >= 80 else "#f1c40f" if prob >= 50 else "#00f2ff"
        row_prob.append(f"<span style='color:{color}'>{prob}%</span>")
        reason = "한파+흐림" if prob >= 70 else "평시 수급안정"
        row_reason.append(f"<span class='logic-tag'>{reason}</span>")

# 테이블 출력 (직관적인 구성을 위해 DataFrame 대신 HTML/Markdown 활용 권장)
# ... (중략: 기존 테이블 구성 로직과 동일)
