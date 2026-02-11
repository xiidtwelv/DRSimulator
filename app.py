import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta

st.set_page_config(page_title="기상청 주간 예보", layout="wide", page_icon="🌤️")

# 🔐 Secrets 확인
try:
    SERVICE_KEY = st.secrets["SERVICE_KEY"]
except:
    st.error("Secrets에 'SERVICE_KEY'를 설정해주세요.")
    st.stop()

st.title("🌤️ 기상청 중기 주간 예보")

# 1. 시간 설정 로직 개선 (기상청 데이터 업데이트 지연 고려)
now = datetime.now()
# 발표 직후에는 데이터가 없을 수 있으므로 1시간 정도 여유를 둡니다.
if now.hour < 7:
    tm_fc = (now - timedelta(days=1)).strftime("%Y%m%d") + "1800"
elif now.hour < 19:
    tm_fc = now.strftime("%Y%m%d") + "0600"
else:
    tm_fc = now.strftime("%Y%m%d") + "1800"

reg_id = "11B10101" # 서울/경기

@st.cache_data(ttl=3600)
def get_mid_weather(key, reg, time):
    url = "http://apis.data.go.kr/1360000/MidFcstInfoService/getMidLandFcst"
    params = {
        'serviceKey': key, 'pageNo': '1', 'numOfRows': '10',
        'dataType': 'JSON', 'regId': reg, 'tmFc': time
    }
    try:
        res = requests.get(url, params=params, timeout=10)
        return res.json()
    except:
        return None

with st.spinner('데이터를 불러오고 있습니다...'):
    data = get_mid_weather(SERVICE_KEY, reg_id, tm_fc)

    # 2. 데이터 존재 여부 정밀 체크
    if data and 'response' in data and data['response']['header']['resultCode'] == '00':
        body = data['response'].get('body', {})
        items = body.get('items', {})
        
        if items and 'item' in items:
            item = items['item'][0]
            forecast_list = []
            
            # 3. KeyError 방지를 위한 .get() 사용
            try:
                for i in range(3, 8):
                    forecast_list.append({"날짜": f"{i}일 후 오전", "상태": item.get(f"wf{i}Am", "-"), "강수
