import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta

# 페이지 설정
st.set_page_config(page_title="기상청 주간 예보", layout="wide", page_icon="🌤️")

# 🔐 Secrets에서 서비스 키 불러오기
try:
    SERVICE_KEY = st.secrets["SERVICE_KEY"]
except:
    st.error("Streamlit Secrets에 'SERVICE_KEY'를 설정해주세요.")
    st.stop()

st.title("🌤️ 기상청 중기 주간 예보")

# 1. 기상청 발표 시각 계산 (06시, 18시)
now = datetime.now()
if now.hour < 7:
    tm_fc = (now - timedelta(days=1)).strftime("%Y%m%d") + "1800"
elif now.hour < 19:
    tm_fc = now.strftime("%Y%m%d") + "0600"
else:
    tm_fc = now.strftime("%Y%m%d") + "1800"

reg_id = "11B10101" # 서울/경기 지역코드

@st.cache_data(ttl=3600)
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
    try:
        res = requests.get(url, params=params, timeout=10)
        return res.json()
    except:
        return None

with st.spinner('데이터를 불러오고 있습니다...'):
    data = get_mid_weather(SERVICE_KEY, reg_id, tm_fc)

    if data and 'response' in data and data['response']['header']['resultCode'] == '00':
        try:
            items = data['response'].get('body', {}).get('items', {}).get('item', [])
            if items:
                item = items[0]
                forecast_list = []
                
                # 3일~7일차 (오전/오후 분리)
                for i in range(3, 8):
                    wf_am = item.get(f"wf{i}Am", "-")
                    rn_am = item.get(f"rnSt{i}Am", "0")
                    wf_pm = item.get(f"wf{i}Pm", "-")
                    rn_pm = item.get(f"rnSt{i}Pm", "0")
                    
                    forecast_list.append({"날짜": f"{i}일 후 오전", "상태": wf_am, "강수": f"{rn_am}%"})
                    forecast_list.append({"날짜": f"{i}일 후 오후", "상태": wf_pm, "강수": f"{rn_pm}%"})
                
                # 8일~10일차 (하루 통합)
                for i in range(8, 11):
                    wf = item.get(f"wf{i}", "-")
                    rn = item.get(f"rnSt{i}", "0")
                    forecast_list.append({"날짜": f"{i}일 후", "상태": wf, "강수": f"{rn}%"})
                
                # 화면 표시
                st.subheader(f"📍 서울/경기 예보 (발표: {tm_fc})")
                
                # 카드형 UI
                cols = st.columns(5)
                for idx, row in enumerate(forecast_list[:10:2]):
                    with cols[idx]:
                        st.metric(row["날짜"].replace(" 후 오전", ""), row["상태"])
                        st.caption(f"💧 강수 {row['강수']}")
                
                st.divider()
                st.subheader("📋 상세 예보 데이터")
                st.dataframe(pd.DataFrame(forecast_list), use_container_width=True)
            else:
                st.warning("예보 데이터가 비어있습니다. 잠시 후 다시 시도해주세요.")
        except Exception as e:
            st.error(f"데이터 처리 중 오류가 발생했습니다: {e}")
    else:
        error_msg = data['response']['header']['resultMsg'] if data else "API 연결 실패"
        st.error(f"기상청 API 오류: {error_msg}")
        st.info("발표 시각 직후에는 데이터가 없을 수 있습니다.")

st.caption("Data provided by Korea Meteorological Administration")
