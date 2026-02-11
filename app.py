import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta

# 페이지 설정
st.set_page_config(page_title="기상청 주간 예보", layout="wide", page_icon="🌤️")

# 🔐 Secrets에서 서비스 키 불러오기 
# (Streamlit Cloud의 Settings -> Secrets 메뉴에 SERVICE_KEY="값" 형태로 저장되어 있어야 합니다)
try:
    SERVICE_KEY = st.secrets["SERVICE_KEY"]
except:
    st.error("Secrets에 'SERVICE_KEY'가 설정되지 않았습니다.")
    st.stop()

st.title("🌤️ 기상청 중기 주간 예보")
st.caption("공공데이터포털 기상청 API 연동 (서울/경기 지역 기준)")

# 기상청 중기예보는 06:00, 18:00에 발표됩니다.
# 현재 시간에 맞춰 가장 최근 발표 시각을 계산합니다.
now = datetime.now()
if now.hour < 6:
    # 새벽이면 어제 저녁 6시 데이터 호출
    target_date = (now - timedelta(days=1)).strftime("%Y%m%d")
    tm_fc = f"{target_date}1800"
elif now.hour < 18:
    # 오전~오후 사이면 오늘 오전 6시 데이터 호출
    tm_fc = f"{now.strftime('%Y%m%d')}0600"
else:
    # 저녁 6시 이후면 오늘 저녁 6시 데이터 호출
    tm_fc = f"{now.strftime('%Y%m%d')}1800"

# 서울/인천/경기도 지역 코드
reg_id = "11B10101"

# API 호출 함수
@st.cache_data(ttl=3600) # 1시간 동안 결과 캐싱
def get_mid_weather(key, reg, time):
    url = "http://apis.data.go.kr/1360000/MidFcstInfoService/getMidLandFcst"
    params = {
        'serviceKey': key,
        'pageNo': '1',
        'numOfRows': '10',
        'dataType': 'JSON',
        'regId': reg,
        'tmFc': time
    }
    res = requests.get(url, params=params)
    return res.json()

# 실행 및 화면 표시
with st.spinner('기상청 데이터를 불러오는 중...'):
    data = get_mid_weather(SERVICE_KEY, reg_id, tm_fc)

    if data.get('response', {}).get('header', {}).get('resultCode') == '00':
        item = data['response']['body']['items']['item'][0]
        
        # 3일~10일 후 날씨 데이터 정리
        forecast_list = []
        for i in range(3, 8):
            forecast_list.append({"날짜": f"{i}일 후 오전", "상태": item[f"wf{i}Am"], "강수": f"{item[f'rnSt{i}Am']}%"})
            forecast_list.append({"날짜": f"{i}일 후 오후", "상태": item[f"wf{i}Pm"], "강수": f"{item[f'rnSt{i}Pm']}%"})
        
        for i in range(8, 11):
            forecast_list.append({"날짜": f"{i}일 후", "상태": item[f"wf{i}"], "강수": f"{item[f'rnSt{i}']}%"})

        df = pd.DataFrame(forecast_list)

        # 상단 주요 요약 (카드 형태)
        st.subheader(f"📍 주요 예보 (발표시각: {tm_fc})")
        cols = st.columns(5)
        for idx, row in enumerate(forecast_list[:10:2]): # 오전 데이터 위주로 5일치 표시
            with cols[idx]:
                st.metric(row["날짜"].split()[0], row["상태"])
                st.caption(f"강수확률: {row['강수']}")

        st.divider()
        
        # 상세 테이블
        st.subheader("📋 전체 주간 상세 일정")
        st.table(df)
        
    else:
        st.error("데이터를 불러오지 못했습니다. 서비스 키 혹은 기상청 점검 상태를 확인하세요.")
        if 'response' in data:
            st.write(f"사유: {data['response']['header']['resultMsg']}")

st.sidebar.markdown("### 설정 안내")
st.sidebar.info("기상청 API는 발표 직후(06:05, 18:05 등)에는 데이터 업데이트 지연이 발생할 수 있습니다.")
