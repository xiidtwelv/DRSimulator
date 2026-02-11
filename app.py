import streamlit as st
import requests
import pandas as pd
from datetime import datetime

# 페이지 설정
st.set_page_config(page_title="기상청 주간 예보", layout="wide")

# API 설정 (본인의 서비스 키를 입력하세요)
SERVICE_KEY = "여기에_공공데이터포털_인증키를_넣으세요"

st.title("🇰🇷 기상청 중기 육상 예보 (서울 기준)")
st.info("이 서비스는 기상청 API를 통해 향후 3일~10일간의 날씨 정보를 제공합니다.")

# 중기예보를 위한 날짜 계산 (오늘 기준 06시 발표 데이터 호출)
today = datetime.now().strftime("%Y%m%d")
tm_fc = f"{today}0600" # 오전 6시 발표분 기준

# 서울/인천/경기도 지역 코드 (서울: 11B10101)
# 다른 지역은 공공데이터포털 가이드의 '지점 코드' 확인 필요
reg_id = "11B10101"

if SERVICE_KEY == "여기에_공공데이터포털_인증키를_넣으세요":
    st.warning("먼저 'SERVICE_KEY' 변수에 본인의 기상청 API 인증키를 입력해주세요.")
else:
    # 기상청 중기육상예보조회 API URL
    url = "http://apis.data.go.kr/1360000/MidFcstInfoService/getMidLandFcst"
    
    params = {
        'serviceKey': SERVICE_KEY,
        'pageNo': '1',
        'numOfRows': '10',
        'dataType': 'JSON',
        'regId': reg_id,
        'tmFc': tm_fc
    }

    try:
        response = requests.get(url, params=params)
        res_data = response.json()

        if res_data['response']['header']['resultCode'] == '00':
            item = res_data['response']['body']['items']['item'][0]
            
            # 데이터 가공 (기상청 중기예보는 3일~10일 후 데이터를 제공함)
            forecast_data = []
            for i in range(3, 8):  # 3일부터 7일까지는 오전/오후 분리
                forecast_data.append({
                    "기간": f"{i}일 후 (오전)",
                    "강수확률(%)": item[f"rnSt{i}Am"],
                    "날씨상태": item[f"wf{i}Am"]
                })
                forecast_data.append({
                    "기간": f"{i}일 후 (오후)",
                    "강수확률(%)": item[f"rnSt{i}Pm"],
                    "날씨상태": item[f"wf{i}Pm"]
                })
            
            for i in range(8, 11): # 8일부터 10일까지는 하루 단위
                forecast_data.append({
                    "기간": f"{i}일 후",
                    "강수확률(%)": item[f"rnSt{i}"],
                    "날씨상태": item[f"wf{i}"]
                })

            # 화면 출력
            st.subheader(f"📍 서울 지역 예보 (기준 시각: {tm_fc})")
            
            # 가독성을 위한 카드 레이아웃
            cols = st.columns(4)
            for idx, f in enumerate(forecast_data[:8]): # 우선 3~6일치만 상단 카드 표시
                with cols[idx % 4]:
                    st.metric(f["기간"], f["날씨상태"])
                    st.write(f"💧 강수확률: {f['강수확률(%)']}%")
            
            st.divider()
            st.subheader("📋 전체 일정별 상세 예보")
            st.table(pd.DataFrame(forecast_data))

        else:
            st.error(f"API 오류: {res_data['response']['header']['resultMsg']}")
            st.caption("데이터가 아직 업데이트되지 않았을 수 있습니다. (06:00, 18:00 발표)")

    except Exception as e:
        st.error(f"데이터 로드 중 오류 발생: {e}")
        st.info("인증키가 올바른지, 혹은 API 신청 후 승인 시간이 지났는지 확인해 주세요.")

st.caption("제공: 기상청 중기예보 조회서비스")
