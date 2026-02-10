import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta, timezone

# 1. 환경 설정 및 시간대 설정
def get_now_kst():
    return datetime.now(timezone(timedelta(hours=9)))

SERVICE_KEY = st.secrets["SERVICE_KEY"]
NOW = get_now_kst()

# 2. 기상청 단기예보 API 호출 (오늘~3일치)
@st.cache_data(ttl=3600)
def get_short_term_forecast(nx=60, ny=127):
    # 오늘 기준 가장 최근 발표 시점 계산 (보통 0200, 0500 등)
    base_date = NOW.strftime("%Y%m%d")
    url = "http://apis.data.go.kr/1360000/VilageFcstInfoService_2.0/getVilageFcst"
    
    params = {
        'serviceKey': SERVICE_KEY,
        'pageNo': '1',
        'numOfRows': '1000',
        'dataType': 'JSON',
        'base_date': base_date,
        'base_time': '0500', # 05시 발표분 기준
        'nx': nx,
        'ny': ny
    }
    
    try:
        res = requests.get(url, params=params)
        items = res.json()['response']['body']['items']['item']
        df = pd.DataFrame(items)
        return df
    except Exception as e:
        st.error(f"단기예보 API 호출 실패: {e}")
        return None

# 3. 기상청 중기예보 API 호출 (3일 후~10일치)
@st.cache_data(ttl=3600)
def get_mid_term_forecast(reg_id="11B10101", land_id="11B00000"):
    # 중기 기온 예보
    url_ta = "http://apis.data.go.kr/1360000/MidFcstInfoService/getMidTa"
    # 중기 육상 예보 (구름/하늘상태)
    url_land = "http://apis.data.go.kr/1360000/MidFcstInfoService/getMidLandFcst"
    
    base_date = NOW.strftime("%Y%m%d") + "0600" # 06시 발표 기준
    
    params_ta = {'serviceKey': SERVICE_KEY, 'dataType': 'JSON', 'regId': reg_id, 'tmFc': base_date}
    params_land = {'serviceKey': SERVICE_KEY, 'dataType': 'JSON', 'regId': land_id, 'tmFc': base_date}
    
    try:
        res_ta = requests.get(url_ta, params=params_ta).json()
        res_land = requests.get(url_land, params=params_land).json()
        
        ta_item = res_ta['response']['body']['items']['item'][0]
        land_item = res_land['response']['body']['items']['item'][0]
        return ta_item, land_item
    except Exception as e:
        st.error(f"중기예보 API 호출 실패: {e}")
        return None, None

# 4. 데이터 가공 및 주간 리스트 생성 (월~금)
def build_weekly_weather():
    short_df = get_short_term_forecast()
    mid_ta, mid_land = get_mid_term_forecast()
    
    this_monday = NOW - timedelta(days=NOW.weekday())
    weekly_list = []
    
    for i in range(5): # 월(0) ~ 금(4)
        target_date = this_monday + timedelta(days=i)
        d_str = target_date.strftime("%Y%m%d")
        
        # 기본 구조 (더미 방지용 초기값)
        day_info = {"date": target_date.strftime("%m.%d"), "min": 0, "max": 0, "sky": "확인불가"}
        
        # 월요일 (과거/관측 데이터 영역 - 여기서는 단기예보의 어제 기록이 없으므로 관측 API 필요)
        if i == 0:
            day_info.update({"min": -8.0, "max": 2.1, "sky": "맑음"}) # 임시 관측치
        
        # 오늘(화) ~ 목요일 (단기예보 활용)
        elif 1 <= i <= 3:
            day_data = short_df[short_df['fcstDate'] == d_str]
            if not day_data.empty:
                tmn = day_data[day_data['category'] == 'TMN']['fcstValue'].values
                tmx = day_data[day_data['category'] == 'TMX']['fcstValue'].values
                sky = day_data[day_data['category'] == 'SKY']['fcstValue'].iloc[0] # 하늘상태
                
                sky_map = {"1": "맑음", "3": "구름많음", "4": "흐림"}
                day_info.update({
                    "min": float(tmn[0]) if len(tmn)>0 else 0,
                    "max": float(tmx[0]) if len(tmx)>0 else 0,
                    "sky": sky_map.get(sky, "확인불가")
                })
        
        # 금요일 (중기예보 활용 - 오늘이 화요일이면 금요일은 3일 후)
        elif i == 4:
            if mid_ta and mid_land:
                day_info.update({
                    "min": mid_ta['taMin3'],
                    "max": mid_ta['taMax3'],
                    "sky": mid_land['wf3Pm'] # 3일 후 오후 날씨
                })
                
        weekly_list.append(day_info)
    return weekly_list

# 5. UI 출력
st.title("NOSTRADAMUS 주간 날씨 관제")
weather_data = build_weekly_weather()

cols = st.columns(5)
week_names = ["월요일", "화요일(오늘)", "수요일", "목요일", "금요일"]

for idx, col in enumerate(cols):
    with col:
        st.markdown(f"**{week_names[idx]}**")
        st.write(f"📅 {weather_data[idx]['date']}")
        st.write(f"🌡️ {weather_data[idx]['min']}℃ / {weather_data[idx]['max']}℃")
        st.write(f"☁️ {weather_data[idx]['sky']}")
